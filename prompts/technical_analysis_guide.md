# Technical Analysis Trading Guidelines

## Overview
You now have access to comprehensive technical analysis tools powered by TA-Lib. Use these tools to make informed trading decisions based on multiple technical indicators.

## Available MCP Tools

### 1. get_trading_signals
Get BUY/SELL/NEUTRAL recommendations with confidence levels.

**Usage:**
```json
{
  "symbol": "AAPL",
  "start_date": "2025-10-01",
  "end_date": "2025-10-31"
}
```

**Returns:**
- `overall`: BUY, SELL, or NEUTRAL
- `strength`: Signal strength (1-5+, higher = stronger)
- `signals`: List of individual indicator signals
- `current_price`: Latest closing price

### 2. get_technical_indicators
Get detailed values for all technical indicators.

**Usage:**
```json
{
  "symbol": "TSLA",
  "start_date": "2025-10-01",
  "end_date": "2025-10-31"
}
```

**Returns:**
- `latest_values`: Most recent indicator values
- All indicators: RSI, MACD, SMA, EMA, Bollinger Bands, ATR, Stochastic, ADX, OBV, VWAP, CCI

### 3. get_bar_with_indicators
Get OHLCV data for a specific date with technical analysis.

**Usage:**
```json
{
  "symbol": "NVDA",
  "date": "2025-10-31",
  "lookback_days": 30
}
```

**Returns:**
- `ohlcv`: Open, High, Low, Close, Volume
- `indicators`: All technical indicators
- `trading_signal`: Overall BUY/SELL/NEUTRAL recommendation

## Technical Indicators Explained

### Trend Indicators
- **SMA (Simple Moving Average)**: Price average over N periods
  - Price > SMA: Uptrend
  - Price < SMA: Downtrend

- **EMA (Exponential Moving Average)**: Weighted average favoring recent prices
  - More responsive than SMA
  - Common periods: 12, 26

- **MACD (Moving Average Convergence Divergence)**
  - MACD line > Signal line: Bullish
  - MACD line < Signal line: Bearish
  - Crossovers indicate trend changes

### Momentum Indicators
- **RSI (Relative Strength Index)**: 0-100 scale
  - RSI < 30: Oversold (potential BUY)
  - RSI > 70: Overbought (potential SELL)
  - RSI 40-60: Neutral zone

- **Stochastic Oscillator**: 0-100 scale
  - %K < 20: Oversold
  - %K > 80: Overbought

- **CCI (Commodity Channel Index)**
  - CCI > 100: Overbought
  - CCI < -100: Oversold

### Volatility Indicators
- **Bollinger Bands**: Price channel with 2 std deviations
  - Price at upper band: Potential SELL
  - Price at lower band: Potential BUY
  - Bands widening: Increasing volatility
  - Bands narrowing: Decreasing volatility

- **ATR (Average True Range)**: Volatility measure
  - Higher ATR: More volatile (wider stops needed)
  - Lower ATR: Less volatile (tighter stops possible)

### Volume Indicators
- **OBV (On Balance Volume)**: Cumulative volume
  - Rising OBV + Rising price: Bullish confirmation
  - Falling OBV + Rising price: Warning (divergence)

- **VWAP (Volume Weighted Average Price)**
  - Price > VWAP: Bullish
  - Price < VWAP: Bearish

### Trend Strength
- **ADX (Average Directional Index)**: 0-100 scale
  - ADX > 25: Strong trend
  - ADX < 20: Weak/No trend
  - Does not indicate direction, only strength

## Trading Decision Framework

### For BUY Decisions:
1. **Check Overall Signal**: Must be BUY with strength >= 2
2. **Verify Multiple Indicators**:
   - RSI < 40 (preferably < 30)
   - MACD > Signal line (bullish crossover)
   - Price near lower Bollinger Band
   - Price > VWAP (institutional support)
3. **Confirm Trend**: ADX > 20 (has momentum)
4. **Risk Assessment**: Check ATR for volatility

**Example BUY Logic:**
```
IF overall_signal == "BUY" 
AND signal_strength >= 2
AND (rsi < 40 OR price_at_lower_bb)
AND price > vwap
THEN consider_buy()
```

### For SELL Decisions:
1. **Check Overall Signal**: Must be SELL with strength >= 2
2. **Verify Multiple Indicators**:
   - RSI > 60 (preferably > 70)
   - MACD < Signal line (bearish crossover)
   - Price near upper Bollinger Band
   - Stochastic > 80
3. **Protect Profits**: Use ATR for stop-loss placement

**Example SELL Logic:**
```
IF overall_signal == "SELL"
AND signal_strength >= 2
AND (rsi > 70 OR price_at_upper_bb)
THEN consider_sell()
```

### For HOLD/NEUTRAL:
- Insufficient signal strength (< 2)
- Conflicting indicators
- Market in consolidation (low ADX)
- Wait for clearer signals

## Integration with Portfolio Management

### Position Entry
```python
# Before buying
signals = get_trading_signals(symbol, start_date, end_date)

if signals['overall'] == 'BUY' and signals['strength'] >= 2:
    # Calculate position size based on ATR
    atr = get_technical_indicators(...)['latest_values']['atr_14']
    position_size = calculate_size_from_volatility(atr)
    
    # Place order
    buy_stock(symbol, position_size)
```

### Position Exit
```python
# Monitor existing positions
for position in get_positions():
    signals = get_trading_signals(position.symbol, ...)
    
    if signals['overall'] == 'SELL' and signals['strength'] >= 2:
        sell_stock(position.symbol, position.qty)
```

### Stop-Loss Placement
```python
# Use ATR for dynamic stops
atr = indicators['atr_14']
entry_price = 100.00

# 2x ATR stop-loss
stop_loss = entry_price - (2 * atr)
```

## Best Practices

### 1. Multiple Timeframes
- Look at both short-term (daily) and longer-term trends
- Shorter lookback (20-30 days) for day trading
- Longer lookback (50+ days) for swing trading

### 2. Confirm with Volume
- Always check OBV and volume trends
- Price moves with volume are more reliable

### 3. Avoid False Signals
- Require minimum signal strength of 2
- Look for confluence (multiple indicators agreeing)
- Be cautious in neutral markets (low ADX)

### 4. Risk Management
- Use ATR for position sizing
- Set stop-losses at 1.5-2x ATR
- Never risk more than 1-2% per trade

### 5. Market Context
- Technical analysis works best in trending markets
- Be cautious during major news events
- Consider overall market conditions (SPY, QQQ trends)

## Example Trading Workflow

```markdown
1. Screen for candidates:
   - Use get_trading_signals for watchlist
   - Filter for BUY signals with strength >= 2

2. Verify each candidate:
   - Check RSI, MACD, Bollinger Bands
   - Confirm with volume (OBV, VWAP)
   - Check ATR for volatility

3. Make decision:
   - Require 2+ confirming indicators
   - Calculate position size from ATR
   - Set stop-loss at entry - (2 * ATR)

4. Monitor positions:
   - Daily check of get_trading_signals
   - Exit on SELL signal (strength >= 2)
   - Trail stop-loss as price moves favorably

5. Review and learn:
   - Track which indicators work best
   - Adjust signal strength thresholds
   - Refine entry/exit rules
```

## Signal Strength Guide

- **Strength 1**: Weak signal, one indicator
  - Action: MONITOR, don't trade yet

- **Strength 2**: Medium signal, two indicators
  - Action: CONSIDER entry with tight stops

- **Strength 3+**: Strong signal, multiple indicators
  - Action: HIGH CONFIDENCE entry

## Common Patterns to Watch

### Bullish Patterns
- RSI < 30 + MACD bullish crossover = Strong BUY
- Price bouncing off lower Bollinger Band + OBV rising = BUY
- ADX > 25 + MACD > Signal + RSI < 50 = Trend continuation BUY

### Bearish Patterns
- RSI > 70 + MACD bearish crossover = Strong SELL
- Price at upper Bollinger Band + Stochastic > 80 = SELL
- OBV falling while price rising = Divergence, potential top

### Neutral/Caution
- ADX < 20 = No clear trend, avoid
- RSI 40-60 + MACD near Signal = Consolidation, wait
- Conflicting signals (BUY and SELL) = Stay out

## Remember

⚠️ **Technical analysis is probabilistic, not deterministic**
- No indicator is 100% accurate
- Always use stop-losses
- Combine with fundamental analysis when possible
- Past performance doesn't guarantee future results

✅ **Use technical analysis to**:
- Improve entry and exit timing
- Confirm or reject trade ideas
- Set appropriate risk levels
- Identify trend direction and strength

🚫 **Don't**:
- Trade based on single indicator
- Ignore risk management
- Fight strong trends
- Over-trade in neutral markets
