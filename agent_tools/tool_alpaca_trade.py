"""
Alpaca-Integrated Trading Tool for MCP

This MCP tool provides AI agents with real trading capabilities through Alpaca's API.
It replaces the file-based simulation with actual market orders and position management.
"""

from fastmcp import FastMCP
import sys
import os
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tools.alpaca_trading import get_alpaca_client, AlpacaTradingClient
from tools.general_tools import get_config_value, write_config_value
from tools.trade_thesis_db import get_trade_thesis_db
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("AlpacaTradeTools")

# Initialize Alpaca client
try:
    alpaca_client = get_alpaca_client()
    print("✅ Alpaca trading client initialized")
except Exception as e:
    print(f"⚠️ Warning: Alpaca client not initialized: {e}")
    alpaca_client = None


def _is_extended_hours() -> bool:
    """
    Auto-detect if we're in extended hours (pre-market or post-market)
    
    Returns:
        True if in pre-market or post-market, False if in regular hours or closed
    """
    try:
        import pytz
        from datetime import time
        
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
        current_time = now.time()
        
        # Skip weekends
        if now.weekday() >= 5:
            return False
        
        # Define market hours
        pre_market_start = time(4, 0)
        regular_start = time(9, 30)
        regular_end = time(16, 0)
        post_market_end = time(20, 0)
        
        # Check if in pre-market (4:00 AM - 9:30 AM ET)
        if pre_market_start <= current_time < regular_start:
            return True
        
        # Check if in post-market (4:00 PM - 8:00 PM ET)
        if regular_end <= current_time < post_market_end:
            return True
        
        # Regular hours or closed
        return False
        
    except Exception as e:
        print(f"⚠️ Warning: Could not detect market session: {e}")
        # Fail safe: return False (don't use extended hours if unsure)
        return False


@mcp.tool()
def get_account_info() -> Dict[str, Any]:
    """
    Get current account information from Alpaca
    
    Returns account details including:
    - Available cash
    - Buying power
    - Total equity
    - Portfolio value
    - Trading status
    
    Returns:
        Dict containing account information
        
    Example:
        >>> info = get_account_info()
        >>> print(f"Cash: ${info['cash']:.2f}")
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
    try:
        account = alpaca_client.get_account()
        return {
            "success": True,
            "account": account
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def get_positions() -> Dict[str, Any]:
    """
    Get all current positions from Alpaca account
    
    Returns information about all open positions including:
    - Symbol and quantity
    - Average entry price
    - Current market value
    - Unrealized profit/loss
    
    Returns:
        Dict with positions information
        
    Example:
        >>> positions = get_positions()
        >>> for symbol, pos in positions['positions'].items():
        >>>     print(f"{symbol}: {pos['qty']} shares")
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
    try:
        positions = alpaca_client.get_positions()
        account = alpaca_client.get_account()
        
        return {
            "success": True,
            "positions": positions,
            "cash": account["cash"],
            "total_equity": account["equity"]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def get_position(symbol: str) -> Dict[str, Any]:
    """
    Get position information for a specific symbol
    
    Args:
        symbol: Stock symbol (e.g., "AAPL", "MSFT")
        
    Returns:
        Position details or None if no position exists
        
    Example:
        >>> pos = get_position("AAPL")
        >>> if pos['success'] and pos['position']:
        >>>     print(f"Holding {pos['position']['qty']} shares")
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
    try:
        position = alpaca_client.get_position(symbol)
        return {
            "success": True,
            "symbol": symbol,
            "position": position  # None if no position
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol
        }


@mcp.tool()
def get_stock_price(symbol: str) -> Dict[str, Any]:
    """
    Get current market price for a stock
    
    Args:
        symbol: Stock symbol (e.g., "AAPL")
        
    Returns:
        Current price information
        
    Example:
        >>> price_info = get_stock_price("AAPL")
        >>> print(f"Current price: ${price_info['price']:.2f}")
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
    try:
        price = alpaca_client.get_latest_price(symbol)
        return {
            "success": True,
            "symbol": symbol,
            "price": price,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol
        }


@mcp.tool()
def get_stock_prices(symbols: List[str]) -> Dict[str, Any]:
    """
    Get current market prices for multiple stocks
    
    Args:
        symbols: List of stock symbols (e.g., ["AAPL", "MSFT", "GOOGL"])
        
    Returns:
        Dict mapping symbols to prices
        
    Example:
        >>> prices = get_stock_prices(["AAPL", "MSFT"])
        >>> for sym, price in prices['prices'].items():
        >>>     print(f"{sym}: ${price:.2f}")
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
    try:
        prices = alpaca_client.get_latest_prices(symbols)
        return {
            "success": True,
            "prices": prices,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbols": symbols
        }


@mcp.tool()
def buy(
    symbol: str,
    quantity: int,
    thesis: str,
    support_price: float,
    resistance_price: float,
    stop_loss_price: float,
    target_price: float,
    order_type: str = "market",
    limit_price: float = None,
    extended_hours: bool = None,
    market_regime: str = None,
    technical_setup: str = None,
    confidence_level: int = None
) -> Dict[str, Any]:
    """
    Place a buy order for a stock with MANDATORY trading thesis and price levels
    
    CRITICAL: Every trade MUST have:
    1. Clear thesis explaining WHY entering this trade
    2. Support level (price floor)
    3. Resistance level (price ceiling)
    4. Stop loss price (exit if wrong)
    5. Target price (exit if right)
    
    The system will:
    - Store your thesis and price levels in database
    - Monitor price vs stop loss and target
    - Auto-recommend exits when stop/target hit
    - Track performance by exit reason
    
    EXTENDED HOURS TRADING:
    - Auto-detects pre-market (4AM-9:30AM) and post-market (4PM-8PM) hours
    - Automatically converts to LIMIT orders during extended hours
    - Uses current price + 0.5% as limit price if not specified
    
    Args:
        symbol: Stock symbol to buy (e.g., "AAPL")
        quantity: Number of shares to buy (must be positive integer)
        thesis: **REQUIRED** Trading thesis - WHY are you buying? (e.g., "Oversold bounce at support, RSI 25, bullish divergence")
        support_price: **REQUIRED** Support level - price floor where buyers step in
        resistance_price: **REQUIRED** Resistance level - price ceiling where sellers step in
        stop_loss_price: **REQUIRED** Exit price if trade goes against you (MUST be below entry for longs)
        target_price: **REQUIRED** Exit price when target is reached (MUST be above entry for longs)
        order_type: Type of order - "market" or "limit" (default: "market")
        limit_price: Limit price for limit orders
        extended_hours: Allow execution during pre-market/post-market
        market_regime: Current market regime (BULLISH, BEARISH, NEUTRAL)
        technical_setup: Technical setup description (e.g., "Bull flag breakout")
        confidence_level: Confidence 1-5 (5 = highest)
        
    Returns:
        Order execution result with order ID, status, and thesis confirmation
        
    Example:
        >>> result = buy(
        >>>     symbol="AAPL",
        >>>     quantity=100,
        >>>     thesis="Oversold bounce at $145 support, RSI 28, bullish MACD crossover",
        >>>     support_price=145.00,
        >>>     resistance_price=155.00,
        >>>     stop_loss_price=143.00,
        >>>     target_price=153.00,
        >>>     market_regime="NEUTRAL",
        >>>     technical_setup="Mean reversion at lower Bollinger Band",
        >>>     confidence_level=4
        >>> )
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
    # CRITICAL: Validate thesis and price levels
    if not thesis or len(thesis) < 20:
        return {
            "success": False,
            "error": "Trading thesis required (minimum 20 characters). Explain WHY you are entering this trade.",
            "symbol": symbol
        }
    
    # Auto-detect extended hours if not specified
    if extended_hours is None:
        extended_hours = _is_extended_hours()
        if extended_hours:
            print(f"🌙 Auto-detected extended hours trading for {symbol}")
    
    # Validate inputs
    if quantity <= 0:
        return {
            "success": False,
            "error": "Quantity must be positive",
            "symbol": symbol,
            "quantity": quantity
        }
    
    try:
        # Get current account to check buying power
        account = alpaca_client.get_account()
        
        # Get current price to estimate cost
        price = alpaca_client.get_latest_price(symbol)
        if price is None:
            return {
                "success": False,
                "error": f"Could not get price for {symbol}",
                "symbol": symbol
            }
        
        # CRITICAL: Validate price levels for LONG position
        if stop_loss_price >= price:
            return {
                "success": False,
                "error": f"Stop loss (${stop_loss_price:.2f}) must be BELOW entry price (${price:.2f}) for long positions",
                "symbol": symbol
            }
        if target_price <= price:
            return {
                "success": False,
                "error": f"Target price (${target_price:.2f}) must be ABOVE entry price (${price:.2f}) for long positions",
                "symbol": symbol
            }
        if support_price >= resistance_price:
            return {
                "success": False,
                "error": f"Support (${support_price:.2f}) must be BELOW resistance (${resistance_price:.2f})",
                "symbol": symbol
            }
        
        estimated_cost = price * quantity
        
        # Check if we have enough buying power
        if estimated_cost > float(account["buying_power"]):
            return {
                "success": False,
                "error": "Insufficient buying power",
                "symbol": symbol,
                "quantity": quantity,
                "estimated_cost": estimated_cost,
                "available_buying_power": account["buying_power"]
            }
        
        # Extended hours requires limit orders
        if extended_hours and order_type == "market":
            print(f"🌙 Converting market order to limit order for extended hours trading")
            order_type = "limit"
            if limit_price is None:
                # Auto-calculate limit price: current price + 0.5% for buys
                limit_price = round(price * 1.005, 2)
                print(f"💰 Auto-calculated limit price: ${limit_price:.2f} (current: ${price:.2f})")
        
        # Place order based on type
        if order_type == "limit":
            if limit_price is None:
                return {
                    "success": False,
                    "error": "limit_price required for limit orders",
                    "symbol": symbol
                }
            result = alpaca_client.buy_limit(symbol, quantity, limit_price, extended_hours=extended_hours)
        else:
            # Market order (regular hours only)
            result = alpaca_client.buy_market(symbol, quantity, extended_hours=extended_hours)
        
        # Mark that trading occurred
        write_config_value("IF_TRADE", True)
        
        # Log the trade
        signature = get_config_value("SIGNATURE")
        today_date = get_config_value("TODAY_DATE")
        log_trade(signature, today_date, "buy", symbol, quantity, result)
        
        # CRITICAL: Store trade thesis in database
        if result.get('success'):
            try:
                db = get_trade_thesis_db()
                order_id = result.get('order_id', result.get('order', {}).get('id', 'unknown'))
                db.add_trade_thesis(
                    order_id=order_id,
                    symbol=symbol,
                    action="BUY",
                    quantity=quantity,
                    thesis=thesis,
                    support_price=support_price,
                    resistance_price=resistance_price,
                    stop_loss_price=stop_loss_price,
                    target_price=target_price,
                    entry_price=price,
                    market_regime=market_regime,
                    technical_setup=technical_setup,
                    confidence_level=confidence_level
                )
                # Add thesis confirmation to result
                risk_reward = (target_price - price) / (price - stop_loss_price)
                result['thesis_stored'] = True
                result['risk_reward_ratio'] = round(risk_reward, 2)
                result['stop_loss'] = stop_loss_price
                result['target_price'] = target_price
                print(f"✅ Trade thesis saved: R/R = {risk_reward:.2f}, Stop=${stop_loss_price:.2f}, Target=${target_price:.2f}")
            except Exception as db_error:
                print(f"⚠️ Failed to store thesis in database: {db_error}")
                result['thesis_error'] = str(db_error)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol,
            "quantity": quantity
        }


@mcp.tool()
def sell(symbol: str, quantity: int, order_type: str = "market", limit_price: float = None, extended_hours: bool = None, allow_short: bool = False) -> Dict[str, Any]:
    """
    Place a sell order for a stock
    
    This function executes a real sell order through Alpaca's trading API.
    By default, you must own the stock before selling it (closes long position).
    Set allow_short=True to enable short selling (opening a short position).
    
    EXTENDED HOURS TRADING:
    - Auto-detects pre-market (4AM-9:30AM) and post-market (4PM-8PM) hours
    - Automatically converts to LIMIT orders during extended hours
    - Uses current price - 0.5% as limit price if not specified
    - Market orders NOT allowed during extended hours per Alpaca rules
    
    Args:
        symbol: Stock symbol to sell (e.g., "AAPL")
        quantity: Number of shares to sell (must be positive integer)
        order_type: Type of order - "market" or "limit" (default: "market")
                    NOTE: Auto-converts to "limit" during extended hours
        limit_price: Limit price for limit orders (required if order_type="limit")
                    During extended hours, auto-calculated as current_price * 0.995
        extended_hours: Allow execution during pre-market (4AM-9:30AM ET) and 
                       post-market (4PM-8PM ET) hours. If None (default), will 
                       auto-detect based on current time.
        allow_short: If True, allows selling without existing position (short selling).
                    Default False for safety. Use short_sell() for clearer intent.
        
    Returns:
        Order execution result with order ID and status
        
    Example:
        >>> # Close existing long position (regular hours)
        >>> result = sell("AAPL", 5)
        >>> 
        >>> # Close position during extended hours (auto-converts to limit)
        >>> result = sell("AAPL", 5)  # Will use limit order automatically
        >>> 
        >>> # Open short position (requires margin account)
        >>> result = sell("AAPL", 100, allow_short=True)
        >>> 
        >>> # Or use dedicated short_sell() function
        >>> result = short_sell("AAPL", 100)
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
    # Auto-detect extended hours if not specified
    if extended_hours is None:
        extended_hours = _is_extended_hours()
        if extended_hours:
            print(f"🌙 Auto-detected extended hours trading for {symbol}")
    
    # Validate inputs
    if quantity <= 0:
        return {
            "success": False,
            "error": "Quantity must be positive",
            "symbol": symbol,
            "quantity": quantity
        }
    
    try:
        # Check if we have the position
        position = alpaca_client.get_position(symbol)
        
        if position is None:
            # No existing position
            if not allow_short:
                return {
                    "success": False,
                    "error": f"No position found for {symbol}. Use allow_short=True or short_sell() to open short position.",
                    "symbol": symbol,
                    "quantity": quantity,
                    "hint": "To short sell, use: sell(symbol, qty, allow_short=True) or short_sell(symbol, qty)"
                }
            # Short selling allowed - proceed with sell order
            print(f"🔻 Opening SHORT position for {symbol} ({quantity} shares)")
        else:
            # Have existing position - check if enough shares
            if quantity > abs(position["qty"]):
                return {
                    "success": False,
                    "error": "Insufficient shares to sell",
                    "symbol": symbol,
                    "requested_qty": quantity,
                    "available_qty": abs(position["qty"])
                }
        
        # Get current price for limit orders
        price = alpaca_client.get_latest_price(symbol)
        if price is None:
            return {
                "success": False,
                "error": f"Could not get price for {symbol}",
                "symbol": symbol
            }
        
        # Extended hours requires limit orders
        if extended_hours and order_type == "market":
            print(f"🌙 Converting market order to limit order for extended hours trading")
            order_type = "limit"
            if limit_price is None:
                # Auto-calculate limit price: current price - 0.5% for sells
                limit_price = round(price * 0.995, 2)
                print(f"💰 Auto-calculated limit price: ${limit_price:.2f} (current: ${price:.2f})")
        
        # Place order based on type
        if order_type == "limit":
            if limit_price is None:
                return {
                    "success": False,
                    "error": "limit_price required for limit orders",
                    "symbol": symbol
                }
            result = alpaca_client.sell_limit(symbol, quantity, limit_price, extended_hours=extended_hours)
        else:
            # Market order (regular hours only)
            result = alpaca_client.sell_market(symbol, quantity, extended_hours=extended_hours)
        
        # Mark that trading occurred
        write_config_value("IF_TRADE", True)
        
        # Log the trade with appropriate action
        signature = get_config_value("SIGNATURE")
        today_date = get_config_value("TODAY_DATE")
        action = "short" if (position is None and allow_short) else "sell"
        log_trade(signature, today_date, action, symbol, quantity, result)
        
        # If closing an existing position, mark it closed in database
        if result.get('success') and position is not None:
            try:
                db = get_trade_thesis_db()
                # Get open positions for this symbol (now works with symbol parameter)
                open_positions = db.get_open_positions(symbol=symbol)
                if open_positions:
                    # Close the most recent position
                    pos = open_positions[0]
                    # Calculate P&L
                    entry_price = pos.get('entry_price', 0)
                    if entry_price > 0:
                        pnl = (price - entry_price) * quantity
                        pnl_percent = ((price - entry_price) / entry_price) * 100
                    else:
                        pnl = None
                        pnl_percent = None
                    
                    # Use the ORIGINAL order_id from the opening trade
                    original_order_id = pos['order_id']
                    db.close_trade(
                        order_id=original_order_id,  # FIXED: use order_id not symbol
                        exit_price=price,
                        exit_reason="MANUAL",  # Agent decides reason
                        pnl=pnl,
                        pnl_percent=pnl_percent
                    )
                    print(f"✅ Position closed in database: {symbol} (Order: {original_order_id[:8]}...) P&L: ${pnl:.2f} ({pnl_percent:+.2f}%)")
            except Exception as db_error:
                print(f"⚠️ Failed to close position in database: {db_error}")
                import traceback
                traceback.print_exc()
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol,
            "quantity": quantity
        }


@mcp.tool()
def short_sell(
    symbol: str,
    quantity: int,
    thesis: str,
    support_price: float,
    resistance_price: float,
    stop_loss_price: float,
    target_price: float,
    order_type: str = "market",
    limit_price: float = None,
    extended_hours: bool = None,
    market_regime: str = None,
    technical_setup: str = None,
    confidence_level: int = None
) -> Dict[str, Any]:
    """
    Open a SHORT position with MANDATORY trading thesis and price levels
    
    CRITICAL: Every SHORT trade MUST have:
    1. Clear thesis explaining WHY shorting (bearish case)
    2. Support level (expected price floor)
    3. Resistance level (expected price ceiling)
    4. Stop loss price (exit if wrong - ABOVE entry for shorts)
    5. Target price (exit if right - BELOW entry for shorts)
    
    IMPORTANT: Short selling involves unlimited risk. The stock price can rise indefinitely,
    causing unlimited losses. Use stop-loss orders and proper risk management.
    
    EXTENDED HOURS TRADING:
    - Auto-detects pre-market (4AM-9:30AM) and post-market (4PM-8PM) hours
    - Automatically converts to LIMIT orders during extended hours
    - Uses current price - 0.5% as limit price if not specified
    - Market orders NOT allowed during extended hours per Alpaca rules
    
    Args:
        symbol: Stock symbol to short (e.g., "TSLA")
        quantity: Number of shares to short sell (must be positive integer)
        thesis: **REQUIRED** Trading thesis - WHY shorting? (e.g., "Overbought at resistance, bearish divergence")
        support_price: **REQUIRED** Support level - expected price floor
        resistance_price: **REQUIRED** Resistance level - price ceiling where selling
        stop_loss_price: **REQUIRED** Exit if wrong (MUST be ABOVE entry for shorts)
        target_price: **REQUIRED** Exit if right (MUST be BELOW entry for shorts)
        order_type: Type of order - "market" or "limit" (default: "market")
        limit_price: Limit price for limit orders (auto-calculated during extended hours)
        extended_hours: Allow execution during pre-market and post-market hours
        market_regime: Current market regime (BULLISH, BEARISH, NEUTRAL)
        technical_setup: Technical setup (e.g., "Bear flag breakdown")
        confidence_level: Confidence 1-5 (5 = highest)
        
    Returns:
        Order execution result with order ID and thesis confirmation
        
    Example:
        >>> result = short_sell(
        >>>     symbol="TSLA",
        >>>     quantity=10,
        >>>     thesis="Overbought at resistance, bearish RSI divergence, failed breakout",
        >>>     support_price=220.00,
        >>>     resistance_price=240.00,
        >>>     stop_loss_price=245.00,  # Above entry
        >>>     target_price=225.00,  # Below entry
        >>>     market_regime="BEARISH",
        >>>     technical_setup="Double top at resistance",
        >>>     confidence_level=4
        >>> )
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
    # CRITICAL: Validate thesis and price levels
    if not thesis or len(thesis) < 20:
        return {
            "success": False,
            "error": "Trading thesis required (minimum 20 characters). Explain WHY you are shorting this stock.",
            "symbol": symbol
        }
    
    # Auto-detect extended hours if not specified
    if extended_hours is None:
        extended_hours = _is_extended_hours()
        if extended_hours:
            print(f"🌙 Auto-detected extended hours trading for {symbol}")
    
    # Validate inputs
    if quantity <= 0:
        return {
            "success": False,
            "error": "Quantity must be positive",
            "symbol": symbol,
            "quantity": quantity
        }
    
    try:
        # Check account configuration
        account = alpaca_client.get_account()
        
        # Get current price to estimate margin requirement
        price = alpaca_client.get_latest_price(symbol)
        if price is None:
            return {
                "success": False,
                "error": f"Could not get price for {symbol}",
                "symbol": symbol
            }
        
        # CRITICAL: Validate price levels for SHORT position (inverted)
        if stop_loss_price <= price:
            return {
                "success": False,
                "error": f"Stop loss (${stop_loss_price:.2f}) must be ABOVE entry price (${price:.2f}) for short positions",
                "symbol": symbol
            }
        if target_price >= price:
            return {
                "success": False,
                "error": f"Target price (${target_price:.2f}) must be BELOW entry price (${price:.2f}) for short positions",
                "symbol": symbol
            }
        if support_price >= resistance_price:
            return {
                "success": False,
                "error": f"Support (${support_price:.2f}) must be BELOW resistance (${resistance_price:.2f})",
                "symbol": symbol
            }
        
        estimated_value = price * quantity
        
        # Check if we have enough buying power (margin requirement for short)
        if estimated_value > float(account["buying_power"]):
            return {
                "success": False,
                "error": "Insufficient buying power for short position",
                "symbol": symbol,
                "quantity": quantity,
                "estimated_value": estimated_value,
                "available_buying_power": account["buying_power"]
            }
        
        # Extended hours requires limit orders
        if extended_hours and order_type == "market":
            print(f"🌙 Converting market order to limit order for extended hours short selling")
            order_type = "limit"
            if limit_price is None:
                # Auto-calculate limit price: current price - 0.5% for shorts
                limit_price = round(price * 0.995, 2)
                print(f"💰 Auto-calculated limit price: ${limit_price:.2f} (current: ${price:.2f})")
        
        # Place short sell order (sell without owning)
        print(f"🔻 Opening SHORT position: {symbol} x {quantity} @ ~${price:.2f}")
        if order_type == "limit":
            if limit_price is None:
                return {
                    "success": False,
                    "error": "limit_price required for limit orders",
                    "symbol": symbol
                }
            result = alpaca_client.sell_limit(symbol, quantity, limit_price, extended_hours=extended_hours)
        else:
            # Market order (regular hours only)
            result = alpaca_client.sell_market(symbol, quantity, extended_hours=extended_hours)
        
        # Mark that trading occurred
        write_config_value("IF_TRADE", True)
        
        # Log the trade
        signature = get_config_value("SIGNATURE")
        today_date = get_config_value("TODAY_DATE")
        log_trade(signature, today_date, "short", symbol, quantity, result)
        
        # CRITICAL: Store trade thesis in database
        if result.get('success'):
            try:
                db = get_trade_thesis_db()
                order_id = result.get('order_id', result.get('order', {}).get('id', 'unknown'))
                db.add_trade_thesis(
                    order_id=order_id,
                    symbol=symbol,
                    action="SHORT",
                    quantity=quantity,
                    thesis=thesis,
                    support_price=support_price,
                    resistance_price=resistance_price,
                    stop_loss_price=stop_loss_price,
                    target_price=target_price,
                    entry_price=price,
                    market_regime=market_regime,
                    technical_setup=technical_setup,
                    confidence_level=confidence_level
                )
                # Add thesis confirmation to result (inverted R/R for shorts)
                risk_reward = (price - target_price) / (stop_loss_price - price)
                result['thesis_stored'] = True
                result['risk_reward_ratio'] = round(risk_reward, 2)
                result['stop_loss'] = stop_loss_price
                result['target_price'] = target_price
                print(f"✅ Short thesis saved: R/R = {risk_reward:.2f}, Stop=${stop_loss_price:.2f}, Target=${target_price:.2f}")
            except Exception as db_error:
                print(f"⚠️ Failed to store thesis in database: {db_error}")
                result['thesis_error'] = str(db_error)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol,
            "quantity": quantity
        }


@mcp.tool()
def check_positions_vs_targets() -> Dict[str, Any]:
    """
    Check ALL open positions against their stop loss and target prices
    
    CRITICAL: Call this function BEFORE making any trading decision!
    
    This tool monitors all open positions and compares current price with:
    - Stop loss price (exit if price hits this level)
    - Target price (exit if price reaches target)
    
    Returns actionable recommendations:
    - "🚨 STOP LOSS HIT" - MUST EXIT immediately
    - "🎯 TARGET REACHED" - MUST EXIT and take profits
    - "✅ HOLD" - Position within acceptable range
    
    The system enforces disciplined trading:
    ❌ NO early exits before target (unless stop hit)
    ❌ NO holding past stop loss
    ❌ NO emotional decisions
    
    Returns:
        Dictionary with:
        - total_positions: Count of open positions
        - recommendations: List of all position checks with should_exit flag
        - immediate_exits: Positions that MUST be exited NOW
        - summary: Overall status
        
    Example:
        >>> result = check_positions_vs_targets()
        >>> if result['immediate_exits']:
        >>>     for exit in result['immediate_exits']:
        >>>         print(f"{exit['recommendation']}: {exit['symbol']} @ ${exit['current_price']}")
        >>>         # Execute exit immediately
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
    try:
        db = get_trade_thesis_db()
        
        # Check current time for end-of-day deadlines
        from datetime import datetime
        import pytz
        et_tz = pytz.timezone('US/Eastern')
        current_time = datetime.now(et_tz)
        hour = current_time.hour
        minute = current_time.minute
        time_decimal = hour + minute / 60.0
        
        # Get all open positions from database
        open_positions = db.get_open_positions()
        
        if not open_positions:
            return {
                "success": True,
                "total_positions": 0,
                "recommendations": [],
                "immediate_exits": [],
                "summary": "No open positions"
            }
        
        recommendations = []
        immediate_exits = []
        
        # CRITICAL: Check for end-of-day deadlines
        is_eod_deadline = False
        eod_reason = ""
        
        if time_decimal >= 19.67:  # 7:40 PM or later (post-market deadline)
            is_eod_deadline = True
            eod_reason = "🚨 POST-MARKET DEADLINE (7:40 PM) - EXIT ALL POSITIONS NOW!"
        elif time_decimal >= 19.50:  # 7:30 PM or later (post-market wind down)
            is_eod_deadline = True
            eod_reason = "⚠️ POST-MARKET WIND DOWN (7:30 PM) - Exit all positions by 7:40 PM"
        elif time_decimal >= 15.75 and time_decimal < 16.0:  # 3:45 PM - 4:00 PM (regular session deadline)
            is_eod_deadline = True
            eod_reason = "🚨 REGULAR SESSION DEADLINE (3:45 PM) - EXIT ALL POSITIONS NOW!"
        elif time_decimal >= 15.50 and time_decimal < 16.0:  # 3:30 PM - 3:45 PM (regular session wind down)
            is_eod_deadline = True
            eod_reason = "⚠️ REGULAR SESSION WIND DOWN (3:30 PM) - Exit all positions by 3:45 PM"
        
        for pos in open_positions:
            symbol = pos['symbol']
            
            # Get current price
            current_price = alpaca_client.get_latest_price(symbol)
            if current_price is None:
                recommendations.append({
                    "symbol": symbol,
                    "error": f"Could not get current price for {symbol}",
                    "should_exit": False
                })
                continue
            
            # If end-of-day deadline, FORCE EXIT regardless of stop/target
            if is_eod_deadline:
                recommendations.append({
                    "symbol": symbol,
                    "current_price": current_price,
                    "recommendation": eod_reason,
                    "should_exit": True,
                    "exit_reason": "END_OF_DAY",
                    "entry_price": pos.get('entry_price'),
                    "stop_loss": pos.get('stop_loss_price'),
                    "target_price": pos.get('target_price')
                })
                immediate_exits.append(recommendations[-1])
            else:
                # Normal check: price action vs stop/target
                check_result = db.check_price_action(symbol, current_price)
                
                if check_result['positions']:
                    for position_check in check_result['positions']:
                        recommendations.append(position_check)
                        
                        # Mark for immediate exit if stop/target hit
                        if position_check.get('should_exit'):
                            immediate_exits.append(position_check)
        
        # Generate summary
        if is_eod_deadline:
            summary = f"🚨 END OF DAY DEADLINE - {len(open_positions)} position(s) MUST EXIT NOW!"
        elif immediate_exits:
            summary = f"⚠️ {len(immediate_exits)} position(s) MUST EXIT NOW!"
        else:
            summary = f"✅ All {len(open_positions)} position(s) within acceptable range"
        
        return {
            "success": True,
            "total_positions": len(open_positions),
            "recommendations": recommendations,
            "immediate_exits": immediate_exits,
            "summary": summary,
            "time_check": f"{hour:02d}:{minute:02d} ET"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def close_position(symbol: str, extended_hours: bool = None) -> Dict[str, Any]:
    """
    Close entire position for a symbol (sell all shares)
    
    Args:
        symbol: Stock symbol to close position for
        extended_hours: Allow execution during extended hours. If None (default), 
                       will auto-detect based on current time.
        
    Returns:
        Order execution result
        
    Example:
        >>> result = close_position("AAPL")
        >>> if result['success']:
        >>>     print("Position closed")
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
    # Auto-detect extended hours if not specified
    if extended_hours is None:
        extended_hours = _is_extended_hours()
        if extended_hours:
            print(f"🌙 Auto-detected extended hours for closing {symbol}")
    
    try:
        # Get current position to know how many shares to sell
        position = alpaca_client.get_position(symbol)
        
        if position is None:
            return {
                "success": False,
                "error": f"No position found for {symbol}",
                "symbol": symbol
            }
        
        # Use sell_market with extended_hours parameter instead of close_position
        qty = int(float(position["qty"]))
        result = alpaca_client.sell_market(symbol, qty, extended_hours=extended_hours)
        
        if result.get("success"):
            # Mark that trading occurred
            write_config_value("IF_TRADE", True)
            
            # Log the trade
            signature = get_config_value("SIGNATURE")
            today_date = get_config_value("TODAY_DATE")
            log_trade(signature, today_date, "close", symbol, qty, result)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol
        }


@mcp.tool()
def get_portfolio_summary() -> Dict[str, Any]:
    """
    Get comprehensive portfolio summary
    
    Returns complete portfolio information including:
    - Account details (cash, equity, buying power)
    - All current positions
    - Total unrealized P&L
    - Number of positions
    
    Returns:
        Comprehensive portfolio summary
        
    Example:
        >>> summary = get_portfolio_summary()
        >>> print(f"Total equity: ${summary['summary']['equity']:.2f}")
        >>> print(f"Positions: {summary['summary']['total_positions']}")
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
    try:
        summary = alpaca_client.get_portfolio_summary()
        return {
            "success": True,
            **summary
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def log_trade(
    signature: str,
    date: str,
    action: str,
    symbol: str,
    quantity: float,
    result: Dict[str, Any]
):
    """
    Log trade execution to file for record keeping
    Enhanced to query filled order details for accurate P&L tracking
    
    Args:
        signature: Model signature
        date: Trading date
        action: Trade action (buy/sell/close/short)
        symbol: Stock symbol
        quantity: Quantity traded
        result: Order result from Alpaca
    """
    try:
        log_dir = os.path.join(project_root, "data", "agent_data", signature, "trades")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"{date}_trades.jsonl")
        
        # Query filled order details if order was successful
        filled_details = None
        if result.get('success') and result.get('order_id') and alpaca_client:
            try:
                import time
                # Wait 2 seconds for order to fill
                time.sleep(2)
                filled_details = alpaca_client.get_order(result['order_id'])
            except Exception as e:
                print(f"⚠️ Could not get filled order details: {e}")
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "date": date,
            "action": action,
            "symbol": symbol,
            "quantity": quantity,
            "result": result,
            "filled_details": filled_details,
            # Extract key execution details for easy analysis
            "side": filled_details.get('side') if filled_details else result.get('side'),
            "qty": filled_details.get('filled_qty') if filled_details else result.get('qty'),
            "price": filled_details.get('filled_avg_price') if filled_details else result.get('filled_avg_price'),
            "status": filled_details.get('status') if filled_details else result.get('status'),
            "pnl": None  # Will be calculated when position is closed
        }
        
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
    except Exception as e:
        print(f"⚠️ Warning: Could not log trade: {e}")


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get port from environment
    port = int(os.getenv("ALPACA_TRADE_HTTP_PORT", "8005"))
    
    print(f"🚀 Starting Alpaca Trade Tools MCP service on port {port}...")
    mcp.run(transport="http", port=port)
