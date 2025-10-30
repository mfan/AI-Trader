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
def buy(symbol: str, quantity: int, order_type: str = "market") -> Dict[str, Any]:
    """
    Place a buy order for a stock
    
    This function executes a real buy order through Alpaca's trading API.
    Use with caution as this involves real money (even in paper trading mode).
    
    Args:
        symbol: Stock symbol to buy (e.g., "AAPL")
        quantity: Number of shares to buy (must be positive integer)
        order_type: Type of order - "market" or "limit" (default: "market")
        
    Returns:
        Order execution result with order ID and status
        
    Example:
        >>> result = buy("AAPL", 10)
        >>> if result['success']:
        >>>     print(f"Order placed: {result['order_id']}")
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
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
        
        # Place market order
        result = alpaca_client.buy_market(symbol, quantity)
        
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
def sell(symbol: str, quantity: int, order_type: str = "market") -> Dict[str, Any]:
    """
    Place a sell order for a stock
    
    This function executes a real sell order through Alpaca's trading API.
    You must own the stock before selling it.
    
    Args:
        symbol: Stock symbol to sell (e.g., "AAPL")
        quantity: Number of shares to sell (must be positive integer)
        order_type: Type of order - "market" or "limit" (default: "market")
        
    Returns:
        Order execution result with order ID and status
        
    Example:
        >>> result = sell("AAPL", 5)
        >>> if result['success']:
        >>>     print(f"Sell order placed: {result['order_id']}")
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
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
            return {
                "success": False,
                "error": f"No position found for {symbol}",
                "symbol": symbol,
                "quantity": quantity
            }
        
        # Check if we have enough shares
        if quantity > position["qty"]:
            return {
                "success": False,
                "error": "Insufficient shares to sell",
                "symbol": symbol,
                "requested_qty": quantity,
                "available_qty": position["qty"]
            }
        
        # Place market sell order
        result = alpaca_client.sell_market(symbol, quantity)
        
        # Mark that trading occurred
        write_config_value("IF_TRADE", True)
        
        # Log the trade
        signature = get_config_value("SIGNATURE")
        today_date = get_config_value("TODAY_DATE")
        log_trade(signature, today_date, "sell", symbol, quantity, result)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol,
            "quantity": quantity
        }


@mcp.tool()
def close_position(symbol: str) -> Dict[str, Any]:
    """
    Close entire position for a symbol (sell all shares)
    
    Args:
        symbol: Stock symbol to close position for
        
    Returns:
        Order execution result
        
    Example:
        >>> result = close_position("AAPL")
        >>> if result['success']:
        >>>     print("Position closed")
    """
    if alpaca_client is None:
        return {"error": "Alpaca client not initialized. Check your API keys."}
    
    try:
        result = alpaca_client.close_position(symbol)
        
        if result.get("success"):
            # Mark that trading occurred
            write_config_value("IF_TRADE", True)
            
            # Log the trade
            signature = get_config_value("SIGNATURE")
            today_date = get_config_value("TODAY_DATE")
            log_trade(signature, today_date, "close", symbol, result.get("qty", 0), result)
        
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
    
    Args:
        signature: Model signature
        date: Trading date
        action: Trade action (buy/sell/close)
        symbol: Stock symbol
        quantity: Quantity traded
        result: Order result from Alpaca
    """
    try:
        log_dir = os.path.join(project_root, "data", "agent_data", signature, "trades")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"{date}_trades.jsonl")
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "date": date,
            "action": action,
            "symbol": symbol,
            "quantity": quantity,
            "result": result
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
