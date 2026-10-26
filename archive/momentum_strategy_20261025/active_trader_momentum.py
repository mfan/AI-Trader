#!/usr/bin/env python3
"""
Active Day Trading Program - High-Frequency Momentum Day Trader
Runs continuously, scanning the market every 2 minutes for high-momentum movers,
analyzing their trend robustness using EMAs, ATRs, & RSIs, and trading the top 2.

Risk Management & Features:
- Trade size: exactly $50,000 per position.
- Maximum 2 concurrent positions at a time.
- Standard Price filter (>= $5) and easy-to-borrow check for shorts.
- Robust EMA-based trailing stop-loss, updated every 2 minutes.
- Explicit timezone handling and market hours tracking (regular sessions only: 9:30 AM - 4:00 PM ET).
- End of day automatic closeout at 3:45 PM ET.
- Preserves strategy state automatically in a local state JSON file for resuming on restarts.
"""

import os
import sys
import json
import time
import asyncio
import signal
import traceback
import logging
from datetime import datetime, time as dt_time, timedelta
import pytz
import numpy as np
import talib
import requests
from dotenv import load_dotenv

# Ensure project root is in the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

# Configure logging to both console and file
log_dir = os.path.join(project_root, "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'active_trader_momentum.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('MomentumTrader')

# File path for trade state persistence
STATE_FILE = os.path.join(project_root, "data", "momentum_trades_state.json")
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

# Reconcile local state with actual broker positions every N strategy cycles (~30 min at 2-min cycles)
RECONCILE_INTERVAL_CYCLES = 15

# Global flag for graceful shutdown
shutdown_requested = False

# Alpaca API configuration
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')
is_paper = os.getenv('ALPACA_PAPER_TRADING', 'true').lower() == 'true'

headers = {
    "APCA-API-KEY-ID": api_key,
    "APCA-API-SECRET-KEY": secret_key,
    "accept": "application/json"
}

def signal_handler(sig, frame):
    """Handle Ctrl+C and termination signals gracefully"""
    global shutdown_requested
    if shutdown_requested:
        logger.info("🛑 Force shutdown requested. Exiting immediately...")
        sys.exit(1)
    else:
        logger.info("⚠️ Shutdown signal received. Gracefully cleaning up and exiting...")
        shutdown_requested = True


# ==================== STATE MANAGEMENT ====================

def load_state() -> dict:
    """Load open positions and trade history from persistent state file"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                # Ensure keys exist
                if "active_trades" not in state:
                    state["active_trades"] = {}
                if "trade_history" not in state:
                    state["trade_history"] = []
                return state
        except Exception as e:
            logger.error(f"❌ Error loading state file: {e}. Starting with clean state.")
            
    return {"active_trades": {}, "trade_history": []}


def save_state(state: dict):
    """Save open positions and trade history to persistent state file"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"❌ Error saving state file: {e}")


# ==================== ALPACA INTEGRATION HELPERS ====================

def get_latest_trade_info(symbol: str):
    """
    Fetch the latest trade price AND its timestamp for a symbol.
    Returns (price, trade_datetime_utc). Timestamp is None when only a quote
    fallback is available (staleness cannot be determined in that case).
    """
    try:
        url = f"https://data.alpaca.markets/v2/stocks/{symbol}/trades/latest"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            trade = data.get("trade")
            if trade:
                price = float(trade.get("p", 0.0))
                ts_raw = trade.get("t")
                trade_ts = None
                if ts_raw:
                    try:
                        trade_ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    except ValueError:
                        trade_ts = None
                if price > 0:
                    return price, trade_ts
        # Fallback to general trading client if needed (quote-based, no trade timestamp)
        from tools.alpaca_trading import get_alpaca_client
        client = get_alpaca_client()
        price = client.get_latest_price(symbol)
        if price and price > 0:
            return price, None
    except Exception as e:
         logger.debug(f"⚠️ Error getting latest trade info for {symbol}: {e}")
    return 0.0, None


def get_latest_trade_price(symbol: str) -> float:
    """Fetch the latest real-time trade price for a symbol"""
    price, _ = get_latest_trade_info(symbol)
    return price


def is_trade_stale(trade_ts, market_is_open: bool) -> bool:
    """
    Detect halted/delisted stocks by last-trade age.
    - Always stale if the last trade is more than 5 calendar days old.
    - During the regular session, stale if no trade for over 1 hour.
    A None timestamp (quote-only fallback) cannot be judged and is treated as fresh.
    """
    if trade_ts is None:
        return False
    age = datetime.now(pytz.utc) - trade_ts
    if age > timedelta(days=5):
        return True
    if market_is_open and age > timedelta(hours=1):
        return True
    return False


def fetch_historical_bars(symbol: str, limit: int = 35) -> list:
    """
    Fetch historical 5-minute bars for a symbol.
    Uses a 16-minute delayed window to support free accounts' SIP-data constraints on Alpaca.
    """
    try:
        # 16 minutes delay buffer
        now = datetime.now(pytz.utc)
        end_time = now - timedelta(minutes=16)
        start_time = end_time - timedelta(days=3) # Go back a couple days to ensure enough bars
        
        from tools.alpaca_data_feed import AlpacaDataFeed
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
        
        feed = AlpacaDataFeed(feed='iex')
        tf_5m = TimeFrame(5, TimeFrameUnit.Minute)
        
        bars_dict = feed.get_bars([symbol], start_time, end_time, timeframe=tf_5m)
        bars = bars_dict.get(symbol, [])
        if bars:
            # Sort from oldest to newest by timestamp and return the latest N requested bars
            bars_sorted = sorted(bars, key=lambda x: x["timestamp"])
            return bars_sorted[-limit:]
    except Exception as e:
        logger.error(f"❌ Error fetching historical bars for {symbol}: {e}")
    return []


def is_asset_shortable(symbol: str) -> bool:
    """Verify if a stock asset is shortable on Alpaca"""
    try:
        from tools.alpaca_trading import get_alpaca_client
        client = get_alpaca_client()
        asset = client.trading_client.get_asset(symbol)
        return bool(asset and asset.shortable and asset.easy_to_borrow)
    except Exception as e:
        logger.warning(f"⚠️ Could not check if {symbol} is shortable: {e}")
    return False


def place_alpaca_order(symbol: str, qty: int, side: str, fill_timeout: int = 30) -> dict:
    """
    Submit a market order to Alpaca and VERIFY the actual fill.

    Order acceptance is NOT a fill: a submitted order may sit pending (illiquid
    names) or fill only partially. This polls the order until it fills, and on
    timeout cancels the remainder, returning the actual filled quantity/price.

    Returns: {"success": bool, "filled_qty": float, "filled_avg_price": float|None, "status": str}
    """
    result = {"success": False, "filled_qty": 0.0, "filled_avg_price": None, "status": "none"}
    try:
        from tools.alpaca_trading import get_alpaca_client
        client = get_alpaca_client()
        logger.info(f"📡 Sending {side.upper()} order for {qty} shares of {symbol}...")

        if side.lower() == "buy":
            submit = client.buy_market(symbol, qty)
        else:
            submit = client.sell_market(symbol, qty)

        if not submit or not submit.get("success"):
            logger.error(f"❌ Order submission failed for {symbol}: {submit}")
            return result

        order_id = submit.get("order_id")
        result["status"] = submit.get("status", "submitted")

        # Poll until the order reaches a terminal state or the timeout expires
        deadline = time.time() + fill_timeout
        order = None
        while time.time() < deadline:
            order = client.get_order(order_id)
            if order is None:
                break
            status = order.get("status")
            result["status"] = status
            if status == "filled":
                break
            if status in ("canceled", "expired", "rejected"):
                logger.error(f"❌ Order {order_id} for {symbol} ended with status: {status}")
                break
            time.sleep(0.5)

        if order is None:
            logger.error(f"❌ Could not verify order {order_id} for {symbol}; treating as failed.")
            return result

        status = order.get("status")
        filled_qty = float(order.get("filled_qty") or 0)

        if status != "filled":
            # Not fully filled within the window: cancel any unfilled remainder
            logger.warning(f"⚠️ Order for {symbol} not fully filled (status={status}, filled {filled_qty}/{qty}). Canceling remainder...")
            try:
                client.cancel_order(order_id)
                time.sleep(1.0)
                refreshed = client.get_order(order_id)
                if refreshed:
                    filled_qty = float(refreshed.get("filled_qty") or filled_qty)
                    status = refreshed.get("status", status)
            except Exception as cancel_err:
                logger.warning(f"⚠️ Could not cancel remainder of order {order_id}: {cancel_err}")

        if filled_qty <= 0:
            logger.error(f"❌ Order for {symbol} filled 0 shares (status={status}).")
            result["status"] = status
            return result

        result.update({
            "success": True,
            "filled_qty": filled_qty,
            "filled_avg_price": order.get("filled_avg_price"),
            "status": status,
        })
        logger.info(f"✅ Order filled for {symbol} | OrderID: {order_id} | Filled {filled_qty}/{qty} @ ${order.get('filled_avg_price')}")
    except Exception as e:
        logger.error(f"❌ Critical exception placing order for {symbol}: {e}")
    return result


# ==================== TECHNICAL ANALYSIS & SCORES ====================

def calculate_trend_robustness(bars_list) -> dict:
    """
    Calculate trend robustness of a stock using EMA9/21 crossovers, slope, RSI, and ATR.
    Scored out of 100 points.
    """
    if not bars_list or len(bars_list) < 22:
        return {"up_score": 0, "down_score": 0, "status": "insufficient_data"}
        
    prices = np.array([bar["close"] for bar in bars_list], dtype=np.float64)
    highs = np.array([bar["high"] for bar in bars_list], dtype=np.float64)
    lows = np.array([bar["low"] for bar in bars_list], dtype=np.float64)
    
    # Calculate indicators
    ema9 = talib.EMA(prices, timeperiod=9)
    ema21 = talib.EMA(prices, timeperiod=21)
    atr = talib.ATR(highs, lows, prices, timeperiod=14)
    rsi = talib.RSI(prices, timeperiod=14)
    
    # Extract latest elements
    close = prices[-1]
    e9 = ema9[-1]
    e21 = ema21[-1]
    r = rsi[-1]
    a = atr[-1]
    
    # Verify slopes (checking previous 3 bars)
    ema9_rising = ema9[-1] > ema9[-2] > ema9[-3]
    ema9_falling = ema9[-1] < ema9[-2] < ema9[-3]
    ema21_rising = ema21[-1] > ema21[-2] > ema21[-3]
    ema21_falling = ema21[-1] < ema21[-2] < ema21[-3]
    
    # Upward / Bullish score
    up_score = 0
    if close > e9: up_score += 20
    if e9 > e21: up_score += 20
    if ema9_rising: up_score += 20
    if ema21_rising: up_score += 20
    if 50 <= r <= 75: up_score += 20 # Momentum sweet spot, not overbought (RSI > 80 is overbought)
    
    # Downward / Bearish score
    down_score = 0
    if close < e9: down_score += 20
    if e9 < e21: down_score += 20
    if ema9_falling: down_score += 20
    if ema21_falling: down_score += 20
    if 25 <= r <= 50: down_score += 20 # Downside momentum sweet spot, not oversold (RSI < 20 is oversold)
    
    return {
        "up_score": up_score,
        "down_score": down_score,
        "ema9": float(e9),
        "ema21": float(e21),
        "atr": float(a),
        "rsi": float(r),
        "close": float(close),
        "status": "success"
    }


# ==================== TRADING LOGIC LOOP ====================

async def execute_trading_strategy():
    """Main algorithmic trading strategy executant - runs calculations and trades"""
    state = load_state()
    active_trades = state.get("active_trades", {})
    trade_history = state.get("trade_history", [])
    
    logger.info(f"📋 Loaded {len(active_trades)} active trades from state.")
    
    # Check current time
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    current_time = now.time()
    
    # ─── CASE 1: END-OF-DAY STOP-LOSS TIGHTENING (3:45 PM ET) ───
    if current_time >= dt_time(15, 45):
        if active_trades:
            logger.info("⏰ Time is past 3:45 PM ET (pre-market close). Managing stop-losses for overnight hold...")
            updated = False
            for symbol in list(active_trades.keys()):
                trade = active_trades[symbol]
                
                # If we haven't already tightened this position's stop loss for the day:
                if not trade.get("overnight_tightened"):
                    if trade.get("untradeable"):
                        continue
                    current_price, trade_ts = get_latest_trade_info(symbol)
                    if current_price <= 0.0:
                        logger.warning(f"⚠️ Could not retrieve price for {symbol} to tighten stop loss.")
                        continue
                    if is_trade_stale(trade_ts, market_is_open=True):
                        logger.critical(f"🚫 {symbol} appears halted/delisted (last trade: {trade_ts}). Stop tightening skipped; flagging as untradeable.")
                        trade["untradeable"] = True
                        active_trades[symbol] = trade
                        updated = True
                        continue
                        
                    direction = trade["direction"]
                    old_stop = trade["stop_loss"]
                    
                    # Tighten stop-loss to 1.0% distance from current price to manage overnight gap risk
                    if direction == "long":
                        new_stop = max(old_stop, current_price * 0.99)
                    else:
                        new_stop = min(old_stop, current_price * 1.01)
                        
                    if new_stop != old_stop:
                        logger.info(f"🔒 Tightening stop loss for {symbol} ({direction.upper()}) to hold overnight: ${old_stop:.2f} -> ${new_stop:.2f} (Current: ${current_price:.2f})")
                        trade["stop_loss"] = new_stop
                        if "trailing_stop_history" not in trade:
                            trade["trailing_stop_history"] = []
                        trade["trailing_stop_history"].append(new_stop)
                    
                    trade["overnight_tightened"] = True
                    active_trades[symbol] = trade
                    updated = True
                    
            if updated:
                state["active_trades"] = active_trades
                save_state(state)
        else:
            logger.info("⏰ Post-3:45 PM ET. No active positions to manage.")
        return

    # ─── CASE 2: MANAGE EXISTING ACTIVE POSITIONS ───
    if active_trades:
        logger.info(f"🔄 Managing {len(active_trades)} open positions...")
        for symbol in list(active_trades.keys()):
            trade = active_trades[symbol]
            
            # Reset overnight tightened flag during regular trading hours before the 3:45 PM wind-down
            if trade.get("overnight_tightened") and current_time < dt_time(15, 45):
                logger.info(f"🌞 Resetting overnight tightened flag for {symbol} for today's regular session.")
                trade["overnight_tightened"] = False
                
            current_price, trade_ts = get_latest_trade_info(symbol)

            if current_price <= 0.0:
                logger.warning(f"⚠️ Could not retrieve price for {symbol}, skipping update.")
                continue

            # Halted/delisted detection: never evaluate stops against frozen quotes
            if is_trade_stale(trade_ts, market_is_open=True):
                if not trade.get("untradeable"):
                    logger.critical(f"🚫 {symbol} has not traded since {trade_ts} — likely halted or delisted. Flagged untradeable; manual broker-side cleanup required.")
                    trade["untradeable"] = True
                    active_trades[symbol] = trade
                    state["active_trades"] = active_trades
                    save_state(state)
                continue
            elif trade.get("untradeable"):
                logger.info(f"♻️ {symbol} is trading again — clearing untradeable flag.")
                trade["untradeable"] = False

            direction = trade["direction"]
            stop_loss = trade["stop_loss"]
            qty = trade["qty"]
            
            logger.info(f"🔍 Stock {symbol} ({direction.upper()}) | Current: ${current_price:.2f} | Stop Loss: ${stop_loss:.2f}")
            
            # Check stop-loss hit
            hit_stop = False
            if direction == "long" and current_price <= stop_loss:
                hit_stop = True
            elif direction == "short" and current_price >= stop_loss:
                hit_stop = True
                
            if hit_stop:
                exit_side = "sell" if direction == "long" else "buy"
                logger.warning(f"🚨 Stop-Loss Hit for {symbol} at ${current_price:.2f}! Exiting position...")

                # Sync exit qty with the actual broker position to avoid overselling
                try:
                    from tools.alpaca_trading import get_alpaca_client
                    client = get_alpaca_client()
                    broker_pos = client.get_position(symbol)
                    if broker_pos is None:
                        # get_position swallows API errors; confirm flatness via the full list
                        all_positions = client.get_positions()
                        if symbol not in all_positions:
                            logger.warning(f"🧹 Broker confirms no position for {symbol}; removing from local tracking without exit order.")
                            del active_trades[symbol]
                            state["active_trades"] = active_trades
                            save_state(state)
                            continue
                        broker_pos = all_positions[symbol]
                except Exception as pos_err:
                    logger.error(f"❌ Could not verify broker position for {symbol} before exit: {pos_err}. Skipping exit this cycle.")
                    continue

                broker_qty = int(abs(float(broker_pos.get("qty", 0))))
                if broker_qty <= 0:
                    logger.warning(f"🧹 Broker shows zero qty for {symbol}; removing from local tracking without exit order.")
                    del active_trades[symbol]
                    state["active_trades"] = active_trades
                    save_state(state)
                    continue
                if broker_qty < qty:
                    logger.warning(f"⚠️ Qty mismatch for {symbol}: local {qty} vs broker {broker_qty}. Exiting broker qty.")
                    qty = broker_qty
                    trade["qty"] = qty

                fill = place_alpaca_order(symbol, qty, exit_side)

                # Only record the exit if the broker actually confirmed a fill
                if not fill["success"]:
                    logger.error(f"❌ Exit order for {symbol} FAILED — position remains open. Will retry next cycle.")
                    continue

                filled_qty = int(fill["filled_qty"])
                exit_price = fill["filled_avg_price"] or current_price

                pnl = (exit_price - trade["entry_price"]) * filled_qty if direction == "long" else (trade["entry_price"] - exit_price) * filled_qty
                pct_return = (pnl / (trade["entry_price"] * filled_qty)) * 100

                trade_history.append({
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": trade["entry_price"],
                    "exit_price": exit_price,
                    "qty": filled_qty,
                    "pnl": pnl,
                    "return_pct": pct_return,
                    "entry_time": trade["entry_time"],
                    "exit_time": now.isoformat(),
                    "exit_reason": "Stop-Loss Hit"
                })
                logger.info(f"🔴 Exit filled for {symbol} | Realized P&L: ${pnl:+.2f} ({pct_return:+.2f}%)")

                if filled_qty >= qty:
                    del active_trades[symbol]
                else:
                    # Partial exit: keep managing the remainder
                    trade["qty"] = qty - filled_qty
                    active_trades[symbol] = trade
                    logger.warning(f"⚠️ Partial exit for {symbol}: {filled_qty}/{qty} filled. Managing remaining {qty - filled_qty} shares.")

                # Save state immediately
                state["active_trades"] = active_trades
                state["trade_history"] = trade_history
                save_state(state)
                continue
                
            # If trade is in our favor, update trailing stop-loss dynamically based on EMA
            in_favor = False
            if direction == "long" and current_price > trade["highest_price"]:
                trade["highest_price"] = current_price
                in_favor = True
            elif direction == "short" and current_price < trade["lowest_price"]:
                trade["lowest_price"] = current_price
                in_favor = True
                
            if in_favor:
                # Recalculate 5-minute bars and get current EMA & ATR
                bars = fetch_historical_bars(symbol, limit=35)
                ta = calculate_trend_robustness(bars)
                
                if ta["status"] == "success":
                    ema = ta["ema21"]
                    atr = ta["atr"]
                    
                    if direction == "long":
                        new_stop = ema - 1.0 * atr
                        # Trail stop-loss upwards only
                        if new_stop > stop_loss:
                            # Clamp stop-loss within 2.0% of highest price to prevent excessive lock-in loss
                            max_allowed_stop = current_price * 0.985
                            final_stop = min(new_stop, max_allowed_stop)
                            if final_stop > stop_loss:
                                logger.info(f"📈 Trailing Stop Loss up for {symbol} from ${stop_loss:.2f} -> ${final_stop:.2f} (Based on EMA21)")
                                trade["stop_loss"] = final_stop
                                if "trailing_stop_history" not in trade:
                                    trade["trailing_stop_history"] = []
                                trade["trailing_stop_history"].append(final_stop)
                    else:
                        new_stop = ema + 1.0 * atr
                        # Trail stop-loss downwards only
                        if new_stop < stop_loss:
                            # Clamp short stop-loss
                            min_allowed_stop = current_price * 1.015
                            final_stop = max(new_stop, min_allowed_stop)
                            if final_stop < stop_loss:
                                logger.info(f"📉 Trailing Stop Loss down for {symbol} from ${stop_loss:.2f} -> ${final_stop:.2f} (Based on EMA21)")
                                trade["stop_loss"] = final_stop
                                if "trailing_stop_history" not in trade:
                                    trade["trailing_stop_history"] = []
                                trade["trailing_stop_history"].append(final_stop)
                                
                # Save status
                active_trades[symbol] = trade
                state["active_trades"] = active_trades
                save_state(state)

    # ─── CASE 3: SCAN AND ENTER NEW MOMENTUM TRADES ───
    # Untradeable (halted/delisted) positions can't be exited, so they don't consume slots
    tradeable_count = sum(1 for t in active_trades.values() if not t.get("untradeable"))
    if tradeable_count < 2:
        slots_available = 2 - tradeable_count
        logger.info(f"🔍 {slots_available} trade slot(s) available. Scanning Alpaca movers...")
        
        try:
            # Query Top daily movers from Alpaca screener API
            movers_url = "https://data.alpaca.markets/v1beta1/screener/stocks/movers?top=20"
            res = requests.get(movers_url, headers=headers)
            
            if res.status_code != 200:
                logger.error(f"❌ Failed to fetch movers from Alpaca screener: {res.text}")
                return
                
            movers_data = res.json()
            gainers = movers_data.get("gainers", [])
            losers = movers_data.get("losers", [])
            
            # Build unified candidates list
            candidates = []
            for g in gainers:
                candidates.append({
                    "symbol": g["symbol"],
                    "percent_change": float(g["percent_change"]),
                    "price": float(g["price"]),
                    "direction": "long"
                })
            for l in losers:
                candidates.append({
                    "symbol": l["symbol"],
                    "percent_change": float(l["percent_change"]), # negative or positive
                    "price": float(l["price"]),
                    "direction": "short"
                })
                
            # Filter candidates
            filtered_candidates = []
            for c in candidates:
                symbol = c["symbol"]
                price = c["price"]
                direction = c["direction"]
                
                # 1. Price constraint ($5 to $500)
                if not (5.0 <= price <= 500.0):
                    continue
                    
                # 2. Exclude symbols already holding
                if symbol in active_trades:
                    continue
                    
                # 3. If short, make sure the asset is easy to borrow / shortable
                if direction == "short" and not is_asset_shortable(symbol):
                    continue
                    
                filtered_candidates.append(c)
                
            # Classify by absolute percent change descending
            filtered_candidates.sort(key=lambda x: abs(x["percent_change"]), reverse=True)
            
            # Select the top 10 most changed stocks
            top_10 = filtered_candidates[:10]
            logger.info(f"🔥 Top 10 most changed stock candidates (after filters): {[c['symbol'] for c in top_10]}")
            
            # Fetch bars and calculate technical indicators to verify robust momentum
            scored_candidates = []
            for c in top_10:
                symbol = c["symbol"]
                direction = c["direction"]
                
                logger.info(f"   📡 Fetching historical bars and calculating trend robustness for {symbol}...")
                bars = fetch_historical_bars(symbol, limit=35)
                ta = calculate_trend_robustness(bars)
                
                if ta["status"] == "success":
                    up_score = ta["up_score"]
                    down_score = ta["down_score"]
                    
                    if direction == "long" and up_score >= 60:
                        scored_candidates.append({
                            **c,
                            "robustness_score": up_score,
                            "ta_data": ta
                        })
                        logger.info(f"      ✅ {symbol} LONG setup is robust with score: {up_score}/100")
                    elif direction == "short" and down_score >= 60:
                        scored_candidates.append({
                            **c,
                            "robustness_score": down_score,
                            "ta_data": ta
                        })
                        logger.info(f"      ✅ {symbol} SHORT setup is robust with score: {down_score}/100")
                    else:
                        logger.info(f"      ❌ {symbol} failed robust trend threshold (Bullish: {up_score}, Bearish: {down_score})")
                        
            # Sort scored candidates by robustness score descending
            scored_candidates.sort(key=lambda x: x["robustness_score"], reverse=True)
            
            # Enter trade for the top candidates
            for idx in range(min(slots_available, len(scored_candidates))):
                item = scored_candidates[idx]
                symbol = item["symbol"]
                direction = item["direction"]
                score = item["robustness_score"]
                ta = item["ta_data"]
                
                # Fetch entry price (real-time) and reject stale/halted quotes
                entry_price, entry_ts = get_latest_trade_info(symbol)
                if entry_price <= 0.0:
                    entry_price = item["price"] # fallback to screener price
                    entry_ts = None
                if is_trade_stale(entry_ts, market_is_open=True):
                    logger.warning(f"⚠️ Skipping {symbol}: last trade is stale ({entry_ts}) — possibly halted/delisted.")
                    continue

                # Trade size constraint: $50,000
                qty = int(50000 / entry_price)
                if qty <= 0:
                    logger.warning(f"⚠️ Quantity of shares for {symbol} is 0 or less, skipping trade.")
                    continue

                # Place Alpaca order and verify the actual fill
                order_side = "buy" if direction == "long" else "sell"
                fill = place_alpaca_order(symbol, qty, order_side)

                if fill["success"]:
                    qty = int(fill["filled_qty"])
                    if fill["filled_avg_price"]:
                        entry_price = fill["filled_avg_price"]
                    # Calculate initial Stop-Loss based on recent EMA
                    # Initial Stop: EMA(21) ± 1.0 * ATR, clamped between 0.5% and 2.0% of the entry price
                    ema = ta["ema21"]
                    atr = ta["atr"]
                    
                    if direction == "long":
                        stop_dist = entry_price - (ema - 1.0 * atr)
                        # Clamp stop distance (0.5% to 2.0%)
                        min_dist = entry_price * 0.005
                        max_dist = entry_price * 0.02
                        clamped_dist = max(min_dist, min(max_dist, stop_dist))
                        stop_loss = entry_price - clamped_dist
                    else:
                        stop_dist = (ema + 1.0 * atr) - entry_price
                        min_dist = entry_price * 0.005
                        max_dist = entry_price * 0.02
                        clamped_dist = max(min_dist, min(max_dist, stop_dist))
                        stop_loss = entry_price + clamped_dist
                        
                    logger.info(f"🚀 ENTERING {direction.upper()} POSITION: {qty} shares of {symbol} | Entry: ${entry_price:.2f} | Stop-Loss Set: ${stop_loss:.2f} (Score: {score}/100)")
                    
                    # Record state
                    active_trades[symbol] = {
                        "symbol": symbol,
                        "direction": direction,
                        "qty": qty,
                        "entry_price": entry_price,
                        "stop_loss": stop_loss,
                        "highest_price": entry_price,
                        "lowest_price": entry_price,
                        "entry_time": now.isoformat(),
                        "trailing_stop_history": [stop_loss],
                        "robustness_score": score
                    }
                    
                    state["active_trades"] = active_trades
                    save_state(state)
                else:
                    logger.error(f"❌ Failed to place order for {symbol}")
                    
        except Exception as scan_err:
            logger.error(f"❌ Error during scanning and trade entry phase: {scan_err}")
            traceback.print_exc()


# ==================== BROKER STATE RECONCILIATION ====================

def reconcile_with_broker(dry_run: bool = False) -> dict:
    """
    Reconcile the local state file with actual Alpaca broker positions.

    - Ghosts: tracked locally but flat at the broker -> moved to trade history.
    - Orphans: held at the broker but untracked locally -> adopted with a fresh
      protective stop so they get stop-loss management instead of drifting.
    - Qty mismatches: local qty is synced down/up to the broker's actual qty.

    Runs at startup and periodically during the session. Never places orders.
    """
    state = load_state()
    active_trades = state.get("active_trades", {})
    trade_history = state.get("trade_history", [])
    actions = []

    try:
        from tools.alpaca_trading import get_alpaca_client
        client = get_alpaca_client()
        broker_positions = client.get_positions()
    except Exception as e:
        logger.error(f"❌ Reconciliation skipped — could not fetch broker positions: {e}")
        return {"actions": actions, "error": str(e)}

    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)

    # ─── 1) Ghost cleanup: in state, not at broker ───
    for symbol in list(active_trades.keys()):
        if symbol in broker_positions:
            continue
        trade = active_trades[symbol]
        exit_price = get_latest_trade_price(symbol) or None
        pnl = None
        if exit_price:
            pnl = (exit_price - trade["entry_price"]) * trade["qty"] if trade["direction"] == "long" \
                else (trade["entry_price"] - exit_price) * trade["qty"]
        logger.warning(f"🧹 RECONCILE: {symbol} tracked locally but FLAT at broker. Removing from active trades.")
        actions.append(f"removed ghost {symbol}")
        trade_history.append({
            "symbol": symbol,
            "direction": trade["direction"],
            "entry_price": trade["entry_price"],
            "exit_price": exit_price,
            "qty": trade["qty"],
            "pnl": pnl,
            "return_pct": None,
            "entry_time": trade["entry_time"],
            "exit_time": now.isoformat(),
            "exit_reason": "Reconciled: no broker position"
        })
        del active_trades[symbol]

    # ─── 2) Orphan adoption: at broker, not in state ───
    for symbol, pos in broker_positions.items():
        if symbol in active_trades:
            continue
        qty = int(abs(float(pos["qty"])))
        if qty <= 0:
            continue
        direction = "short" if ("short" in str(pos.get("side", "")).lower() or float(pos["qty"]) < 0) else "long"
        entry_price = float(pos["avg_entry_price"])
        current_price = float(pos.get("current_price") or 0) or get_latest_trade_price(symbol)

        # Initial protective stop: EMA21 ± ATR (clamped 0.5%-2%), fallback to 1.5%
        stop_loss = None
        if current_price and current_price > 0:
            try:
                bars = fetch_historical_bars(symbol, limit=35)
                ta = calculate_trend_robustness(bars)
                if ta["status"] == "success":
                    if direction == "long":
                        raw_dist = current_price - (ta["ema21"] - 1.0 * ta["atr"])
                    else:
                        raw_dist = (ta["ema21"] + 1.0 * ta["atr"]) - current_price
                    dist = max(current_price * 0.005, min(current_price * 0.02, raw_dist))
                    stop_loss = current_price - dist if direction == "long" else current_price + dist
            except Exception as ta_err:
                logger.warning(f"⚠️ TA-based stop failed for adopted {symbol}: {ta_err}. Using 1.5% fallback.")
            if stop_loss is None:
                stop_loss = current_price * 0.985 if direction == "long" else current_price * 1.015

        logger.warning(f"🔗 RECONCILE: Adopting untracked broker position {symbol} ({direction.upper()} {qty} @ ${entry_price:.2f}) with protective stop ${stop_loss:.2f}")
        actions.append(f"adopted orphan {symbol} ({direction} {qty})")
        active_trades[symbol] = {
            "symbol": symbol,
            "direction": direction,
            "qty": qty,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "highest_price": current_price or entry_price,
            "lowest_price": current_price or entry_price,
            "entry_time": now.isoformat(),
            "trailing_stop_history": [stop_loss],
            "robustness_score": 0,
            "adopted": True
        }

    # ─── 3) Quantity sync for mutually tracked positions ───
    for symbol, trade in active_trades.items():
        if symbol not in broker_positions:
            continue
        broker_qty = int(abs(float(broker_positions[symbol]["qty"])))
        if broker_qty > 0 and broker_qty != int(trade["qty"]):
            logger.warning(f"🔧 RECONCILE: Qty mismatch for {symbol}: local {trade['qty']} vs broker {broker_qty}. Syncing to broker.")
            actions.append(f"synced qty {symbol} {trade['qty']} -> {broker_qty}")
            trade["qty"] = broker_qty
            active_trades[symbol] = trade

    if actions and not dry_run:
        state["active_trades"] = active_trades
        state["trade_history"] = trade_history
        save_state(state)

    if actions:
        logger.info(f"✅ Reconciliation {'(DRY RUN) ' if dry_run else ''}complete: {len(actions)} action(s): {actions}")
    else:
        logger.info("✅ Reconciliation complete: state matches broker.")
    return {"actions": actions}


# ==================== MAIN SERVICE ENGINE ====================

async def main_trading_loop():
    """Main trader service daemon loop - wakes up every 2 minutes to trade"""
    global shutdown_requested
    
    logger.info("⚡ Active Day Trading Momentum Strategy Started")
    logger.info("📈 Monitoring Alpaca API every 2 minutes during market hours.")

    # Reconcile local state with actual broker positions at startup
    reconcile_with_broker()
    cycle_counter = 0

    # Simple loop
    while not shutdown_requested:
        try:
            # Check market hours
            from tools.market_schedule import is_market_hours, get_next_market_open, format_time_until
            is_open, session_type = is_market_hours()
            
            # Double-check if today is actually a trading session
            if not is_open:
                import pytz
                from datetime import time as dt_t
                eastern = pytz.timezone('US/Eastern')
                now_eastern = datetime.now(eastern)
                # Check weekends or holiday logic
                # We will sleep or log closed
                logger.info(f"💤 Market is CLOSED. Current Eastern Time: {now_eastern.strftime('%I:%M:%S %p ET')}")
                
                next_open = get_next_market_open()
                if next_open:
                    time_until = format_time_until(next_open)
                    logger.info(f"⏭️ Next market session opens at: {next_open.strftime('%A, %B %d at %I:%M %p ET')} ({time_until} remaining)")
                    # Calculate wait time up to wake up (5 minutes before open)
                    wake_time = next_open - timedelta(minutes=5)
                    sleep_seconds = (wake_time - now_eastern).total_seconds()
                    
                    if sleep_seconds > 60:
                        logger.info(f"😴 Going into deep sleep mode for {int(sleep_seconds)} seconds...")
                        # Sleep in increments of 1 second so we can respond to shutdown
                        for _ in range(int(sleep_seconds)):
                            if shutdown_requested:
                                break
                            await asyncio.sleep(1)
                        continue
                
                logger.info("⏳ Waiting 60 seconds before next schedule check...")
                await asyncio.sleep(60)
                continue
                
            # If market is open, run strategy logic
            logger.info("🟢 Market is OPEN. Executing strategy cycle...")
            start_cycle_time = time.time()

            # Periodically re-reconcile state with the broker (~every 30 minutes)
            cycle_counter += 1
            if cycle_counter % RECONCILE_INTERVAL_CYCLES == 0:
                reconcile_with_broker()

            await execute_trading_strategy()
            
            # Calculate duration and sleep for remaining of 2 minutes
            cycle_duration = time.time() - start_cycle_time
            sleep_remaining = max(1, 120 - int(cycle_duration))
            
            logger.info(f"⏳ Strategy cycle completed in {cycle_duration:.1f}s. Sleeping for {sleep_remaining}s until next check...")
            
            for _ in range(sleep_remaining):
                 if shutdown_requested:
                      break
                 await asyncio.sleep(1)
                 
        except KeyboardInterrupt:
            shutdown_requested = True
            break
        except Exception as main_err:
            logger.error(f"❌ Unexpected exception inside main loop: {main_err}")
            traceback.print_exc()
            logger.info("⚠️ Attempting recovery in 30 seconds...")
            await asyncio.sleep(30)
            
    # Cleanup on exit
    logger.info("🧹 Gracefully winding down active trading program...")
    logger.info("👋 Good bye!")


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run loop
    try:
        asyncio.run(main_trading_loop())
    except KeyboardInterrupt:
        logger.info("Program terminated.")
