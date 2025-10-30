"""
Bridge between AI-Trader agents and Alpaca Official MCP Server

This module provides a Python interface to Alpaca's official MCP server,
allowing AI agents to access 60+ trading and market data tools through
a simple, synchronous API.

Usage:
    from tools.alpaca_mcp_bridge import AlpacaMCPBridge
    
    # Synchronous usage
    bridge = AlpacaMCPBridge()
    account = bridge.get_account()
    positions = bridge.get_positions()
    
    # Place order
    order = bridge.place_order("AAPL", 10, "buy", "market")
"""

import os
import sys
import subprocess
import json
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()


class AlpacaMCPBridge:
    """
    Bridge to Alpaca's official MCP server
    
    This class provides a synchronous Python interface to the official
    Alpaca MCP server, making it easy to integrate with existing AI-Trader code.
    """
    
    def __init__(self, port: Optional[int] = None):
        """
        Initialize the bridge
        
        Args:
            port: HTTP port for MCP server (default from env or 8004)
        """
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.port = port or int(os.getenv("ALPACA_MCP_PORT", "8004"))
        self.base_url = f"http://localhost:{self.port}"
        
        if not self.api_key or not self.secret_key:
            raise ValueError(
                "ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env file"
            )
    
    def _call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """
        Call an MCP tool via HTTP
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments as dictionary
            
        Returns:
            Tool result (varies by tool)
        """
        if arguments is None:
            arguments = {}
        
        try:
            response = requests.post(
                f"{self.base_url}/tools/{tool_name}",
                json={"arguments": arguments},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result.get("result", result)
            
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Alpaca MCP server at {self.base_url}. "
                f"Is the server running? Start it with: ./scripts/start_alpaca_mcp.sh"
            )
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error calling tool {tool_name}: {str(e)}")
    
    # ========================================================================
    # Account Management
    # ========================================================================
    
    def get_account(self) -> Dict[str, Any]:
        """
        Get account information including balance and buying power
        
        Returns:
            Dictionary with account details:
            - account_number: Account identifier
            - cash: Available cash
            - buying_power: Current buying power
            - portfolio_value: Total portfolio value
            - equity: Current equity
            - status: Account status
        """
        return self._call_tool("get_account")
    
    def get_account_configurations(self) -> Dict[str, Any]:
        """Get account configuration settings"""
        return self._call_tool("get_account_configurations")
    
    # ========================================================================
    # Position Management
    # ========================================================================
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions
        
        Returns:
            List of position dictionaries, each containing:
            - symbol: Stock symbol
            - qty: Quantity held
            - avg_entry_price: Average entry price
            - current_price: Current market price
            - market_value: Current market value
            - unrealized_pl: Unrealized profit/loss
        """
        return self._call_tool("get_positions")
    
    def get_position(self, symbol: str) -> Dict[str, Any]:
        """
        Get position for specific symbol
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Position details dictionary
        """
        return self._call_tool("get_position", {"symbol": symbol})
    
    def close_position(
        self,
        symbol: str,
        qty: Optional[float] = None,
        percentage: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Close position (full or partial)
        
        Args:
            symbol: Stock symbol to close
            qty: Number of shares to close (optional)
            percentage: Percentage of position to close (optional)
            
        Returns:
            Order details for the closing order
        """
        args = {"symbol": symbol}
        if qty is not None:
            args["qty"] = qty
        if percentage is not None:
            args["percentage"] = percentage
            
        return self._call_tool("close_position", args)
    
    def close_all_positions(self, cancel_orders: bool = True) -> List[Dict[str, Any]]:
        """
        Close all open positions
        
        Args:
            cancel_orders: Whether to cancel open orders first
            
        Returns:
            List of orders created to close positions
        """
        return self._call_tool("close_all_positions", {"cancel_orders": cancel_orders})
    
    # ========================================================================
    # Order Management
    # ========================================================================
    
    def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = "market",
        time_in_force: str = "day",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Place a stock/ETF order
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            qty: Number of shares
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop', 'stop_limit', 'trailing_stop'
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
            limit_price: Limit price (required for limit orders)
            stop_price: Stop price (required for stop orders)
            **kwargs: Additional order parameters
            
        Returns:
            Order details including order_id
        """
        args = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
            **kwargs
        }
        
        if limit_price is not None:
            args["limit_price"] = limit_price
        if stop_price is not None:
            args["stop_price"] = stop_price
            
        return self._call_tool("place_order", args)
    
    def get_orders(
        self,
        status: str = "all",
        limit: int = 100,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Get order history
        
        Args:
            status: Order status filter ('open', 'closed', 'all')
            limit: Maximum number of orders to return
            **kwargs: Additional filter parameters
            
        Returns:
            List of order dictionaries
        """
        args = {"status": status, "limit": limit, **kwargs}
        return self._call_tool("get_orders", args)
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        Get specific order details
        
        Args:
            order_id: Order identifier
            
        Returns:
            Order details dictionary
        """
        return self._call_tool("get_order", {"order_id": order_id})
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel specific order
        
        Args:
            order_id: Order identifier to cancel
            
        Returns:
            Cancellation confirmation
        """
        return self._call_tool("cancel_order", {"order_id": order_id})
    
    def cancel_all_orders(self) -> List[Dict[str, Any]]:
        """
        Cancel all open orders
        
        Returns:
            List of cancelled orders
        """
        return self._call_tool("cancel_all_orders")
    
    # ========================================================================
    # Market Data
    # ========================================================================
    
    def get_latest_trade(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest trade for symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Latest trade data with price, size, timestamp
        """
        return self._call_tool("get_latest_trade", {"symbol": symbol})
    
    def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest bid/ask quote
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quote with bid_price, ask_price, bid_size, ask_size
        """
        return self._call_tool("get_latest_quote", {"symbol": symbol})
    
    def get_latest_bar(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest OHLCV bar
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Bar data with open, high, low, close, volume
        """
        return self._call_tool("get_latest_bar", {"symbol": symbol})
    
    def get_snapshot(self, symbol: str) -> Dict[str, Any]:
        """
        Get complete market snapshot (quote + trade + bar)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Complete snapshot with all market data
        """
        return self._call_tool("get_snapshot", {"symbol": symbol})
    
    def get_bars(
        self,
        symbol: str,
        start: str,
        end: str = None,
        timeframe: str = "1Day",
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get historical price bars
        
        Args:
            symbol: Stock symbol
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD), optional
            timeframe: Bar timeframe ('1Min', '5Min', '1Hour', '1Day', etc.)
            limit: Maximum bars to return
            
        Returns:
            List of bars with OHLCV data
        """
        args = {
            "symbol": symbol,
            "start": start,
            "timeframe": timeframe,
            "limit": limit
        }
        if end:
            args["end"] = end
            
        return self._call_tool("get_bars", args)
    
    # ========================================================================
    # Convenience Methods (Compatible with custom wrapper)
    # ========================================================================
    
    def get_latest_price(self, symbol: str) -> float:
        """
        Get current market price (simplified)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price as float
        """
        trade = self.get_latest_trade(symbol)
        return float(trade.get("price", 0))
    
    def buy_market(self, symbol: str, qty: float) -> Dict[str, Any]:
        """Buy shares at market price"""
        return self.place_order(symbol, qty, "buy", "market")
    
    def sell_market(self, symbol: str, qty: float) -> Dict[str, Any]:
        """Sell shares at market price"""
        return self.place_order(symbol, qty, "sell", "market")
    
    def buy_limit(self, symbol: str, qty: float, limit_price: float) -> Dict[str, Any]:
        """Buy shares with limit order"""
        return self.place_order(symbol, qty, "buy", "limit", limit_price=limit_price)
    
    def sell_limit(self, symbol: str, qty: float, limit_price: float) -> Dict[str, Any]:
        """Sell shares with limit order"""
        return self.place_order(symbol, qty, "sell", "limit", limit_price=limit_price)
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get portfolio summary (compatible with custom wrapper)
        
        Returns:
            Dictionary with account and position summaries
        """
        account = self.get_account()
        positions = self.get_positions()
        
        return {
            "account": {
                "cash": float(account.get("cash", 0)),
                "buying_power": float(account.get("buying_power", 0)),
                "portfolio_value": float(account.get("portfolio_value", 0)),
                "equity": float(account.get("equity", 0)),
            },
            "positions": [
                {
                    "symbol": p.get("symbol"),
                    "qty": float(p.get("qty", 0)),
                    "avg_entry_price": float(p.get("avg_entry_price", 0)),
                    "current_price": float(p.get("current_price", 0)),
                    "market_value": float(p.get("market_value", 0)),
                    "unrealized_pl": float(p.get("unrealized_pl", 0)),
                    "unrealized_plpc": float(p.get("unrealized_plpc", 0)),
                }
                for p in positions
            ],
            "position_count": len(positions)
        }


# ============================================================================
# Standalone Functions (for backward compatibility)
# ============================================================================

def get_account_info() -> Dict[str, Any]:
    """Get account information (standalone function)"""
    bridge = AlpacaMCPBridge()
    return bridge.get_account()


def get_positions_list() -> List[Dict[str, Any]]:
    """Get all positions (standalone function)"""
    bridge = AlpacaMCPBridge()
    return bridge.get_positions()


def place_market_order(symbol: str, qty: float, side: str) -> Dict[str, Any]:
    """Place market order (standalone function)"""
    bridge = AlpacaMCPBridge()
    return bridge.place_order(symbol, qty, side, "market")


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    print("Testing Alpaca MCP Bridge...")
    print("=" * 50)
    
    try:
        bridge = AlpacaMCPBridge()
        
        # Test account
        print("\n1. Testing get_account()...")
        account = bridge.get_account()
        print(f"   ✅ Account: ${account.get('portfolio_value', 0):,.2f}")
        
        # Test positions
        print("\n2. Testing get_positions()...")
        positions = bridge.get_positions()
        print(f"   ✅ Positions: {len(positions)} open")
        
        # Test market data
        print("\n3. Testing get_latest_price('AAPL')...")
        price = bridge.get_latest_price("AAPL")
        print(f"   ✅ AAPL Price: ${price:.2f}")
        
        # Test portfolio summary
        print("\n4. Testing get_portfolio_summary()...")
        summary = bridge.get_portfolio_summary()
        print(f"   ✅ Portfolio Value: ${summary['account']['portfolio_value']:,.2f}")
        print(f"   ✅ Positions: {summary['position_count']}")
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        
    except ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nTo start the server, run:")
        print("  ./scripts/start_alpaca_mcp.sh")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
