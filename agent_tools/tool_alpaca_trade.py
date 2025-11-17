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
def buy(symbol: str, quantity: int, order_type: str = "market", extended_hours: bool = None) -> Dict[str, Any]:
    """
    Place a buy order for a stock
    
    This function executes a real buy order through Alpaca's trading API.
    Use with caution as this involves real money (even in paper trading mode).
    
    Args:
        symbol: Stock symbol to buy (e.g., "AAPL")
        quantity: Number of shares to buy (must be positive integer)
        order_type: Type of order - "market" or "limit" (default: "market")
        extended_hours: Allow execution during pre-market (4AM-9:30AM ET) and 
                       post-market (4PM-8PM ET) hours. If None (default), will 
                       auto-detect based on current time.
        
    Returns:
        Order execution result with order ID and status
        
    Example:
        >>> result = buy("AAPL", 10)
        >>> if result['success']:
        >>>     print(f"Order placed: {result['order_id']}")
        >>> 
        >>> # Explicitly specify extended hours
        >>> result = buy("AAPL", 10, extended_hours=True)
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
        
        # Place market order with extended_hours parameter
        result = alpaca_client.buy_market(symbol, quantity, extended_hours=extended_hours)
        
        # Mark that trading occurred
        write_config_value("IF_TRADE", True)
        
        # Log the trade
        signature = get_config_value("SIGNATURE")
        today_date = get_config_value("TODAY_DATE")
        log_trade(signature, today_date, "buy", symbol, quantity, result)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol,
            "quantity": quantity
        }


@mcp.tool()
def sell(symbol: str, quantity: int, order_type: str = "market", extended_hours: bool = None, allow_short: bool = False) -> Dict[str, Any]:
    """
    Place a sell order for a stock
    
    This function executes a real sell order through Alpaca's trading API.
    By default, you must own the stock before selling it (closes long position).
    Set allow_short=True to enable short selling (opening a short position).
    
    Args:
        symbol: Stock symbol to sell (e.g., "AAPL")
        quantity: Number of shares to sell (must be positive integer)
        order_type: Type of order - "market" or "limit" (default: "market")
        extended_hours: Allow execution during pre-market (4AM-9:30AM ET) and 
                       post-market (4PM-8PM ET) hours. If None (default), will 
                       auto-detect based on current time.
        allow_short: If True, allows selling without existing position (short selling).
                    Default False for safety. Use short_sell() for clearer intent.
        
    Returns:
        Order execution result with order ID and status
        
    Example:
        >>> # Close existing long position
        >>> result = sell("AAPL", 5)
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
        
        # Place market sell order with extended_hours parameter
        result = alpaca_client.sell_market(symbol, quantity, extended_hours=extended_hours)
        
        # Mark that trading occurred
        write_config_value("IF_TRADE", True)
        
        # Log the trade with appropriate action
        signature = get_config_value("SIGNATURE")
        today_date = get_config_value("TODAY_DATE")
        action = "short" if (position is None and allow_short) else "sell"
        log_trade(signature, today_date, action, symbol, quantity, result)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol,
            "quantity": quantity
        }


@mcp.tool()
def short_sell(symbol: str, quantity: int, order_type: str = "market", extended_hours: bool = None) -> Dict[str, Any]:
    """
    Open a SHORT position (sell stock you don't own)
    
    This function opens a short position by selling shares you don't currently own.
    Requires a margin account with short selling enabled.
    
    IMPORTANT: Short selling involves unlimited risk. The stock price can rise indefinitely,
    causing unlimited losses. Use stop-loss orders and proper risk management.
    
    Args:
        symbol: Stock symbol to short (e.g., "AAPL")
        quantity: Number of shares to short sell (must be positive integer)
        order_type: Type of order - "market" or "limit" (default: "market")
        extended_hours: Allow execution during pre-market and post-market hours
        
    Returns:
        Order execution result with order ID and status
        
    Example:
        >>> # Open short position on overbought stock
        >>> result = short_sell("TSLA", 10)
        >>> if result['success']:
        >>>     print(f"Short position opened: {result['order_id']}")
        >>> 
        >>> # Later, close the short by buying back
        >>> result = buy("TSLA", 10)  # Covers the short
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
        
        # Place short sell order (sell without owning)
        print(f"🔻 Opening SHORT position: {symbol} x {quantity} @ ~${price:.2f}")
        result = alpaca_client.sell_market(symbol, quantity, extended_hours=extended_hours)
        
        # Mark that trading occurred
        write_config_value("IF_TRADE", True)
        
        # Log the trade
        signature = get_config_value("SIGNATURE")
        today_date = get_config_value("TODAY_DATE")
        log_trade(signature, today_date, "short", symbol, quantity, result)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol,
            "quantity": quantity
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
