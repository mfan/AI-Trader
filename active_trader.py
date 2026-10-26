#!/usr/bin/env python3
"""
Active Trader — ETF Time-Series Momentum (Jansen "Machine Learning for Trading" methodology)

Strategy selected by honest walk-forward research (see ML_STRATEGY_REPORT.md):
- Three cross-sectional ML variants (mixed/momentum/reversal) showed NO edge (IC ~ 0)
  and were rejected per the book's evidence discipline.
- The book's surviving case study — ETF time-series momentum — showed a robust
  out-of-sample edge: Sharpe 1.56, +34.6%/yr, -15.5% max DD (2024-06 → 2026-10),
  validated across parameter perturbations.

Live rules (all a priori, book-standard):
- Universe: 10 liquid sector/asset ETFs (XLK XLF XLE XLV SMH SOXX ARKK TLT GLD IWM)
- Signal: 252-day momentum skipping the most recent 21 days (classic 12-1)
- Portfolio: top-3 ETFs with POSITIVE momentum; flat if none; inverse-vol sized
- Rebalance: daily membership check, 2%-of-equity band (turnover/cost control)
- Risk: 2.5xATR disaster stops (2-min monitoring), -8% monthly drawdown breaker
- Execution: verified fills only; broker reconciliation at startup
"""

import os
import sys
import json
import time
import asyncio
import signal
import logging
import traceback
from datetime import datetime, time as dt_time, timedelta

import numpy as np
import pandas as pd
import pytz
import requests
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

log_dir = os.path.join(project_root, "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'active_trader_ml.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('MLTrader')

STATE_FILE = os.path.join(project_root, "data", "ml_strategy_state.json")
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

# ─── Strategy parameters (a priori canonical 12-1 momentum, NOT grid-searched) ───
ETF_UNIVERSE = ["XLK", "XLF", "XLE", "XLV", "SMH", "SOXX", "ARKK", "TLT", "GLD", "IWM"]
MOM_LOOKBACK = 252           # 12-month momentum (canonical horizon, book case study)
MOM_SKIP = 21                # skip most recent month (avoid short-term reversal)
TOP_K = 3                    # portfolio size
MAX_WEIGHT_PER_NAME = 0.35   # concentration cap
REBALANCE_BAND = 0.02        # trade only legs drifting > 2% of equity
DISASTER_STOP_ATR = 2.5      # per-name disaster stop distance (x ATR14 daily)
MONTHLY_DD_LIMIT = 0.08      # flatten + halt for the month beyond -8%

shutdown_requested = False
headers = {
    "APCA-API-KEY-ID": os.getenv('ALPACA_API_KEY'),
    "APCA-API-SECRET-KEY": os.getenv('ALPACA_SECRET_KEY'),
    "accept": "application/json"
}


def signal_handler(sig, frame):
    global shutdown_requested
    if shutdown_requested:
        sys.exit(1)
    logger.info("⚠️ Shutdown signal received. Gracefully cleaning up...")
    shutdown_requested = True


# ==================== STATE ====================

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
            state.setdefault("positions", {})
            state.setdefault("history", [])
            state.setdefault("month_start_equity", None)
            state.setdefault("halted_until", None)
            return state
        except Exception as e:
            logger.error(f"❌ State load failed: {e}; starting clean.")
    return {"positions": {}, "history": [], "month_start_equity": None, "halted_until": None}


def save_state(state: dict):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"❌ State save failed: {e}")


# ==================== MARKET DATA / BROKER HELPERS ====================

def get_latest_trade_price(symbol: str) -> float:
    try:
        url = f"https://data.alpaca.markets/v2/stocks/{symbol}/trades/latest"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            t = r.json().get("trade")
            if t:
                return float(t.get("p", 0.0))
    except Exception as e:
        logger.debug(f"⚠️ price fetch failed for {symbol}: {e}")
    return 0.0


def get_account_equity() -> float:
    from tools.alpaca_trading import get_alpaca_client
    acct = get_alpaca_client().get_account()
    return float(acct["equity"])


def get_broker_positions() -> dict:
    from tools.alpaca_trading import get_alpaca_client
    return get_alpaca_client().get_positions()


def place_order_verified(symbol: str, qty: int, side: str, fill_timeout: int = 30) -> dict:
    """Submit market order and verify the actual fill (never trust submission)."""
    result = {"success": False, "filled_qty": 0.0, "filled_avg_price": None}
    try:
        from tools.alpaca_trading import get_alpaca_client
        client = get_alpaca_client()
        logger.info(f"📡 {side.upper()} {qty} {symbol} ...")
        submit = client.buy_market(symbol, qty) if side.lower() == "buy" else client.sell_market(symbol, qty)
        if not submit or not submit.get("success"):
            logger.error(f"❌ submit failed {symbol}: {submit}")
            return result
        oid = submit["order_id"]
        deadline = time.time() + fill_timeout
        order = None
        while time.time() < deadline:
            order = client.get_order(oid)
            if order is None or order.get("status") in ("filled", "canceled", "expired", "rejected"):
                break
            time.sleep(0.5)
        if order is None:
            return result
        if order.get("status") != "filled":
            try:
                client.cancel_order(oid)
                time.sleep(1.0)
                order = client.get_order(oid) or order
            except Exception:
                pass
        fq = float(order.get("filled_qty") or 0)
        if fq <= 0:
            logger.error(f"❌ {symbol} filled 0 shares (status={order.get('status')})")
            return result
        result.update(success=True, filled_qty=fq, filled_avg_price=order.get("filled_avg_price"))
        logger.info(f"✅ {side.upper()} {symbol} filled {fq}/{qty} @ ${order.get('filled_avg_price')}")
    except Exception as e:
        logger.error(f"❌ order exception {symbol}: {e}")
    return result


# ==================== DAILY SIGNAL & REBALANCE ====================

def generate_target_portfolio(equity: float) -> dict:
    """
    Daily TSMOM pipeline: refresh data -> 12-1 momentum per ETF -> top-3 positive
    -> inverse-vol weights. Returns {symbol: weight} (fractions of equity).
    Empty dict = flat (no positive-momentum ETFs).
    """
    from tools.ml_data import download_daily_bars, load_universe

    logger.info("📦 Refreshing daily bars (incremental)...")
    download_daily_bars(ETF_UNIVERSE, start="2023-01-01")
    universe = load_universe(ETF_UNIVERSE, min_history_days=MOM_LOOKBACK + MOM_SKIP + 30)

    today_et = datetime.now(pytz.timezone('US/Eastern')).date()
    signals = {}
    vols = {}
    asof = None
    for sym, df in universe.items():
        c = df["close"]
        # Defensive: never use today's partial bar even if one slipped into the cache
        c = c[c.index.date < today_et]
        if len(c) < MOM_LOOKBACK + 1:
            continue
        asof = c.index[-1]
        sig = float(c.iloc[-1 - MOM_SKIP] / c.iloc[-1 - MOM_LOOKBACK] - 1)
        signals[sym] = sig
        vols[sym] = float(c.pct_change(fill_method=None).rolling(21).std().iloc[-1])

    if not signals:
        logger.error("❌ No signals computed; no trades.")
        return {}

    ranked = sorted(signals.items(), key=lambda kv: kv[1], reverse=True)
    logger.info(f"📊 12-1 momentum @ {asof.date()}: " +
                ", ".join(f"{s} {v:+.1%}" for s, v in ranked))

    top = [s for s, v in ranked[:TOP_K] if v > 0]
    logger.info(f"🏆 Selected (positive momentum): {top if top else 'NONE — flat'}")

    inv = {s: 1.0 / vols[s] for s in top if vols.get(s, 0) > 0}
    total = sum(inv.values())
    if total <= 0:
        return {}
    weights = {s: min(0.95 * v / total, MAX_WEIGHT_PER_NAME) for s, v in inv.items()}
    logger.info(f"⚖️ Target weights: { {s: f'{w:.1%}' for s, w in weights.items()} }")
    return weights


def rebalance(state: dict, targets: dict, equity: float):
    """
    Diff target vs current holdings and trade the legs that drifted beyond the band.
    Sells first (frees cash), then buys. All fills verified.
    """
    positions = state["positions"]

    # Current dollar value per held symbol (from state; broker is synced on entry/exit)
    current_syms = set(positions.keys())
    target_syms = set(targets.keys())

    # 1) Exits: held but no longer targeted
    for sym in sorted(current_syms - target_syms):
        qty = positions[sym]["qty"]
        fill = place_order_verified(sym, qty, "sell")
        if fill["success"]:
            px = fill["filled_avg_price"] or positions[sym]["entry_price"]
            pnl = (px - positions[sym]["entry_price"]) * fill["filled_qty"]
            state["history"].append({
                "symbol": sym, "qty": fill["filled_qty"], "entry_price": positions[sym]["entry_price"],
                "exit_price": px, "pnl": pnl, "exit_time": datetime.now(pytz.timezone('US/Eastern')).isoformat(),
                "exit_reason": "Signal rotation"
            })
            logger.info(f"🔴 EXIT {sym} | P&L ${pnl:+,.2f}")
            remaining = qty - int(fill["filled_qty"])
            if remaining > 0:
                positions[sym]["qty"] = remaining
            else:
                del positions[sym]

    # 2) Entries / adjustments
    for sym, w in targets.items():
        target_dollars = w * equity
        current_qty = positions.get(sym, {}).get("qty", 0)
        price = get_latest_trade_price(sym)
        if price <= 0:
            logger.warning(f"⚠️ No price for {sym}; skipping")
            continue
        current_dollars = current_qty * price
        drift = target_dollars - current_dollars

        if abs(drift) < REBALANCE_BAND * equity:
            continue  # inside rebalance band — skip to control turnover

        qty_delta = int(abs(drift) / price)
        if qty_delta <= 0:
            continue

        if drift > 0:
            fill = place_order_verified(sym, qty_delta, "buy")
            if fill["success"]:
                fq = int(fill["filled_qty"])
                px = fill["filled_avg_price"] or price
                # ATR-based disaster stop from cached daily bars
                atr_stop = _disaster_stop(sym, px)
                if sym in positions:
                    old = positions[sym]
                    tot = old["qty"] + fq
                    old["entry_price"] = (old["entry_price"] * old["qty"] + px * fq) / tot
                    old["qty"] = tot
                    old["stop"] = max(old.get("stop", 0), atr_stop)
                else:
                    positions[sym] = {"qty": fq, "entry_price": px, "stop": atr_stop,
                                      "entry_time": datetime.now(pytz.timezone('US/Eastern')).isoformat()}
                logger.info(f"🟢 ENTER/ADD {sym} {fq} sh @ ${px:.2f} | stop ${positions[sym]['stop']:.2f}")
        else:
            fill = place_order_verified(sym, qty_delta, "sell")
            if fill["success"]:
                fq = int(fill["filled_qty"])
                remaining = current_qty - fq
                if remaining > 0:
                    positions[sym]["qty"] = remaining
                else:
                    px = fill["filled_avg_price"] or price
                    pnl = (px - positions[sym]["entry_price"]) * fq
                    state["history"].append({
                        "symbol": sym, "qty": fq, "entry_price": positions[sym]["entry_price"],
                        "exit_price": px, "pnl": pnl,
                        "exit_time": datetime.now(pytz.timezone('US/Eastern')).isoformat(),
                        "exit_reason": "Weight reduction"
                    })
                    logger.info(f"🔴 REDUCE->FLAT {sym} | P&L ${pnl:+,.2f}")
                    del positions[sym]

    save_state(state)


def _disaster_stop(symbol: str, entry_price: float) -> float:
    """2.5 x ATR(14) below entry, from cached daily bars."""
    try:
        from tools.ml_data import _cache_path
        df = pd.read_csv(_cache_path(symbol), parse_dates=["timestamp"])
        h, l, c = df["high"], df["low"], df["close"]
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        return round(entry_price - DISASTER_STOP_ATR * atr, 2)
    except Exception:
        return round(entry_price * 0.95, 2)  # fallback: -5%


# ==================== RISK ====================

def check_circuit_breaker(state: dict, equity: float, now_et) -> bool:
    """Monthly drawdown breaker: -8% from month-start equity -> flatten + halt."""
    month_key = now_et.strftime("%Y-%m")
    if state.get("month_key") != month_key:
        state["month_key"] = month_key
        state["month_start_equity"] = equity
        state["halted_until"] = None
        save_state(state)
        logger.info(f"📅 New month baseline equity: ${equity:,.2f}")
        return False

    if state.get("halted_until"):
        logger.warning(f"🛑 Trading halted until {state['halted_until']} (drawdown breaker)")
        return True

    base = state.get("month_start_equity") or equity
    dd = equity / base - 1
    if dd <= -MONTHLY_DD_LIMIT:
        logger.critical(f"🚨 MONTHLY DRAWDOWN {dd:.1%} exceeds -{MONTHLY_DD_LIMIT:.0%}. Flattening and halting until next month.")
        for sym in list(state["positions"].keys()):
            qty = state["positions"][sym]["qty"]
            fill = place_order_verified(sym, qty, "sell")
            if fill["success"] and int(fill["filled_qty"]) >= qty:
                del state["positions"][sym]
        state["halted_until"] = "next_month"
        save_state(state)
        return True
    return False


def monitor_disaster_stops(state: dict):
    """Every-cycle check: exit any position that breached its ATR disaster stop."""
    for sym in list(state["positions"].keys()):
        pos = state["positions"][sym]
        price = get_latest_trade_price(sym)
        if price <= 0:
            continue
        if price <= pos["stop"]:
            logger.warning(f"🚨 DISASTER STOP {sym}: ${price:.2f} <= ${pos['stop']:.2f}")
            fill = place_order_verified(sym, pos["qty"], "sell")
            if fill["success"]:
                px = fill["filled_avg_price"] or price
                pnl = (px - pos["entry_price"]) * fill["filled_qty"]
                state["history"].append({
                    "symbol": sym, "qty": fill["filled_qty"], "entry_price": pos["entry_price"],
                    "exit_price": px, "pnl": pnl,
                    "exit_time": datetime.now(pytz.timezone('US/Eastern')).isoformat(),
                    "exit_reason": "Disaster stop"
                })
                logger.info(f"🔴 STOP EXIT {sym} | P&L ${pnl:+,.2f}")
                remaining = pos["qty"] - int(fill["filled_qty"])
                if remaining > 0:
                    pos["qty"] = remaining
                else:
                    del state["positions"][sym]
                save_state(state)


def reconcile_with_broker(state: dict):
    """Sync state positions with actual broker positions (runs at startup)."""
    try:
        broker = get_broker_positions()
    except Exception as e:
        logger.error(f"❌ reconcile failed: {e}")
        return
    changed = False
    for sym in list(state["positions"].keys()):
        if sym not in broker:
            logger.warning(f"🧹 RECONCILE: {sym} not at broker; dropping from state")
            del state["positions"][sym]
            changed = True
        else:
            bq = int(abs(float(broker[sym]["qty"])))
            if bq != state["positions"][sym]["qty"]:
                logger.warning(f"🔧 RECONCILE: {sym} qty {state['positions'][sym]['qty']} -> {bq}")
                state["positions"][sym]["qty"] = bq
                changed = True
    for sym, pos in broker.items():
        if sym not in state["positions"]:
            qty = int(abs(float(pos["qty"])))
            px = float(pos["avg_entry_price"])
            logger.warning(f"🔗 RECONCILE: adopting {sym} ({qty} @ ${px})")
            state["positions"][sym] = {"qty": qty, "entry_price": px, "stop": _disaster_stop(sym, px),
                                       "entry_time": datetime.now(pytz.timezone('US/Eastern')).isoformat()}
            changed = True
    if changed:
        save_state(state)
    logger.info(f"✅ Reconcile: {len(state['positions'])} tracked positions match broker")


# ==================== MAIN LOOP ====================

async def main_loop():
    logger.info("⚡ ETF Time-Series Momentum Strategy Started (Jansen methodology)")
    logger.info(f"📐 Params: top-{TOP_K}, 12-1 momentum ({MOM_LOOKBACK}d skip {MOM_SKIP}d), max_w={MAX_WEIGHT_PER_NAME:.0%}, band={REBALANCE_BAND:.0%}")

    state = load_state()
    reconcile_with_broker(state)

    last_signal_date = None

    while not shutdown_requested:
        try:
            from tools.market_schedule import is_market_hours, get_next_market_open, format_time_until
            is_open, _ = is_market_hours()
            eastern = pytz.timezone('US/Eastern')
            now_et = datetime.now(eastern)

            if not is_open:
                next_open = get_next_market_open()
                if next_open:
                    logger.info(f"💤 Market closed. Next open: {next_open.strftime('%a %b %d %I:%M %p ET')} ({format_time_until(next_open)})")
                    wake = next_open - timedelta(minutes=5)
                    secs = (wake - now_et).total_seconds()
                    if secs > 60:
                        for _ in range(int(secs)):
                            if shutdown_requested:
                                break
                            await asyncio.sleep(1)
                        continue
                await asyncio.sleep(60)
                continue

            # ── Market is open ──
            equity = get_account_equity()

            # Circuit breaker first
            if check_circuit_breaker(state, equity, now_et):
                await asyncio.sleep(300)
                continue

            # Daily signal + rebalance once per day, after 9:35 AM ET
            today = now_et.date()
            if now_et.time() >= dt_time(9, 35) and last_signal_date != today:
                logger.info("📊 Running daily signal pipeline...")
                try:
                    targets = generate_target_portfolio(equity)
                    rebalance(state, targets, equity)
                    last_signal_date = today
                except Exception as sig_err:
                    logger.error(f"❌ Signal pipeline failed: {sig_err}")
                    traceback.print_exc()

            # Continuous risk: disaster stops
            monitor_disaster_stops(state)

            await asyncio.sleep(120)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"❌ main loop error: {e}")
            traceback.print_exc()
            await asyncio.sleep(30)

    logger.info("🧹 ML Trader winding down. Goodbye!")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass
