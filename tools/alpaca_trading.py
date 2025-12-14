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
    GetCalendarRequest,
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
from datetime import date

from tools.retry_utils import retry_with_backoff
from configs.settings import SystemConfig


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
        
        # Auto-select API URL based on trading mode (unless explicitly provided)
        if base_url:
            # Use explicitly provided URL
            api_url = base_url
        elif os.getenv("ALPACA_BASE_URL"):
            # Use URL from environment if set
            api_url = os.getenv("ALPACA_BASE_URL")
        else:
            # Auto-select based on paper trading mode
            api_url = "https://paper-api.alpaca.markets" if self.paper else "https://api.alpaca.markets"
        
        # Initialize trading client
        self.trading_client = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=self.paper,
            url_override=api_url
        )
        
        # Initialize data client (no auth required for basic market data)
        self.data_client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )
        
        # Log initialization with mode and URL
        mode = 'PAPER' if self.paper else 'LIVE'
        print(f"✅ Alpaca client initialized ({mode} trading)")
        print(f"   API URL: {api_url}")
    
    @retry_with_backoff(retries=SystemConfig.API_MAX_RETRIES, delay=SystemConfig.API_RETRY_DELAY)
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
    
    @retry_with_backoff(retries=SystemConfig.API_MAX_RETRIES, delay=SystemConfig.API_RETRY_DELAY)
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
    
    @retry_with_backoff(retries=SystemConfig.API_MAX_RETRIES, delay=SystemConfig.API_RETRY_DELAY)
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
    
    @retry_with_backoff(retries=SystemConfig.API_MAX_RETRIES, delay=SystemConfig.API_RETRY_DELAY)
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
    
    @retry_with_backoff(retries=SystemConfig.API_MAX_RETRIES, delay=SystemConfig.API_RETRY_DELAY)
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
    
    @retry_with_backoff(retries=SystemConfig.API_MAX_RETRIES, delay=SystemConfig.API_RETRY_DELAY)
    def get_clock(self) -> Any:
        """
        Get market clock from Alpaca API
        
        Returns:
            Clock object with is_open, next_open, next_close, timestamp
        """
        try:
            return self.trading_client.get_clock()
        except Exception as e:
            print(f"❌ Error getting market clock: {e}")
            raise
    
    def is_market_open_today(self) -> bool:
        """
        Check if market has a trading session today (not a holiday or weekend)
        
        Returns:
            bool: True if today has a trading session, False if holiday/weekend
        """
        try:
            today = date.today()
            request = GetCalendarRequest(start=today, end=today)
            calendar = self.trading_client.get_calendar(filters=request)
            return bool(calendar)  # Returns True if trading session exists
        except Exception as e:
            print(f"❌ Error checking market calendar: {e}")
            return False
    
    def is_market_open_now(self) -> Tuple[bool, str]:
        """
        Check if market is currently open using Alpaca's clock API
        
        This is more reliable than time-based checks as it accounts for:
        - Market holidays (Thanksgiving, Christmas, etc.)
        - Early closes (half days)
        - Unexpected closures
        
        Returns:
            tuple: (is_open, status_message)
        """
        try:
            clock = self.get_clock()
            
            if clock.is_open:
                return True, "Market is OPEN"
            else:
                # Check if today has a trading session
                has_session_today = self.is_market_open_today()
                
                if has_session_today:
                    return False, f"Market is CLOSED (opens at {clock.next_open})"
                else:
                    return False, f"Market is CLOSED - No trading session today (next open: {clock.next_open})"
                    
        except Exception as e:
            print(f"❌ Error checking market status: {e}")
            return False, f"Market status unknown (error: {e})"
    
    @retry_with_backoff(retries=SystemConfig.API_MAX_RETRIES, delay=SystemConfig.API_RETRY_DELAY)
    def _submit_order_with_retry(self, order_data):
        """Internal helper to submit orders with retry logic"""
        return self.trading_client.submit_order(order_data)

    @retry_with_backoff(retries=SystemConfig.API_MAX_RETRIES, delay=SystemConfig.API_RETRY_DELAY)
    def _close_position_with_retry(self, symbol_or_id):
        """Internal helper to close position with retry logic"""
        return self.trading_client.close_position(symbol_or_id)

    def buy_market(
        self,
        symbol: str,
        qty: int,
        time_in_force: TimeInForce = TimeInForce.DAY,
        extended_hours: bool = False
    ) -> Dict[str, Any]:
        """
        Place market buy order
        
        Args:
            symbol: Stock symbol
            qty: Quantity to buy
            time_in_force: Order time in force (default: DAY)
            extended_hours: Allow execution during pre-market (4AM-9:30AM ET) 
                          and post-market (4PM-8PM ET) hours (default: False)
            
        Returns:
            Order details dict
        """
        try:
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=time_in_force,
                extended_hours=extended_hours
            )
            
            order = self._submit_order_with_retry(order_data)
            
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
                "extended_hours": extended_hours,
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
        time_in_force: TimeInForce = TimeInForce.DAY,
        extended_hours: bool = False,
        cancel_pending_orders: bool = True
    ) -> Dict[str, Any]:
        """
        Place market sell order
        
        Args:
            symbol: Stock symbol
            qty: Quantity to sell
            time_in_force: Order time in force (default: DAY)
            extended_hours: Allow execution during pre-market (4AM-9:30AM ET) 
                          and post-market (4PM-8PM ET) hours (default: False)
            cancel_pending_orders: Cancel any pending orders for this symbol first
                                   to avoid "held_for_orders" errors (default: True)
            
        Returns:
            Order details dict
        """
        try:
            # Cancel pending orders to free up shares that may be "held_for_orders"
            if cancel_pending_orders:
                canceled = self.cancel_orders_for_symbol(symbol)
                if canceled > 0:
                    import time
                    time.sleep(0.5)  # Brief delay to let cancellation settle
            
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=time_in_force,
                extended_hours=extended_hours
            )
            
            order = self._submit_order_with_retry(order_data)
            
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
                "extended_hours": extended_hours,
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
        time_in_force: TimeInForce = TimeInForce.DAY,
        extended_hours: bool = False
    ) -> Dict[str, Any]:
        """
        Place limit buy order
        
        Args:
            symbol: Stock symbol
            qty: Quantity to buy
            limit_price: Limit price
            time_in_force: Order time in force (default: DAY)
            extended_hours: Allow execution during pre-market (4AM-9:30AM ET) 
                          and post-market (4PM-8PM ET) hours (default: False)
            
        Returns:
            Order details dict
        """
        try:
            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=time_in_force,
                limit_price=limit_price,
                extended_hours=extended_hours
            )
            
            order = self._submit_order_with_retry(order_data)
            
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
                "extended_hours": extended_hours,
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
    
    def sell_limit(
        self,
        symbol: str,
        qty: int,
        limit_price: float,
        time_in_force: TimeInForce = TimeInForce.DAY,
        extended_hours: bool = False,
        cancel_pending_orders: bool = True
    ) -> Dict[str, Any]:
        """
        Place limit sell order
        
        Args:
            symbol: Stock symbol
            qty: Quantity to sell
            limit_price: Limit price
            time_in_force: Order time in force (default: DAY)
            extended_hours: Allow execution during pre-market (4AM-9:30AM ET) 
                          and post-market (4PM-8PM ET) hours (default: False)
            cancel_pending_orders: Cancel any pending orders for this symbol first
                                   to avoid "held_for_orders" errors (default: True)
            
        Returns:
            Order details dict
        """
        try:
            # Cancel pending orders to free up shares that may be "held_for_orders"
            if cancel_pending_orders:
                canceled = self.cancel_orders_for_symbol(symbol)
                if canceled > 0:
                    import time
                    time.sleep(0.5)  # Brief delay to let cancellation settle
            
            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=time_in_force,
                limit_price=limit_price,
                extended_hours=extended_hours
            )
            
            order = self._submit_order_with_retry(order_data)
            
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
                "extended_hours": extended_hours,
            }
        except Exception as e:
            print(f"❌ Error placing limit sell order for {symbol}: {e}")
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
    
    def get_open_orders_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get all open/pending orders for a specific symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of open orders for the symbol
        """
        try:
            request = GetOrdersRequest(
                status=QueryOrderStatus.OPEN,
                symbols=[symbol]
            )
            orders = self.trading_client.get_orders(request)
            
            result = []
            for order in orders:
                result.append({
                    "order_id": str(order.id),
                    "symbol": order.symbol,
                    "qty": float(order.qty),
                    "side": order.side.value,
                    "type": order.type.value,
                    "status": order.status.value,
                    "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                })
            return result
        except Exception as e:
            print(f"⚠️ Error getting open orders for {symbol}: {e}")
            return []
    
    def cancel_orders_for_symbol(self, symbol: str) -> int:
        """
        Cancel all open orders for a specific symbol.
        
        This is critical to avoid "held_for_orders" errors when trying to sell
        shares that are reserved by pending orders.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Number of orders canceled
        """
        try:
            open_orders = self.get_open_orders_for_symbol(symbol)
            canceled_count = 0
            
            for order in open_orders:
                order_id = order["order_id"]
                if self.cancel_order(order_id):
                    print(f"✅ Canceled order {order_id} for {symbol}")
                    canceled_count += 1
                else:
                    print(f"⚠️ Failed to cancel order {order_id} for {symbol}")
            
            if canceled_count > 0:
                print(f"🧹 Canceled {canceled_count} pending order(s) for {symbol}")
            
            return canceled_count
        except Exception as e:
            print(f"❌ Error canceling orders for {symbol}: {e}")
            return 0

    def close_position(self, symbol: str, cancel_pending_orders: bool = True) -> Dict[str, Any]:
        """
        Close entire position for a symbol
        
        Args:
            symbol: Stock symbol
            cancel_pending_orders: Cancel any pending orders for this symbol first
                                   to avoid "held_for_orders" errors (default: True)
            
        Returns:
            Order details dict
        """
        try:
            # Cancel pending orders to free up shares that may be "held_for_orders"
            if cancel_pending_orders:
                canceled = self.cancel_orders_for_symbol(symbol)
                if canceled > 0:
                    import time
                    time.sleep(0.5)  # Brief delay to let cancellation settle
            
            order = self._close_position_with_retry(symbol)
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
