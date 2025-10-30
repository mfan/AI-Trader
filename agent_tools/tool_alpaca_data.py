"""
Alpaca Data Feed MCP Service

This module provides Model Context Protocol (MCP) tools for AI agents to access
real-time and historical market data via Alpaca's Data API.

Available Tools:
1. get_latest_quote - Get current bid/ask prices for a symbol
2. get_latest_quotes - Get current bid/ask prices for multiple symbols
3. get_latest_trade - Get last trade price for a symbol
4. get_latest_price - Get current market price for a symbol
5. get_stock_bars - Get historical OHLCV bars for a symbol
6. get_daily_bars - Get daily bars for a date range
7. get_bar_for_date - Get OHLCV data for specific date (like get_price_local)
8. get_opening_price - Get opening price for a specific date

Usage:
    Run as MCP service:
    $ python agent_tools/tool_alpaca_data.py
    
    Or import in code:
    from agent_tools.tool_alpaca_data import get_bar_for_date_function
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from fastmcp import FastMCP
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

# Import Alpaca data feed client
from tools.alpaca_data_feed import AlpacaDataFeed

# Initialize MCP server
mcp = FastMCP("AlpacaData")

# Global data feed client (lazy initialization)
_data_feed: Optional[AlpacaDataFeed] = None


def _get_data_feed() -> AlpacaDataFeed:
    """Get or create the Alpaca data feed client."""
    global _data_feed
    if _data_feed is None:
        _data_feed = AlpacaDataFeed()
    return _data_feed


def _validate_date(date_str: str) -> None:
    """Validate date format is YYYY-MM-DD."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("date must be in YYYY-MM-DD format") from exc


# ============================================================================
# MCP Tools - Real-time Data
# ============================================================================

@mcp.tool()
def get_latest_quote(symbol: str) -> Dict[str, Any]:
    """Get latest bid/ask quote for a stock symbol.
    
    Returns current bid price, ask price, bid size, and ask size.
    Useful for getting the current market spread.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        
    Returns:
        Dictionary containing:
        - symbol: Stock symbol
        - bid_price: Current bid price
        - ask_price: Current ask price
        - bid_size: Bid size (shares)
        - ask_size: Ask size (shares)
        - timestamp: Quote timestamp
        - error: Error message if request failed
    """
    try:
        feed = _get_data_feed()
        quote = feed.get_latest_quote(symbol)
        
        if quote is None:
            return {
                "error": f"No quote data available for {symbol}",
                "symbol": symbol
            }
            
        return {
            "symbol": symbol,
            "bid_price": float(quote.bid_price),
            "ask_price": float(quote.ask_price),
            "bid_size": quote.bid_size,
            "ask_size": quote.ask_size,
            "timestamp": quote.timestamp.isoformat(),
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get quote: {str(e)}",
            "symbol": symbol
        }


@mcp.tool()
def get_latest_quotes(symbols: List[str]) -> Dict[str, Any]:
    """Get latest bid/ask quotes for multiple stock symbols.
    
    Efficient batch request for getting quotes for many symbols at once.
    
    Args:
        symbols: List of stock symbols (e.g., ['AAPL', 'TSLA', 'MSFT'])
        
    Returns:
        Dictionary containing:
        - quotes: Dictionary mapping symbol to quote data
        - error: Error message if request failed
    """
    try:
        feed = _get_data_feed()
        quotes_dict = feed.get_latest_quotes(symbols)
        
        result = {"quotes": {}}
        
        for symbol, quote in quotes_dict.items():
            if quote is not None:
                result["quotes"][symbol] = {
                    "bid_price": float(quote.bid_price),
                    "ask_price": float(quote.ask_price),
                    "bid_size": quote.bid_size,
                    "ask_size": quote.ask_size,
                    "timestamp": quote.timestamp.isoformat(),
                }
            else:
                result["quotes"][symbol] = {"error": "No data available"}
                
        return result
        
    except Exception as e:
        return {
            "error": f"Failed to get quotes: {str(e)}",
            "symbols": symbols
        }


@mcp.tool()
def get_latest_trade(symbol: str) -> Dict[str, Any]:
    """Get latest trade information for a stock symbol.
    
    Returns the last trade price, size, and timestamp.
    Useful for getting the actual last executed trade.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        
    Returns:
        Dictionary containing:
        - symbol: Stock symbol
        - price: Last trade price
        - size: Trade size (shares)
        - timestamp: Trade timestamp
        - exchange: Exchange code
        - error: Error message if request failed
    """
    try:
        feed = _get_data_feed()
        trade = feed.get_latest_trade(symbol)
        
        if trade is None:
            return {
                "error": f"No trade data available for {symbol}",
                "symbol": symbol
            }
            
        return {
            "symbol": symbol,
            "price": float(trade.price),
            "size": trade.size,
            "timestamp": trade.timestamp.isoformat(),
            "exchange": trade.exchange,
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get trade: {str(e)}",
            "symbol": symbol
        }


@mcp.tool()
def get_latest_price(symbol: str) -> Dict[str, Any]:
    """Get current market price for a stock symbol.
    
    Returns the best available current price (from latest trade or quote).
    This is the most common function for getting "current price".
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        
    Returns:
        Dictionary containing:
        - symbol: Stock symbol
        - price: Current market price
        - timestamp: Price timestamp
        - source: Data source ('trade' or 'quote')
        - error: Error message if request failed
    """
    try:
        feed = _get_data_feed()
        price = feed.get_latest_price(symbol)
        
        if price is None:
            return {
                "error": f"No price data available for {symbol}",
                "symbol": symbol
            }
            
        return {
            "symbol": symbol,
            "price": float(price),
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get price: {str(e)}",
            "symbol": symbol
        }


# ============================================================================
# MCP Tools - Historical Data (Bars/OHLCV)
# ============================================================================

@mcp.tool()
def get_stock_bars(
    symbol: str,
    start_date: str,
    end_date: str,
    timeframe: str = "1Day"
) -> Dict[str, Any]:
    """Get historical OHLCV bars for a stock symbol.
    
    Returns bars (candlestick data) for the specified time range and timeframe.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        timeframe: Bar timeframe, one of:
                  '1Min', '5Min', '15Min', '30Min', '1Hour', '1Day' (default)
        
    Returns:
        Dictionary containing:
        - symbol: Stock symbol
        - timeframe: Requested timeframe
        - bars: List of bar data, each containing:
            - timestamp: Bar timestamp
            - open: Opening price
            - high: High price
            - low: Low price
            - close: Closing price
            - volume: Trading volume
            - trade_count: Number of trades (if available)
            - vwap: Volume-weighted average price (if available)
        - error: Error message if request failed
    """
    try:
        _validate_date(start_date)
        _validate_date(end_date)
        
        feed = _get_data_feed()
        bars = feed.get_bars(symbol, start_date, end_date, timeframe)
        
        if not bars:
            return {
                "error": f"No bar data available for {symbol} from {start_date} to {end_date}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "timeframe": timeframe
            }
            
        bars_data = []
        for bar in bars:
            bars_data.append({
                "timestamp": bar.timestamp.isoformat(),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": bar.volume,
                "trade_count": bar.trade_count,
                "vwap": float(bar.vwap) if bar.vwap else None,
            })
            
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(bars_data),
            "bars": bars_data,
        }
        
    except ValueError as e:
        return {
            "error": str(e),
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        }
    except Exception as e:
        return {
            "error": f"Failed to get bars: {str(e)}",
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        }


@mcp.tool()
def get_daily_bars(symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """Get daily OHLCV bars for a stock symbol.
    
    Simplified version of get_stock_bars with daily timeframe only.
    Useful for backtesting and historical analysis.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Dictionary containing:
        - symbol: Stock symbol
        - bars: List of daily bar data
        - error: Error message if request failed
    """
    try:
        _validate_date(start_date)
        _validate_date(end_date)
        
        feed = _get_data_feed()
        bars = feed.get_daily_bars(symbol, start_date, end_date)
        
        if not bars:
            return {
                "error": f"No daily bar data available for {symbol} from {start_date} to {end_date}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
            
        bars_data = []
        for bar in bars:
            bars_data.append({
                "date": bar.timestamp.strftime("%Y-%m-%d"),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": bar.volume,
                "trade_count": bar.trade_count,
                "vwap": float(bar.vwap) if bar.vwap else None,
            })
            
        return {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(bars_data),
            "bars": bars_data,
        }
        
    except ValueError as e:
        return {
            "error": str(e),
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        }
    except Exception as e:
        return {
            "error": f"Failed to get daily bars: {str(e)}",
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        }


@mcp.tool()
def get_bar_for_date(symbol: str, date: str) -> Dict[str, Any]:
    """Get OHLCV data for a specific stock and date.
    
    This is the Alpaca equivalent of get_price_local() - returns OHLCV data
    for a single trading day. Compatible with existing AI agent workflows.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        date: Date in YYYY-MM-DD format
        
    Returns:
        Dictionary containing:
        - symbol: Stock symbol
        - date: Requested date
        - ohlcv: Dictionary with open, high, low, close, volume
        - error: Error message if data not found
    """
    try:
        _validate_date(date)
        
        feed = _get_data_feed()
        bar = feed.get_bar_for_date(symbol, date)
        
        if bar is None:
            return {
                "error": f"No bar data available for {symbol} on {date}. Market may have been closed.",
                "symbol": symbol,
                "date": date
            }
            
        return {
            "symbol": symbol,
            "date": date,
            "ohlcv": {
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": bar.volume,
            },
            "additional_data": {
                "trade_count": bar.trade_count,
                "vwap": float(bar.vwap) if bar.vwap else None,
            }
        }
        
    except ValueError as e:
        return {
            "error": str(e),
            "symbol": symbol,
            "date": date
        }
    except Exception as e:
        return {
            "error": f"Failed to get bar data: {str(e)}",
            "symbol": symbol,
            "date": date
        }


@mcp.tool()
def get_opening_price(symbol: str, date: str) -> Dict[str, Any]:
    """Get opening price for a specific stock and date.
    
    Simplified function to get just the opening price for a trading day.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        date: Date in YYYY-MM-DD format
        
    Returns:
        Dictionary containing:
        - symbol: Stock symbol
        - date: Requested date
        - opening_price: Opening price for that day
        - error: Error message if data not found
    """
    try:
        _validate_date(date)
        
        feed = _get_data_feed()
        price = feed.get_opening_price(symbol, date)
        
        if price is None:
            return {
                "error": f"No opening price available for {symbol} on {date}",
                "symbol": symbol,
                "date": date
            }
            
        return {
            "symbol": symbol,
            "date": date,
            "opening_price": float(price),
        }
        
    except ValueError as e:
        return {
            "error": str(e),
            "symbol": symbol,
            "date": date
        }
    except Exception as e:
        return {
            "error": f"Failed to get opening price: {str(e)}",
            "symbol": symbol,
            "date": date
        }


# ============================================================================
# Standalone Functions (for direct use without MCP)
# ============================================================================

def get_bar_for_date_function(symbol: str, date: str) -> Dict[str, Any]:
    """Standalone function to get OHLCV data for a specific date.
    
    This can be imported and used directly without MCP server.
    Equivalent to get_price_local_function() but uses Alpaca API.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        date: Date in YYYY-MM-DD format
        
    Returns:
        Dictionary with symbol, date, and ohlcv data
    """
    return get_bar_for_date(symbol, date)


def get_latest_price_function(symbol: str) -> Dict[str, Any]:
    """Standalone function to get latest market price.
    
    This can be imported and used directly without MCP server.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        
    Returns:
        Dictionary with symbol and current price
    """
    return get_latest_price(symbol)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("ALPACA_DATA_HTTP_PORT", "8004"))
    
    print(f"Starting Alpaca Data MCP Service on port {port}...")
    print("Available tools:")
    print("  - get_latest_quote: Get current bid/ask prices")
    print("  - get_latest_quotes: Get quotes for multiple symbols")
    print("  - get_latest_trade: Get last trade information")
    print("  - get_latest_price: Get current market price")
    print("  - get_stock_bars: Get historical OHLCV bars")
    print("  - get_daily_bars: Get daily bars for date range")
    print("  - get_bar_for_date: Get OHLCV for specific date (like get_price_local)")
    print("  - get_opening_price: Get opening price for specific date")
    
    mcp.run(transport="http", port=port)
