"""
Alpaca Trading Integration Module

This module provides integration with Alpaca's trading API using the official alpaca-py SDK.
It supports both paper trading (for testing) and live trading.

Features:
- Real-time order execution
- Position management
- Account information retrieval
- Market data access
- Order history and tracking
"""

import os
import sys
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

# Alpaca SDK imports
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    GetOrdersRequest,
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    OrderType,
    QueryOrderStatus,
)
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame


class AlpacaTradingClient:
    """
    Wrapper class for Alpaca Trading API
    
    Provides a simplified interface for trading operations while maintaining
    compatibility with the existing AI-Trader architecture.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper: bool = True,
        base_url: Optional[str] = None
    ):
        """
        Initialize Alpaca Trading Client
        
        Args:
            api_key: Alpaca API key (from env if not provided)
            secret_key: Alpaca secret key (from env if not provided)
            paper: Whether to use paper trading (default: True)
            base_url: Custom base URL (optional, uses default if not provided)
        """
        # Get API credentials
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        
        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca API credentials not found. "
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file"
            )
        
        # Determine paper trading mode
        self.paper = paper
        if os.getenv("ALPACA_PAPER_TRADING", "true").lower() == "false":
            self.paper = False
        
        # Initialize trading client
        self.trading_client = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=self.paper,
            url_override=base_url or os.getenv("ALPACA_BASE_URL")
        )
        
        # Initialize data client (no auth required for basic market data)
        self.data_client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )
        
        print(f"✅ Alpaca client initialized ({'PAPER' if self.paper else 'LIVE'} trading)")
    
    def get_account(self) -> Dict[str, Any]:
        """
        Get account information
        
        Returns:
            Dict containing account info (cash, buying_power, equity, etc.)
        """
        try:
            account = self.trading_client.get_account()
            return {
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "equity": float(account.equity),
                "portfolio_value": float(account.portfolio_value),
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "account_blocked": account.account_blocked,
            }
        except Exception as e:
            print(f"❌ Error getting account info: {e}")
            raise
    
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all current positions
        
        Returns:
            Dict mapping symbol to position info
        """
        try:
            positions = self.trading_client.get_all_positions()
            result = {}
            for pos in positions:
                result[pos.symbol] = {
                    "qty": float(pos.qty),
                    "avg_entry_price": float(pos.avg_entry_price),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "cost_basis": float(pos.cost_basis),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc),
                    "side": pos.side,
                }
            return result
        except Exception as e:
            print(f"❌ Error getting positions: {e}")
            raise
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position for a specific symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Position info dict or None if no position
        """
        try:
            pos = self.trading_client.get_open_position(symbol)
            return {
                "qty": float(pos.qty),
                "avg_entry_price": float(pos.avg_entry_price),
                "current_price": float(pos.current_price),
                "market_value": float(pos.market_value),
                "cost_basis": float(pos.cost_basis),
                "unrealized_pl": float(pos.unrealized_pl),
                "unrealized_plpc": float(pos.unrealized_plpc),
                "side": pos.side,
            }
        except Exception as e:
            # No position exists
            return None
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get latest price for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Latest price or None if not available
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = self.data_client.get_stock_latest_quote(request)
            if symbol in quote:
                return float(quote[symbol].ask_price)
            return None
        except Exception as e:
            print(f"⚠️ Error getting price for {symbol}: {e}")
            return None
    
    def get_latest_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """
        Get latest prices for multiple symbols
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to price
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbols)
            quotes = self.data_client.get_stock_latest_quote(request)
            result = {}
            for symbol in symbols:
                if symbol in quotes:
                    result[symbol] = float(quotes[symbol].ask_price)
                else:
                    result[symbol] = None
            return result
        except Exception as e:
            print(f"⚠️ Error getting prices: {e}")
            return {symbol: None for symbol in symbols}
    
    def buy_market(
        self,
        symbol: str,
        qty: int,
        time_in_force: TimeInForce = TimeInForce.DAY
    ) -> Dict[str, Any]:
        """
        Place market buy order
        
        Args:
            symbol: Stock symbol
            qty: Quantity to buy
            time_in_force: Order time in force (default: DAY)
            
        Returns:
            Order details dict
        """
        try:
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=time_in_force
            )
            
            order = self.trading_client.submit_order(order_data)
            
            return {
                "success": True,
                "order_id": str(order.id),
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side.value,
                "type": order.type.value,
                "status": order.status.value,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            }
        except Exception as e:
            print(f"❌ Error placing buy order for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "qty": qty
            }
    
    def sell_market(
        self,
        symbol: str,
        qty: int,
        time_in_force: TimeInForce = TimeInForce.DAY
    ) -> Dict[str, Any]:
        """
        Place market sell order
        
        Args:
            symbol: Stock symbol
            qty: Quantity to sell
            time_in_force: Order time in force (default: DAY)
            
        Returns:
            Order details dict
        """
        try:
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=time_in_force
            )
            
            order = self.trading_client.submit_order(order_data)
            
            return {
                "success": True,
                "order_id": str(order.id),
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side.value,
                "type": order.type.value,
                "status": order.status.value,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            }
        except Exception as e:
            print(f"❌ Error placing sell order for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "qty": qty
            }
    
    def buy_limit(
        self,
        symbol: str,
        qty: int,
        limit_price: float,
        time_in_force: TimeInForce = TimeInForce.DAY
    ) -> Dict[str, Any]:
        """
        Place limit buy order
        
        Args:
            symbol: Stock symbol
            qty: Quantity to buy
            limit_price: Limit price
            time_in_force: Order time in force (default: DAY)
            
        Returns:
            Order details dict
        """
        try:
            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=time_in_force,
                limit_price=limit_price
            )
            
            order = self.trading_client.submit_order(order_data)
            
            return {
                "success": True,
                "order_id": str(order.id),
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side.value,
                "type": order.type.value,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "status": order.status.value,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            }
        except Exception as e:
            print(f"❌ Error placing limit buy order for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "qty": qty,
                "limit_price": limit_price
            }
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order details by ID
        
        Args:
            order_id: Order ID
            
        Returns:
            Order details dict or None
        """
        try:
            order = self.trading_client.get_order_by_id(order_id)
            return {
                "order_id": str(order.id),
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side.value,
                "type": order.type.value,
                "status": order.status.value,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
            }
        except Exception as e:
            print(f"⚠️ Error getting order {order_id}: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.trading_client.cancel_order_by_id(order_id)
            return True
        except Exception as e:
            print(f"❌ Error canceling order {order_id}: {e}")
            return False
    
    def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Close entire position for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Order details dict
        """
        try:
            order = self.trading_client.close_position(symbol)
            return {
                "success": True,
                "order_id": str(order.id),
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side.value,
                "status": order.status.value,
            }
        except Exception as e:
            print(f"❌ Error closing position for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol
            }
    
    def close_all_positions(self) -> List[Dict[str, Any]]:
        """
        Close all open positions
        
        Returns:
            List of order details dicts
        """
        try:
            orders = self.trading_client.close_all_positions(cancel_orders=True)
            results = []
            for order in orders:
                results.append({
                    "success": True,
                    "order_id": str(order.id),
                    "symbol": order.symbol,
                    "qty": float(order.qty),
                    "side": order.side.value,
                    "status": order.status.value,
                })
            return results
        except Exception as e:
            print(f"❌ Error closing all positions: {e}")
            return []
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary
        
        Returns:
            Dict with account info and all positions
        """
        try:
            account = self.get_account()
            positions = self.get_positions()
            
            total_position_value = sum(
                pos["market_value"] for pos in positions.values()
            )
            total_unrealized_pl = sum(
                pos["unrealized_pl"] for pos in positions.values()
            )
            
            return {
                "account": account,
                "positions": positions,
                "summary": {
                    "total_positions": len(positions),
                    "total_position_value": total_position_value,
                    "total_unrealized_pl": total_unrealized_pl,
                    "cash": account["cash"],
                    "equity": account["equity"],
                }
            }
        except Exception as e:
            print(f"❌ Error getting portfolio summary: {e}")
            raise


# Singleton instance for easy access
_alpaca_client: Optional[AlpacaTradingClient] = None

def get_alpaca_client(
    api_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    paper: bool = True
) -> AlpacaTradingClient:
    """
    Get or create Alpaca trading client (singleton pattern)
    
    Args:
        api_key: Alpaca API key (optional)
        secret_key: Alpaca secret key (optional)
        paper: Paper trading mode (default: True)
        
    Returns:
        AlpacaTradingClient instance
    """
    global _alpaca_client
    if _alpaca_client is None:
        _alpaca_client = AlpacaTradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper
        )
    return _alpaca_client


if __name__ == "__main__":
    # Test the Alpaca client
    print("🧪 Testing Alpaca Trading Client...")
    
    try:
        client = get_alpaca_client()
        
        # Test account info
        print("\n📊 Account Info:")
        account = client.get_account()
        for key, value in account.items():
            print(f"  {key}: {value}")
        
        # Test positions
        print("\n📈 Current Positions:")
        positions = client.get_positions()
        if positions:
            for symbol, pos in positions.items():
                print(f"  {symbol}: {pos['qty']} shares @ ${pos['avg_entry_price']:.2f}")
        else:
            print("  No open positions")
        
        # Test price fetching
        print("\n💰 Latest Prices:")
        prices = client.get_latest_prices(["AAPL", "MSFT", "GOOGL"])
        for symbol, price in prices.items():
            if price:
                print(f"  {symbol}: ${price:.2f}")
        
        print("\n✅ Alpaca client test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("Make sure your ALPACA_API_KEY and ALPACA_SECRET_KEY are set in .env")
