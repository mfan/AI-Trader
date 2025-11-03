# Technical Analysis Integration - Deep Analysis & Implementation Plan

## Executive Summary

Current State: The Alpaca Data Feed MCP provides **raw OHLCV data** but NO technical indicators.
Goal: Add comprehensive technical analysis capabilities (MACD, RSI, Volume-weighted indicators, etc.)

## Current Alpaca Data Feed Capabilities

### ✅ What We Have (Raw Data)

**Real-time Data:**
- `get_latest_quote()` - Bid/ask prices, sizes
- `get_latest_trade()` - Last trade price, size, exchange
- `get_latest_price()` - Current market price

**Historical Data (OHLCV):**
- `get_stock_bars()` - Historical bars with timeframes: 1Min, 5Min, 15Min, 30Min, 1Hour, 1Day
- `get_daily_bars()` - Daily OHLCV data for date range
- `get_bar_for_date()` - Single day OHLCV data

**Bar Data Structure:**
```python
{
    "timestamp": "2025-11-03T09:30:00",
    "open": 175.50,
    "high": 176.80,
    "low": 175.20,
    "close": 176.45,
    "volume": 12500000,
    "vwap": 176.15,        # ✅ Volume Weighted Average Price (already included!)
    "trade_count": 145000   # ✅ Number of trades (already included!)
}
```

### ❌ What We DON'T Have (Technical Indicators)

**Trend Indicators:**
- MACD (Moving Average Convergence Divergence)
- EMA (Exponential Moving Average)
- SMA (Simple Moving Average)
- ADX (Average Directional Index)
- Parabolic SAR

**Momentum Indicators:**
- RSI (Relative Strength Index)
- Stochastic Oscillator
- Williams %R
- CCI (Commodity Channel Index)
- ROC (Rate of Change)

**Volume Indicators:**
- OBV (On-Balance Volume)
- Volume-weighted RSI
- Accumulation/Distribution Line
- Chaikin Money Flow
- Money Flow Index (MFI)

**Volatility Indicators:**
- Bollinger Bands
- ATR (Average True Range)
- Keltner Channels
- Standard Deviation

**Support/Resistance:**
- Pivot Points
- Fibonacci Retracements
- Support/Resistance Levels

## Architecture Decision: Where to Calculate Indicators?

### Option 1: ❌ Calculate in MCP Service (Server-Side)
**Pros:**
- Centralized calculations
- Consistent results across all clients
- Can cache results

**Cons:**
- Requires installing heavy dependencies (pandas, ta-lib) in MCP service
- Increases MCP service complexity
- Slower response times for simple data requests
- More memory usage on server

### Option 2: ✅ Calculate in AI Agent (Client-Side) - **RECOMMENDED**
**Pros:**
- MCP service stays lightweight and fast
- AI agent gets raw data and computes what it needs
- More flexible - different agents can use different indicators
- Easier to add/modify indicators without restarting MCP
- Better separation of concerns

**Cons:**
- Each AI agent needs to compute indicators
- Slightly more data transfer (but we already get full OHLCV)

### Option 3: 🔶 Hybrid Approach
**Pros:**
- MCP provides both raw data AND common indicators
- AI agent can choose what to use
- Best of both worlds

**Cons:**
- Most complex to implement
- Duplicated code

## Recommended Implementation: Client-Side with Helper Module

### Phase 1: Add Technical Analysis Library

Install `pandas-ta` (easiest) or `ta` (lightweight) or `TA-Lib` (most comprehensive):

```bash
# Option A: pandas-ta (easiest, most comprehensive)
pip install pandas pandas-ta

# Option B: ta (lightweight, no pandas required)
pip install ta

# Option C: TA-Lib (most powerful, harder to install)
# Requires C library: sudo apt-get install ta-lib
pip install TA-Lib
```

**Recommendation: Start with `ta` library**
- Pure Python (easy install)
- No heavy pandas dependency
- Covers all common indicators
- Well-maintained

### Phase 2: Create Technical Analysis Helper Module

Create `tools/technical_analysis.py`:

```python
"""
Technical Analysis Helper Module

Provides technical indicators calculated from OHLCV data.
Uses the 'ta' library for pure Python implementation.

Usage:
    from tools.technical_analysis import TechnicalAnalysis
    
    # Get bars from Alpaca
    bars = get_daily_bars("AAPL", "2025-01-01", "2025-11-03")
    
    # Calculate indicators
    ta = TechnicalAnalysis(bars)
    
    # Get individual indicators
    macd = ta.get_macd()
    rsi = ta.get_rsi(period=14)
    bollinger = ta.get_bollinger_bands()
    
    # Get all indicators at once
    all_indicators = ta.get_all_indicators()
```

### Phase 3: Add MCP Tools for Technical Analysis (Optional)

If we want server-side calculation, add to `tool_alpaca_data.py`:

```python
@mcp.tool()
def get_technical_indicators(
    symbol: str,
    start_date: str,
    end_date: str,
    indicators: List[str]
) -> Dict[str, Any]:
    """
    Get technical indicators for a symbol
    
    Args:
        symbol: Stock symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        indicators: List of indicators to calculate
                   ['macd', 'rsi', 'bbands', 'sma_20', 'ema_50', ...]
    
    Returns:
        Dictionary with indicator values for each date
    """
```

## Detailed Implementation Plan

### Step 1: Install Dependencies

```bash
cd /home/mfan/work/aitrader
pip install ta  # or pandas-ta for more features
```

Add to `requirements.txt`:
```
ta>=0.11.0  # Technical analysis library
```

### Step 2: Create `tools/technical_analysis.py`

```python
"""
Technical Analysis Module

Provides technical indicators for stock market data.
Designed to work with Alpaca OHLCV bar data.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import ta  # Technical Analysis library


class TechnicalAnalysis:
    """
    Calculate technical indicators from OHLCV data
    
    Works with bar data from Alpaca Data Feed.
    """
    
    def __init__(self, bars: List[Dict[str, Any]]):
        """
        Initialize with OHLCV bar data
        
        Args:
            bars: List of bar dictionaries with keys:
                  timestamp, open, high, low, close, volume
        """
        if not bars:
            raise ValueError("No bar data provided")
        
        self.bars = sorted(bars, key=lambda x: x['timestamp'])
        
        # Extract price and volume arrays
        self.close = [float(bar['close']) for bar in self.bars]
        self.open = [float(bar['open']) for bar in self.bars]
        self.high = [float(bar['high']) for bar in self.bars]
        self.low = [float(bar['low']) for bar in self.bars]
        self.volume = [int(bar['volume']) for bar in self.bars]
        self.timestamps = [bar['timestamp'] for bar in self.bars]
    
    # ==================== TREND INDICATORS ====================
    
    def get_sma(self, period: int = 20) -> List[Optional[float]]:
        """Simple Moving Average"""
        return ta.trend.sma_indicator(
            close=pd.Series(self.close),
            window=period
        ).tolist()
    
    def get_ema(self, period: int = 20) -> List[Optional[float]]:
        """Exponential Moving Average"""
        return ta.trend.ema_indicator(
            close=pd.Series(self.close),
            window=period
        ).tolist()
    
    def get_macd(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, List[Optional[float]]]:
        """
        MACD (Moving Average Convergence Divergence)
        
        Returns:
            Dictionary with 'macd', 'signal', 'histogram'
        """
        close_series = pd.Series(self.close)
        
        macd_line = ta.trend.macd(
            close_series,
            window_slow=slow_period,
            window_fast=fast_period
        ).tolist()
        
        signal_line = ta.trend.macd_signal(
            close_series,
            window_slow=slow_period,
            window_fast=fast_period,
            window_sign=signal_period
        ).tolist()
        
        histogram = ta.trend.macd_diff(
            close_series,
            window_slow=slow_period,
            window_fast=fast_period,
            window_sign=signal_period
        ).tolist()
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    # ==================== MOMENTUM INDICATORS ====================
    
    def get_rsi(self, period: int = 14) -> List[Optional[float]]:
        """Relative Strength Index"""
        return ta.momentum.rsi(
            close=pd.Series(self.close),
            window=period
        ).tolist()
    
    def get_stochastic(
        self,
        k_period: int = 14,
        d_period: int = 3
    ) -> Dict[str, List[Optional[float]]]:
        """
        Stochastic Oscillator
        
        Returns:
            Dictionary with '%K' and '%D' lines
        """
        high_series = pd.Series(self.high)
        low_series = pd.Series(self.low)
        close_series = pd.Series(self.close)
        
        k_line = ta.momentum.stoch(
            high=high_series,
            low=low_series,
            close=close_series,
            window=k_period,
            smooth_window=d_period
        ).tolist()
        
        d_line = ta.momentum.stoch_signal(
            high=high_series,
            low=low_series,
            close=close_series,
            window=k_period,
            smooth_window=d_period
        ).tolist()
        
        return {
            '%K': k_line,
            '%D': d_line
        }
    
    # ==================== VOLUME INDICATORS ====================
    
    def get_obv(self) -> List[float]:
        """On-Balance Volume"""
        close_series = pd.Series(self.close)
        volume_series = pd.Series(self.volume)
        
        return ta.volume.on_balance_volume(
            close=close_series,
            volume=volume_series
        ).tolist()
    
    def get_mfi(self, period: int = 14) -> List[Optional[float]]:
        """Money Flow Index (Volume-weighted RSI)"""
        high_series = pd.Series(self.high)
        low_series = pd.Series(self.low)
        close_series = pd.Series(self.close)
        volume_series = pd.Series(self.volume)
        
        return ta.volume.money_flow_index(
            high=high_series,
            low=low_series,
            close=close_series,
            volume=volume_series,
            window=period
        ).tolist()
    
    def get_volume_weighted_rsi(self, period: int = 14) -> List[Optional[float]]:
        """
        Volume-Weighted RSI
        
        Custom indicator: RSI calculated on volume-weighted price changes
        """
        # Use MFI as it's essentially volume-weighted RSI
        return self.get_mfi(period)
    
    # ==================== VOLATILITY INDICATORS ====================
    
    def get_bollinger_bands(
        self,
        period: int = 20,
        std_dev: int = 2
    ) -> Dict[str, List[Optional[float]]]:
        """
        Bollinger Bands
        
        Returns:
            Dictionary with 'upper', 'middle', 'lower' bands
        """
        close_series = pd.Series(self.close)
        
        upper = ta.volatility.bollinger_hband(
            close=close_series,
            window=period,
            window_dev=std_dev
        ).tolist()
        
        middle = ta.volatility.bollinger_mavg(
            close=close_series,
            window=period
        ).tolist()
        
        lower = ta.volatility.bollinger_lband(
            close=close_series,
            window=period,
            window_dev=std_dev
        ).tolist()
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }
    
    def get_atr(self, period: int = 14) -> List[Optional[float]]:
        """Average True Range"""
        high_series = pd.Series(self.high)
        low_series = pd.Series(self.low)
        close_series = pd.Series(self.close)
        
        return ta.volatility.average_true_range(
            high=high_series,
            low=low_series,
            close=close_series,
            window=period
        ).tolist()
    
    # ==================== COMPOSITE FUNCTIONS ====================
    
    def get_all_indicators(self) -> Dict[str, Any]:
        """
        Get all major technical indicators at once
        
        Returns:
            Dictionary with all calculated indicators
        """
        return {
            'trend': {
                'sma_20': self.get_sma(20),
                'sma_50': self.get_sma(50),
                'ema_12': self.get_ema(12),
                'ema_26': self.get_ema(26),
                'macd': self.get_macd(),
            },
            'momentum': {
                'rsi_14': self.get_rsi(14),
                'stochastic': self.get_stochastic(),
            },
            'volume': {
                'obv': self.get_obv(),
                'mfi_14': self.get_mfi(14),
                'volume_weighted_rsi': self.get_volume_weighted_rsi(14),
            },
            'volatility': {
                'bollinger_bands': self.get_bollinger_bands(),
                'atr_14': self.get_atr(14),
            },
            'timestamps': self.timestamps,
        }
    
    def get_latest_values(self) -> Dict[str, Any]:
        """
        Get only the latest (most recent) value for each indicator
        
        Useful for real-time decision making.
        """
        all_indicators = self.get_all_indicators()
        
        def get_last(values):
            if isinstance(values, list):
                return values[-1] if values else None
            elif isinstance(values, dict):
                return {k: get_last(v) for k, v in values.items()}
            else:
                return values
        
        return {k: get_last(v) for k, v in all_indicators.items()}
```

### Step 3: Add MCP Tool for Technical Analysis

Add to `agent_tools/tool_alpaca_data.py`:

```python
@mcp.tool()
def get_technical_analysis(
    symbol: str,
    start_date: str,
    end_date: str,
    indicators: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get technical analysis indicators for a stock symbol.
    
    Calculates technical indicators from historical OHLCV data.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        indicators: List of indicators to calculate. If None, returns all.
                   Options: 'macd', 'rsi', 'bbands', 'sma_20', 'sma_50',
                           'ema_12', 'ema_26', 'stochastic', 'obv', 'mfi',
                           'volume_weighted_rsi', 'atr'
    
    Returns:
        Dictionary containing:
        - symbol: Stock symbol
        - start_date: Start date
        - end_date: End date
        - indicators: Dictionary of calculated indicators
        - latest_values: Most recent value for each indicator
        - error: Error message if calculation failed
    
    Example:
        >>> result = get_technical_analysis("AAPL", "2025-10-01", "2025-11-03")
        >>> print(result['latest_values']['momentum']['rsi_14'])
        >>> 65.4
        
        >>> # Get only specific indicators
        >>> result = get_technical_analysis(
        ...     "AAPL",
        ...     "2025-10-01",
        ...     "2025-11-03",
        ...     indicators=['macd', 'rsi', 'volume_weighted_rsi']
        ... )
    """
    try:
        from tools.technical_analysis import TechnicalAnalysis
        
        _validate_date(start_date)
        _validate_date(end_date)
        
        # Get historical bars
        feed = _get_data_feed()
        bars_result = feed.get_daily_bars([symbol], start_date, end_date)
        
        if symbol not in bars_result or not bars_result[symbol]:
            return {
                "error": f"No bar data available for {symbol}",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }
        
        bars = bars_result[symbol]
        
        # Calculate technical indicators
        ta = TechnicalAnalysis(bars)
        
        if indicators is None:
            # Get all indicators
            all_indicators = ta.get_all_indicators()
            latest_values = ta.get_latest_values()
        else:
            # Get specific indicators
            # TODO: Implement selective indicator calculation
            all_indicators = ta.get_all_indicators()
            latest_values = ta.get_latest_values()
        
        return {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "bar_count": len(bars),
            "indicators": all_indicators,
            "latest_values": latest_values,
        }
        
    except ImportError:
        return {
            "error": "Technical analysis library not installed. Run: pip install ta",
            "symbol": symbol
        }
    except Exception as e:
        return {
            "error": f"Failed to calculate technical indicators: {str(e)}",
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        }
```

### Step 4: Update AI Agent Prompts

Update `prompts/agent_prompt.py` to include technical analysis:

```python
TECHNICAL_ANALYSIS_GUIDANCE = """
When analyzing stocks, you can use technical indicators to inform your decisions:

TREND INDICATORS:
- SMA (Simple Moving Average): Smooth price trends, common periods: 20, 50, 200
- EMA (Exponential Moving Average): More responsive to recent prices
- MACD: Trend direction and momentum. Buy when MACD crosses above signal line.

MOMENTUM INDICATORS:
- RSI (Relative Strength Index): 
  * RSI > 70 = Overbought (potential sell signal)
  * RSI < 30 = Oversold (potential buy signal)
  * RSI 40-60 = Neutral
  
- Stochastic Oscillator: Similar to RSI but compares close to high-low range

VOLUME INDICATORS:
- OBV (On-Balance Volume): Accumulation/distribution based on volume
- MFI (Money Flow Index): Volume-weighted RSI
  * MFI > 80 = Overbought
  * MFI < 20 = Oversold
  
- Volume-Weighted RSI: Combines price momentum with volume

VOLATILITY INDICATORS:
- Bollinger Bands: 
  * Price near upper band = potential overbought
  * Price near lower band = potential oversold
  * Bands widening = increased volatility
  
- ATR (Average True Range): Measure of volatility, useful for stop-loss placement

USAGE:
1. Use get_technical_analysis() to calculate indicators for a date range
2. Focus on latest_values for current decision making
3. Combine multiple indicators for confirmation
4. Don't rely on single indicator - use confluence

EXAMPLE DECISION LOGIC:
- Bullish: RSI < 40, MACD crossover, price above SMA20
- Bearish: RSI > 70, MACD negative crossover, price below SMA20
- High confidence: Multiple indicators agree
- Low confidence: Mixed signals, stay neutral or reduce position size
"""
```

## Implementation Checklist

### Phase 1: Basic Setup
- [ ] Install `ta` library: `pip install ta`
- [ ] Add to `requirements.txt`
- [ ] Create `tools/technical_analysis.py` with basic indicators
- [ ] Test indicator calculations manually

### Phase 2: MCP Integration
- [ ] Add `get_technical_analysis()` tool to `tool_alpaca_data.py`
- [ ] Test MCP tool with sample data
- [ ] Verify JSON serialization works
- [ ] Add error handling for missing data

### Phase 3: AI Agent Integration
- [ ] Update agent prompts with technical analysis guidance
- [ ] Add example usage to agent
- [ ] Test end-to-end: data fetch → indicator calculation → decision
- [ ] Monitor performance (calculation time)

### Phase 4: Optimization
- [ ] Cache calculated indicators (if needed)
- [ ] Add batch processing for multiple symbols
- [ ] Optimize for real-time calculations
- [ ] Add visualization helpers (optional)

## Performance Considerations

### Calculation Time
- **Fast** (< 100ms): RSI, SMA, EMA on 30-day data
- **Medium** (100-500ms): MACD, Bollinger Bands on 100-day data
- **Slow** (> 500ms): Complex indicators on 1+ year data

### Recommendations:
1. **Limit lookback period**: 30-100 days for most indicators
2. **Calculate once per cycle**: Don't recalculate every second
3. **Cache results**: Store calculated indicators for reuse
4. **Batch processing**: Calculate for multiple symbols together

## Alternative: Use Alpaca's Built-in Technical Indicators

⚠️ **Important Discovery**: Check if Alpaca Pro/Premium provides pre-calculated indicators!

Some data providers include technical indicators in their API:
- **VWAP**: Already included in bar data! ✅
- **SMA/EMA**: May be available in premium tier
- **RSI/MACD**: Check Alpaca Pro features

**Action**: Review Alpaca API documentation for built-in indicators before implementing custom calculations.

## Example Usage in AI Agent

```python
# In agent workflow:

# 1. Get historical data
bars = get_daily_bars("AAPL", "2025-10-01", "2025-11-03")

# 2. Calculate technical indicators
ta_result = get_technical_analysis("AAPL", "2025-10-01", "2025-11-03")

# 3. Extract latest values
latest = ta_result['latest_values']
rsi = latest['momentum']['rsi_14']
macd = latest['trend']['macd']
volume_rsi = latest['volume']['volume_weighted_rsi']

# 4. Make decision
if rsi < 35 and macd['histogram'] > 0 and volume_rsi < 30:
    decision = "BUY - Oversold with positive momentum and volume support"
elif rsi > 70 and macd['histogram'] < 0:
    decision = "SELL - Overbought with negative momentum"
else:
    decision = "HOLD - Mixed signals"

# 5. Log reasoning
print(f"RSI: {rsi:.2f}, MACD Histogram: {macd['histogram']:.4f}")
print(f"Volume-weighted RSI: {volume_rsi:.2f}")
print(f"Decision: {decision}")
```

## Conclusion

**Recommended Approach:**
1. **Install `ta` library** - lightweight, pure Python
2. **Create `tools/technical_analysis.py`** - helper module
3. **Add MCP tool** - optional, for server-side calculation
4. **Update AI agent** - use indicators in decision logic

**Key Advantages:**
- ✅ No modification to existing Alpaca data feed
- ✅ Flexible - easy to add new indicators
- ✅ Testable - can verify indicator calculations
- ✅ Reusable - can be used in multiple agents

**Next Steps:**
1. Review this document
2. Decide on client-side vs server-side calculation
3. Install required libraries
4. Implement Phase 1 (basic setup)
5. Test with historical data
6. Integrate with AI trading agent

Would you like me to proceed with implementation?
