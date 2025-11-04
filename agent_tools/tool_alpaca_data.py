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
from tools.technical_indicators import get_ta_engine
import numpy as np

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
        
        # quote is already a dictionary from AlpacaDataFeed
        return quote
        
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
        
        # quotes_dict already contains dictionaries from AlpacaDataFeed
        result = {"quotes": quotes_dict}
                
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
        
        # trade is already a dictionary from AlpacaDataFeed
        # Validate it has the required fields
        if not isinstance(trade, dict):
            return {
                "error": f"Invalid trade data format for {symbol}",
                "symbol": symbol
            }
        
        return trade
        
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
        
        # price is a float from AlpacaDataFeed
        if not isinstance(price, (int, float)):
            return {
                "error": f"Invalid price data format for {symbol}",
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
        
        # Get bars - AlpacaDataFeed.get_daily_bars returns dict[symbol -> list[bar_dicts]]
        bars_dict = feed.get_daily_bars([symbol], start_date, end_date)
        
        # Validate response format
        if not isinstance(bars_dict, dict):
            return {
                "error": f"Invalid response format from data feed for {symbol}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "timeframe": timeframe
            }
        
        bars_list = bars_dict.get(symbol, [])
        
        if not bars_list:
            return {
                "error": f"No bar data available for {symbol} from {start_date} to {end_date}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "timeframe": timeframe
            }
        
        # Validate bars are dictionaries with required fields
        if not isinstance(bars_list, list):
            return {
                "error": f"Invalid bars format for {symbol}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "timeframe": timeframe
            }
        
        # Validate at least the first bar has required fields
        if bars_list and isinstance(bars_list[0], dict):
            required_fields = ['open', 'high', 'low', 'close', 'volume']
            missing_fields = [f for f in required_fields if f not in bars_list[0]]
            if missing_fields:
                return {
                    "error": f"Missing required fields in bar data: {missing_fields}",
                    "symbol": symbol,
                    "start_date": start_date,
                    "end_date": end_date,
                    "timeframe": timeframe
                }
        
        # bars_list is already a list of dictionaries from AlpacaDataFeed
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(bars_list),
            "bars": bars_list,
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
        # get_daily_bars returns dict[symbol -> list[bar_dicts]]
        bars_dict = feed.get_daily_bars([symbol], start_date, end_date)
        
        # Validate response format
        if not isinstance(bars_dict, dict):
            return {
                "error": f"Invalid response format from data feed for {symbol}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
        
        bars_list = bars_dict.get(symbol, [])
        
        if not bars_list:
            return {
                "error": f"No daily bar data available for {symbol} from {start_date} to {end_date}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
        
        # Validate bars are list of dictionaries
        if not isinstance(bars_list, list):
            return {
                "error": f"Invalid bars format for {symbol}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
        
        # Validate first bar has required fields
        if bars_list and isinstance(bars_list[0], dict):
            required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing_fields = [f for f in required_fields if f not in bars_list[0]]
            if missing_fields:
                return {
                    "error": f"Missing required fields in bar data: {missing_fields}",
                    "symbol": symbol,
                    "start_date": start_date,
                    "end_date": end_date
                }
        
        # bars_list is already a list of dictionaries from AlpacaDataFeed
        # Add a 'date' field for convenience
        try:
            for bar in bars_list:
                if 'timestamp' in bar:
                    bar['date'] = bar['timestamp'][:10]  # Extract YYYY-MM-DD from ISO format
        except Exception as e:
            # If date extraction fails, continue without it
            pass
            
        return {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(bars_list),
            "bars": bars_list,
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
        
        # bar is already a dictionary from AlpacaDataFeed
        # Validate it has required fields
        if not isinstance(bar, dict):
            return {
                "error": f"Invalid bar data format for {symbol} on {date}",
                "symbol": symbol,
                "date": date
            }
        
        required_fields = ['open', 'high', 'low', 'close', 'volume']
        missing_fields = [f for f in required_fields if f not in bar]
        if missing_fields:
            return {
                "error": f"Missing required fields in bar data: {missing_fields}",
                "symbol": symbol,
                "date": date
            }
            
        return {
            "symbol": symbol,
            "date": date,
            "ohlcv": {
                "open": float(bar['open']),
                "high": float(bar['high']),
                "low": float(bar['low']),
                "close": float(bar['close']),
                "volume": int(bar['volume']),
            },
            "additional_data": {
                "trade_count": bar.get('trade_count'),
                "vwap": float(bar['vwap']) if bar.get('vwap') else None,
                "timestamp": bar.get('timestamp'),
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
        
        # price is a float from AlpacaDataFeed
        if not isinstance(price, (int, float)):
            return {
                "error": f"Invalid price format for {symbol} on {date}",
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
# MCP Tools - Technical Analysis
# ============================================================================

@mcp.tool()
def get_technical_indicators(
    symbol: str,
    start_date: str,
    end_date: str,
    indicators: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Calculate technical indicators for a stock symbol.
    
    Returns comprehensive technical analysis indicators calculated from historical data.
    Perfect for swing trading and day trading decision-making.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        indicators: Optional list of specific indicators to calculate.
                   If None, calculates all available indicators.
                   Available: sma, ema, rsi, macd, bbands, atr, stoch, adx, obv, vwap, cci
        
    Returns:
        Dictionary containing:
        - symbol: Stock symbol
        - date_range: Start and end dates
        - latest_values: Most recent indicator values
        - all_indicators: Full time series of all indicators
        - error: Error message if request failed
    """
    try:
        _validate_date(start_date)
        _validate_date(end_date)
        
        # Get historical bars
        feed = _get_data_feed()
        bars = feed.get_daily_bars(symbol, start_date, end_date)
        
        if not bars:
            return {
                "error": f"No bar data available for {symbol} from {start_date} to {end_date}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
        
        # Extract OHLCV arrays
        high = np.array([float(bar.high) for bar in bars], dtype=np.float64)
        low = np.array([float(bar.low) for bar in bars], dtype=np.float64)
        close = np.array([float(bar.close) for bar in bars], dtype=np.float64)
        volume = np.array([float(bar.volume) for bar in bars], dtype=np.float64)
        
        # Calculate technical indicators
        ta = get_ta_engine()
        analysis = ta.get_comprehensive_analysis(high, low, close, volume)
        
        if not analysis['success']:
            return {
                "error": f"Failed to calculate indicators: {analysis.get('error', 'Unknown error')}",
                "symbol": symbol
            }
        
        return {
            "symbol": symbol,
            "date_range": {
                "start": start_date,
                "end": end_date
            },
            "bar_count": len(bars),
            "latest_values": analysis['latest'],
            "timestamp": analysis['timestamp']
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
            "error": f"Failed to calculate indicators: {str(e)}",
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        }


@mcp.tool()
def get_trading_signals(
    symbol: str,
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """Get trading signals based on technical analysis.
    
    Analyzes technical indicators and generates BUY/SELL/NEUTRAL signals
    with confidence levels. Perfect for automated trading decisions.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Dictionary containing:
        - symbol: Stock symbol
        - overall_signal: BUY, SELL, or NEUTRAL
        - signal_strength: Number indicating confidence (1-5+)
        - detailed_signals: List of individual indicator signals
        - current_price: Latest closing price
        - error: Error message if request failed
    """
    try:
        _validate_date(start_date)
        _validate_date(end_date)
        
        # Get historical bars
        feed = _get_data_feed()
        # get_daily_bars returns dict[symbol -> list[bar_dicts]]
        bars_dict = feed.get_daily_bars([symbol], start_date, end_date)
        
        # Validate response
        if not isinstance(bars_dict, dict):
            return {
                "error": f"Invalid response format from data feed for {symbol}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
        
        bars_list = bars_dict.get(symbol, [])
        
        if not bars_list:
            return {
                "error": f"No bar data available for {symbol} from {start_date} to {end_date}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
        
        # Validate we have enough data for technical indicators (typically need 50+ bars)
        if len(bars_list) < 20:
            return {
                "error": f"Insufficient data for technical analysis: {len(bars_list)} bars (need at least 20)",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "bar_count": len(bars_list)
            }
        
        # Validate bars are dictionaries with required fields
        if not isinstance(bars_list, list) or not all(isinstance(b, dict) for b in bars_list):
            return {
                "error": f"Invalid bars format for {symbol}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
        
        # Extract OHLCV arrays from list of dictionaries with validation
        try:
            high = np.array([float(bar['high']) for bar in bars_list], dtype=np.float64)
            low = np.array([float(bar['low']) for bar in bars_list], dtype=np.float64)
            close = np.array([float(bar['close']) for bar in bars_list], dtype=np.float64)
            volume = np.array([float(bar['volume']) for bar in bars_list], dtype=np.float64)
        except KeyError as e:
            return {
                "error": f"Missing required field in bar data: {str(e)}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
        except (ValueError, TypeError) as e:
            return {
                "error": f"Invalid numeric data in bars: {str(e)}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
        
        # Validate arrays have data and are not all zeros/NaN
        if len(close) == 0 or np.all(np.isnan(close)) or np.all(close == 0):
            return {
                "error": f"Invalid price data for {symbol} (all zeros or NaN)",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
        
        # Get trading signals
        ta = get_ta_engine()
        signals = ta.get_trading_signals(high, low, close, volume)
        
        # Validate signals response
        if not isinstance(signals, dict):
            return {
                "error": f"Invalid signals format from TA engine",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
        
        # Add current price
        signals['symbol'] = symbol
        signals['current_price'] = float(close[-1])
        signals['date_range'] = {
            "start": start_date,
            "end": end_date
        }
        signals['bar_count'] = len(bars_list)
        
        return signals
        
        return signals
        
    except ValueError as e:
        return {
            "error": str(e),
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        }
    except Exception as e:
        return {
            "error": f"Failed to generate trading signals: {str(e)}",
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        }


@mcp.tool()
def get_bar_with_indicators(symbol: str, date: str, lookback_days: int = 50) -> Dict[str, Any]:
    """Get OHLCV data for a specific date with technical indicators.
    
    Enhanced version of get_bar_for_date that includes technical analysis.
    Uses lookback period to calculate indicators with sufficient data.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        date: Date in YYYY-MM-DD format
        lookback_days: Number of days to look back for indicator calculation (default: 50)
        
    Returns:
        Dictionary containing:
        - symbol: Stock symbol
        - date: Requested date
        - ohlcv: OHLCV data for the date
        - indicators: Technical indicators for the date
        - trading_signal: Overall trading signal (BUY/SELL/NEUTRAL)
        - error: Error message if data not found
    """
    try:
        from datetime import datetime, timedelta
        
        _validate_date(date)
        
        # Calculate start date with lookback period
        end_date_obj = datetime.strptime(date, "%Y-%m-%d")
        start_date_obj = end_date_obj - timedelta(days=lookback_days)
        start_date = start_date_obj.strftime("%Y-%m-%d")
        
        # Get historical bars for indicator calculation
        feed = _get_data_feed()
        bars = feed.get_daily_bars(symbol, start_date, date)
        
        if not bars:
            return {
                "error": f"No bar data available for {symbol} around {date}",
                "symbol": symbol,
                "date": date
            }
        
        # Get the bar for the requested date
        target_bar = None
        for bar in bars:
            if bar.timestamp.strftime("%Y-%m-%d") == date:
                target_bar = bar
                break
        
        if target_bar is None:
            return {
                "error": f"No bar data for {symbol} on {date}. Market may have been closed.",
                "symbol": symbol,
                "date": date
            }
        
        # Extract OHLCV arrays for indicators
        high = np.array([float(bar.high) for bar in bars], dtype=np.float64)
        low = np.array([float(bar.low) for bar in bars], dtype=np.float64)
        close = np.array([float(bar.close) for bar in bars], dtype=np.float64)
        volume = np.array([float(bar.volume) for bar in bars], dtype=np.float64)
        
        # Calculate indicators
        ta = get_ta_engine()
        analysis = ta.get_comprehensive_analysis(high, low, close, volume)
        signals = ta.get_trading_signals(high, low, close, volume)
        
        return {
            "symbol": symbol,
            "date": date,
            "ohlcv": {
                "open": float(target_bar.open),
                "high": float(target_bar.high),
                "low": float(target_bar.low),
                "close": float(target_bar.close),
                "volume": target_bar.volume,
            },
            "additional_data": {
                "trade_count": target_bar.trade_count,
                "vwap": float(target_bar.vwap) if target_bar.vwap else None,
            },
            "indicators": analysis['latest'] if analysis['success'] else {},
            "trading_signal": {
                "overall": signals.get('overall', 'NEUTRAL'),
                "strength": signals.get('strength', 0),
                "signals": signals.get('signals', [])
            },
            "lookback_days_used": len(bars)
        }
        
    except ValueError as e:
        return {
            "error": str(e),
            "symbol": symbol,
            "date": date
        }
    except Exception as e:
        return {
            "error": f"Failed to get bar with indicators: {str(e)}",
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
    print("  Real-time Data:")
    print("    - get_latest_quote: Get current bid/ask prices")
    print("    - get_latest_quotes: Get quotes for multiple symbols")
    print("    - get_latest_trade: Get last trade information")
    print("    - get_latest_price: Get current market price")
    print()
    print("  Historical Data:")
    print("    - get_stock_bars: Get historical OHLCV bars")
    print("    - get_daily_bars: Get daily bars for date range")
    print("    - get_bar_for_date: Get OHLCV for specific date")
    print("    - get_opening_price: Get opening price for specific date")
    print()
    print("  Technical Analysis (TA-Lib powered):")
    print("    - get_technical_indicators: Calculate all TA indicators")
    print("    - get_trading_signals: Get BUY/SELL/NEUTRAL signals")
    print("    - get_bar_with_indicators: Get OHLCV + indicators for a date")
    print()
    print("  Indicators: SMA, EMA, RSI, MACD, Bollinger Bands, ATR,")
    print("              Stochastic, ADX, OBV, VWAP, CCI")
    
    mcp.run(transport="http", port=port)
