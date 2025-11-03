"""
Alpaca Real-Time Data Feed Integration

This module provides real-time market data using Alpaca's Data API v2 with SSE protocol.
Supports:
- Real-time quotes (bid/ask prices)
- Real-time trades (last trade price)
- Real-time bars (OHLCV data)
- Historical bars (for backtesting)
- Multiple symbols simultaneously
"""

import os
import sys
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta, date
from collections import defaultdict
import asyncio
from decimal import Decimal
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

# Alpaca Data SDK imports
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import (
    StockLatestQuoteRequest,
    StockBarsRequest,
    StockLatestTradeRequest
)
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.models import Bar, Quote, Trade
from alpaca.data.enums import DataFeed


class AlpacaDataFeed:
    """
    Real-time and historical data feed using Alpaca's API
    
    Provides both real-time streaming data and historical data access.
    Supports multiple symbols and various timeframes.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        feed: str = "iex"  # 'iex' (free) or 'sip' (paid, more comprehensive)
    ):
        """
        Initialize Alpaca Data Feed
        
        Args:
            api_key: Alpaca API key (from env if not provided)
            secret_key: Alpaca secret key (from env if not provided)
            feed: Data feed type - 'iex' (free, IEX only) or 'sip' (paid, all exchanges)
        """
        # Get API credentials
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        
        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca API credentials not found. "
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file"
            )
        
        # Convert feed string to DataFeed enum
        self.feed = DataFeed.IEX if feed.lower() == "iex" else DataFeed.SIP
        
        # Initialize historical data client
        self.historical_client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )
        
        # Initialize streaming client (will be used for real-time data)
        self.stream_client = StockDataStream(
            api_key=self.api_key,
            secret_key=self.secret_key,
            feed=self.feed
        )
        
        # Cache for latest data
        self.latest_quotes: Dict[str, Quote] = {}
        self.latest_trades: Dict[str, Trade] = {}
        self.latest_bars: Dict[str, Bar] = {}
        
        # Streaming status
        self.is_streaming = False
        
        print(f"✅ Alpaca Data Feed initialized (feed: {feed})")
    
    # ==================== LATEST DATA (Real-time) ====================
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest quote (bid/ask) for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quote data dict with bid_price, ask_price, bid_size, ask_size
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self.historical_client.get_stock_latest_quote(request)
            
            if symbol in quotes:
                quote = quotes[symbol]
                return {
                    "symbol": symbol,
                    "bid_price": float(quote.bid_price),
                    "ask_price": float(quote.ask_price),
                    "bid_size": int(quote.bid_size),
                    "ask_size": int(quote.ask_size),
                    "timestamp": quote.timestamp.isoformat(),
                }
            return None
        except Exception as e:
            print(f"⚠️ Error getting quote for {symbol}: {e}")
            return None
    
    def get_latest_quotes(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Get latest quotes for multiple symbols
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to quote data
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbols)
            quotes = self.historical_client.get_stock_latest_quote(request)
            
            result = {}
            for symbol in symbols:
                if symbol in quotes:
                    quote = quotes[symbol]
                    result[symbol] = {
                        "symbol": symbol,
                        "bid_price": float(quote.bid_price),
                        "ask_price": float(quote.ask_price),
                        "bid_size": int(quote.bid_size),
                        "ask_size": int(quote.ask_size),
                        "timestamp": quote.timestamp.isoformat(),
                    }
                else:
                    result[symbol] = None
            return result
        except Exception as e:
            print(f"⚠️ Error getting quotes: {e}")
            return {symbol: None for symbol in symbols}
    
    def get_latest_trade(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest trade (last price) for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Trade data dict with price, size, timestamp
        """
        try:
            request = StockLatestTradeRequest(symbol_or_symbols=symbol)
            trades = self.historical_client.get_stock_latest_trade(request)
            
            if symbol in trades:
                trade = trades[symbol]
                return {
                    "symbol": symbol,
                    "price": float(trade.price),
                    "size": int(trade.size),
                    "timestamp": trade.timestamp.isoformat(),
                    "exchange": trade.exchange,
                }
            return None
        except Exception as e:
            print(f"⚠️ Error getting trade for {symbol}: {e}")
            return None
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get latest price for a symbol (from last trade)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Latest price or None
        """
        trade = self.get_latest_trade(symbol)
        if trade:
            return trade["price"]
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
            request = StockLatestTradeRequest(symbol_or_symbols=symbols)
            trades = self.historical_client.get_stock_latest_trade(request)
            
            result = {}
            for symbol in symbols:
                if symbol in trades:
                    result[symbol] = float(trades[symbol].price)
                else:
                    result[symbol] = None
            return result
        except Exception as e:
            print(f"⚠️ Error getting prices: {e}")
            return {symbol: None for symbol in symbols}
    
    # ==================== HISTORICAL BARS ====================
    
    def get_bars(
        self,
        symbols: List[str],
        start: datetime,
        end: datetime,
        timeframe: TimeFrame = TimeFrame.Day
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get historical bars (OHLCV data) for symbols
        
        Args:
            symbols: List of stock symbols
            start: Start datetime
            end: End datetime
            timeframe: Bar timeframe (Day, Hour, Minute, etc.)
            
        Returns:
            Dict mapping symbol to list of bars
        """
        try:
            request = StockBarsRequest(
                symbol_or_symbols=symbols,
                start=start,
                end=end,
                timeframe=timeframe
            )
            
            bars_response = self.historical_client.get_stock_bars(request)
            
            result = {}
            for symbol in symbols:
                if symbol in bars_response.data:
                    bars = bars_response.data[symbol]
                    result[symbol] = [
                        {
                            "timestamp": bar.timestamp.isoformat(),
                            "open": float(bar.open),
                            "high": float(bar.high),
                            "low": float(bar.low),
                            "close": float(bar.close),
                            "volume": int(bar.volume),
                            "vwap": float(bar.vwap) if bar.vwap else None,
                            "trade_count": bar.trade_count,
                        }
                        for bar in bars
                    ]
                else:
                    result[symbol] = []
            
            return result
        except Exception as e:
            print(f"⚠️ Error getting bars: {e}")
            return {symbol: [] for symbol in symbols}
    
    def get_daily_bars(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get daily bars for symbols (convenient wrapper)
        
        Args:
            symbols: List of stock symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Dict mapping symbol to list of daily bars
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        return self.get_bars(symbols, start, end, TimeFrame.Day)
    
    def get_bar_for_date(
        self,
        symbol: str,
        date_str: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get OHLCV bar for a specific date
        
        Args:
            symbol: Stock symbol
            date_str: Date (YYYY-MM-DD)
            
        Returns:
            Bar data dict or None
        """
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        end_date = target_date + timedelta(days=1)
        
        bars = self.get_bars([symbol], target_date, end_date, TimeFrame.Day)
        
        if symbol in bars and len(bars[symbol]) > 0:
            return bars[symbol][0]
        return None
    
    def get_opening_price(self, symbol: str, date_str: str) -> Optional[float]:
        """
        Get opening price for a symbol on a specific date
        
        Args:
            symbol: Stock symbol
            date_str: Date (YYYY-MM-DD)
            
        Returns:
            Opening price or None
        """
        bar = self.get_bar_for_date(symbol, date_str)
        if bar:
            return bar["open"]
        return None
    
    def get_closing_price(self, symbol: str, date_str: str) -> Optional[float]:
        """
        Get closing price for a symbol on a specific date
        
        Args:
            symbol: Stock symbol
            date_str: Date (YYYY-MM-DD)
            
        Returns:
            Closing price or None
        """
        bar = self.get_bar_for_date(symbol, date_str)
        if bar:
            return bar["close"]
        return None
    
    # ==================== REAL-TIME STREAMING ====================
    
    async def subscribe_quotes(
        self,
        symbols: List[str],
        handler: Callable[[Quote], None]
    ):
        """
        Subscribe to real-time quote updates
        
        Args:
            symbols: List of symbols to subscribe to
            handler: Callback function to handle quote updates
        """
        async def quote_handler(data: Quote):
            self.latest_quotes[data.symbol] = data
            if handler:
                handler(data)
        
        self.stream_client.subscribe_quotes(quote_handler, *symbols)
    
    async def subscribe_trades(
        self,
        symbols: List[str],
        handler: Callable[[Trade], None]
    ):
        """
        Subscribe to real-time trade updates
        
        Args:
            symbols: List of symbols to subscribe to
            handler: Callback function to handle trade updates
        """
        async def trade_handler(data: Trade):
            self.latest_trades[data.symbol] = data
            if handler:
                handler(data)
        
        self.stream_client.subscribe_trades(trade_handler, *symbols)
    
    async def subscribe_bars(
        self,
        symbols: List[str],
        handler: Callable[[Bar], None]
    ):
        """
        Subscribe to real-time bar updates
        
        Args:
            symbols: List of symbols to subscribe to
            handler: Callback function to handle bar updates
        """
        async def bar_handler(data: Bar):
            self.latest_bars[data.symbol] = data
            if handler:
                handler(data)
        
        self.stream_client.subscribe_bars(bar_handler, *symbols)
    
    async def start_streaming(self):
        """
        Start real-time data streaming
        """
        if not self.is_streaming:
            self.is_streaming = True
            print("🔴 Starting real-time data stream...")
            await self.stream_client.run()
    
    async def stop_streaming(self):
        """
        Stop real-time data streaming
        """
        if self.is_streaming:
            self.is_streaming = False
            await self.stream_client.close()
            print("⏹️ Real-time data stream stopped")


# ==================== CONVENIENCE FUNCTIONS ====================

_data_feed: Optional[AlpacaDataFeed] = None

def get_data_feed(
    api_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    feed: str = "iex"
) -> AlpacaDataFeed:
    """
    Get or create Alpaca data feed (singleton pattern)
    
    Args:
        api_key: Alpaca API key (optional)
        secret_key: Alpaca secret key (optional)
        feed: Data feed type - 'iex' or 'sip'
        
    Returns:
        AlpacaDataFeed instance
    """
    global _data_feed
    if _data_feed is None:
        _data_feed = AlpacaDataFeed(
            api_key=api_key,
            secret_key=secret_key,
            feed=feed
        )
    return _data_feed


# ==================== TESTING ====================

if __name__ == "__main__":
    print("🧪 Testing Alpaca Data Feed...")
    
    try:
        feed = get_data_feed()
        
        # Test 1: Latest prices
        print("\n💰 Test 1: Latest Prices")
        prices = feed.get_latest_prices(["AAPL", "MSFT", "GOOGL"])
        for symbol, price in prices.items():
            if price:
                print(f"  {symbol}: ${price:.2f}")
        
        # Test 2: Latest quote
        print("\n📊 Test 2: Latest Quote (AAPL)")
        quote = feed.get_latest_quote("AAPL")
        if quote:
            print(f"  Bid: ${quote['bid_price']:.2f} x {quote['bid_size']}")
            print(f"  Ask: ${quote['ask_price']:.2f} x {quote['ask_size']}")
        
        # Test 3: Historical bars
        print("\n📈 Test 3: Historical Bars (Last 5 days)")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        bars = feed.get_bars(["AAPL"], start_date, end_date, TimeFrame.Day)
        
        if "AAPL" in bars:
            for bar in bars["AAPL"][:5]:
                print(f"  {bar['timestamp'][:10]}: O=${bar['open']:.2f} C=${bar['close']:.2f} V={bar['volume']:,}")
        
        # Test 4: Specific date
        print("\n📅 Test 4: Specific Date Bar")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        bar = feed.get_bar_for_date("AAPL", yesterday)
        if bar:
            print(f"  Date: {yesterday}")
            print(f"  Open: ${bar['open']:.2f}")
            print(f"  High: ${bar['high']:.2f}")
            print(f"  Low: ${bar['low']:.2f}")
            print(f"  Close: ${bar['close']:.2f}")
            print(f"  Volume: {bar['volume']:,}")
        
        print("\n✅ Alpaca Data Feed test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("Make sure your ALPACA_API_KEY and ALPACA_SECRET_KEY are set in .env")
