# Technical Analysis Integration - Quick Start

## ✅ Integration Complete!

Technical analysis powered by TA-Lib is now fully integrated into the AI trading system.

## 🎯 What's New

### 1. **Technical Indicators Engine** (`tools/technical_indicators.py`)
- 11+ technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, Stochastic, ADX, OBV, VWAP, CCI)
- Automated BUY/SELL/NEUTRAL signal generation
- Confidence scoring for trading decisions

### 2. **Trading Decision Helper** (`tools/ta_helper.py`)
- `should_buy(symbol)` - Get buy recommendation with confidence
- `should_sell(symbol)` - Get sell recommendation with confidence  
- `get_quick_analysis(symbol)` - Fast technical overview

### 3. **MCP Service Integration** (`agent_tools/tool_alpaca_data.py`)
AI agents now have 3 new MCP tools:
- `get_trading_signals(symbol, start_date, end_date)` - BUY/SELL signals
- `get_technical_indicators(symbol, start_date, end_date)` - All indicator values
- `get_bar_with_indicators(symbol, date, lookback_days)` - OHLCV + TA

### 4. **Active Trader Support** (`active_trader.py`)
- Exports `TA_ENABLED=True` flag to agents
- Ready to use TA helpers in trading loops

### 5. **AI Agent Guidance** (`prompts/`)
- `technical_analysis_guide.md` - Complete TA trading guide
- `agent_prompt.py` - Updated with TA tools and usage instructions

## 🚀 Quick Usage

### For Python Scripts
```python
from tools.ta_helper import get_trading_decision_helper

helper = get_trading_decision_helper()

# Check if should buy
decision = helper.should_buy("AAPL", lookback_days=30, min_signal_strength=2)
if decision['should_buy']:
    print(f"BUY AAPL - Confidence: {decision['confidence']}")
    print(f"Reasons: {', '.join(decision['reasons'])}")

# Check if should sell  
decision = helper.should_sell("TSLA", lookback_days=30)
if decision['should_sell']:
    print(f"SELL TSLA - Confidence: {decision['confidence']}")
```

### For AI Agents (via MCP)
```json
// Get trading signals
{
  "tool": "get_trading_signals",
  "symbol": "NVDA",
  "start_date": "2025-10-01",
  "end_date": "2025-10-31"
}

// Returns:
{
  "overall": "BUY",
  "strength": 3,
  "signals": [
    {"indicator": "RSI", "signal": "OVERSOLD", "action": "BUY", "confidence": "HIGH"},
    {"indicator": "MACD", "signal": "BULLISH_CROSSOVER", "action": "BUY"},
    {"indicator": "Bollinger Bands", "signal": "PRICE_AT_LOWER_BAND", "action": "BUY"}
  ],
  "current_price": 245.67
}
```

### Testing with OKLO and CRWV
```bash
# Analyze OKLO and CRWV  
python test_ta_analysis.py
```

Results showed:
- **OKLO**: NEUTRAL (RSI: 55.31, below VWAP)
- **CRWV**: NEUTRAL (RSI: 53.36, below VWAP)
- Both stocks lack strong directional signals → HOLD/WAIT

## 📊 Trading Signal Interpretation

### Signal Strength Guide
- **Strength 1**: Weak (1 indicator) → MONITOR only
- **Strength 2**: Medium (2 indicators) → CONSIDER with tight stops
- **Strength 3+**: Strong (3+ indicators) → HIGH CONFIDENCE

### Common Patterns
**Strong BUY**:
- RSI < 30 + MACD bullish crossover + Price at lower BB
- Strength >= 3

**Strong SELL**:
- RSI > 70 + MACD bearish crossover + Price at upper BB  
- Strength >= 3

**NEUTRAL/HOLD**:
- Conflicting signals
- Strength < 2
- ADX < 20 (weak trend)

## 🧪 Testing

Run comprehensive integration test:
```bash
python test_ta_integration.py
```

Expected output:
```
✅ TA-Lib installed: v0.6.8
✅ Technical indicators module working
✅ TA Helper module working
✅ MCP TA tools defined
✅ active_trader.py has TA support enabled
✅ Agent prompt includes TA tools
```

## 🎓 Learning Resources

1. **Technical Analysis Guide**: `prompts/technical_analysis_guide.md`
   - Complete indicator explanations
   - Trading decision framework
   - Best practices and patterns

2. **Example Analysis**: `test_ta_analysis.py`
   - Real-world analysis of stocks
   - Shows all indicators in action
   - Demonstrates signal generation

3. **TA-Lib Documentation**: https://ta-lib.github.io/ta-lib-python/

## 🔧 Starting the System

### 1. Start MCP Services
```bash
# Start Alpaca Data with TA support (port 8004)
python agent_tools/tool_alpaca_data.py
```

### 2. Run AI Agent Trading
```bash
# Single trading session
python trade.py
```

### 3. Run Active Trader
```bash
# Continuous trading during market hours
python active_trader.py
```

## 📝 AI Agent Instructions

When the AI agent runs, it now has access to:

```
📈 Technical Analysis Tools (TA-Lib):
• get_trading_signals(symbol, start_date, end_date)
  → Get BUY/SELL/NEUTRAL with confidence
  → Use BEFORE buying or selling

• get_technical_indicators(symbol, start_date, end_date)
  → Get RSI, MACD, Bollinger Bands, etc.
  
⚠️ WHEN TO USE:
• BEFORE buying: Require BUY signal strength >= 2
• BEFORE selling: Look for SELL signal strength >= 2
• Overbought (RSI > 70): Consider taking profits
• Oversold (RSI < 30): Look for buying opportunities
```

## 🎯 Example Trading Workflow

1. **Screen Candidates**:
   ```python
   symbols = ["AAPL", "TSLA", "NVDA", "MSFT"]
   for symbol in symbols:
       signals = get_trading_signals(symbol, ...)
       if signals['overall'] == 'BUY' and signals['strength'] >= 2:
           print(f"{symbol}: {signals}")
   ```

2. **Verify Top Pick**:
   ```python
   indicators = get_technical_indicators("AAPL", ...)
   # Check RSI, MACD, Bollinger Bands
   # Confirm with volume (OBV, VWAP)
   ```

3. **Execute Trade**:
   ```python
   # Calculate position size from ATR
   atr = indicators['latest']['atr_14']
   position_size = calculate_size_from_risk(atr)
   
   # Place order
   buy_stock("AAPL", position_size)
   
   # Set stop-loss at entry - (2 * ATR)
   ```

## 💡 Pro Tips

1. **Multiple Timeframes**: Use 30-day lookback for swing trading, 50+ for position trading
2. **Confirm with Volume**: Strong moves should have OBV confirmation
3. **Signal Strength Matters**: Don't trade on Strength 1 signals
4. **Use Stop-Losses**: Always set stops at 1.5-2x ATR
5. **Market Context**: Check SPY/QQQ trends before individual stocks

## 🐛 Troubleshooting

**Issue**: No historical data for symbol
- **Solution**: Some newer IPOs (like OKLO, CRWV) have limited history in IEX feed
- **Workaround**: Use shorter lookback period (20-30 days instead of 50+)

**Issue**: Some indicators return N/A
- **Solution**: Need more data points (e.g., SMA-50 needs 50+ bars)
- **Normal**: MACD needs 26+ days, ADX needs 14+ days

**Issue**: MCP tool not callable
- **Solution**: MCP tools only work when MCP server is running
- **Fix**: Start with `python agent_tools/tool_alpaca_data.py`

## 📚 Files Created/Modified

### New Files
- `tools/technical_indicators.py` - Core TA engine
- `tools/ta_helper.py` - Trading decision helper
- `prompts/technical_analysis_guide.md` - Complete TA guide
- `test_ta_analysis.py` - Example analysis script
- `test_ta_integration.py` - Integration test
- `test_oklo_crwv.py` - Data availability checker

### Modified Files
- `agent_tools/tool_alpaca_data.py` - Added 3 TA MCP tools
- `tools/alpaca_data_feed.py` - Fixed `.data` attribute access
- `active_trader.py` - Added TA_ENABLED flag
- `prompts/agent_prompt.py` - Added TA tools section

## ✨ Summary

✅ **11+ technical indicators** available  
✅ **Automated trading signals** with confidence levels  
✅ **MCP integration** for AI agents  
✅ **Helper functions** for easy use  
✅ **Complete documentation** and examples  
✅ **Tested and working** with real market data  

**The system is ready for technical analysis-powered trading!** 🚀📈
