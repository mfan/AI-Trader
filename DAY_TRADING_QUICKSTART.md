# Day Trading Quick Start Guide 🚀

## System Overview
**Pure Technical Analysis Day Trading** - No news, no overnight positions, fast intraday trades.

---

## 1️⃣ Start Trading (3 Simple Steps)

### Step 1: Activate Environment & Start Services
```bash
cd /home/mfan/work/aitrader
source /home/mfan/work/bin/activate
python agent_tools/start_mcp_services.py
```

**Services Started:**
- ✅ AlpacaData (Port 8004) - Market data + TA signals
- ✅ AlpacaTrade (Port 8005) - Order execution

### Step 2: Get Trading Signal
```python
from tools.ta_helper import get_quick_analysis

# Check if AAPL is a BUY
signal = get_quick_analysis("AAPL", days=30)

print(signal)
# Output:
# {
#   "signal": "BUY",           # BUY/SELL/NEUTRAL
#   "strength": 3,             # 1-5 (need >= 2 to trade)
#   "rsi": 45.2,              # < 30 = oversold, > 70 = overbought
#   "macd_histogram": 0.52,   # Positive = bullish
#   "price_vs_vwap": "above"  # Above VWAP = intraday strength
# }
```

### Step 3: Execute Trade (If Signal is Good)
```python
from agent_tools.tool_alpaca_trade import place_order, get_account
from tools.technical_indicators import get_technical_indicators

# Only trade if BUY + Strength >= 2
if signal["signal"] == "BUY" and signal["strength"] >= 2:
    
    # Get account info
    account = get_account()
    portfolio_value = account["portfolio_value"]
    
    # Calculate position size (max 10% of portfolio)
    current_price = 250.00
    position_size = portfolio_value * 0.10
    shares = int(position_size / current_price)
    
    # Get ATR for stop-loss
    indicators = get_technical_indicators("AAPL", "2025-10-01", "2025-10-31")
    atr = indicators["ATR"]
    
    # Calculate stops
    stop_loss = current_price - (2 * atr)
    take_profit = current_price + (3 * atr)
    
    # Execute order
    place_order("AAPL", shares, "buy", "market", "day")
    
    print(f"✅ Bought {shares} shares of AAPL at ${current_price}")
    print(f"🛡️ Stop-loss: ${stop_loss:.2f}")
    print(f"🎯 Target: ${take_profit:.2f}")
```

---

## 2️⃣ Day Trading Rules (CRITICAL)

### Entry Checklist ✅
- [ ] `get_trading_signals()` shows **BUY**
- [ ] Signal strength >= **2**
- [ ] RSI < 50 (not overbought)
- [ ] MACD bullish (positive histogram)
- [ ] Position size <= 10% of portfolio
- [ ] Stop-loss calculated (entry - 2×ATR)

### Exit Checklist 🚨
**Exit IMMEDIATELY if:**
- [ ] `get_trading_signals()` shows **SELL** with strength >= 2
- [ ] RSI > 70 (overbought)
- [ ] Price hits stop-loss
- [ ] Price hits take-profit target
- [ ] Time is 3:45 PM ET (market close)

### End of Day ⏰
**At 3:45 PM ET - Close EVERYTHING:**
```python
from agent_tools.tool_alpaca_trade import close_all_positions

close_all_positions(cancel_orders=True)
print("✅ All positions closed - flat overnight")
```

---

## 3️⃣ Common Trading Scenarios

### Scenario A: Find Day Trading Opportunities
```python
from tools.ta_helper import get_quick_analysis

# Popular day trading stocks
candidates = ["SPY", "QQQ", "AAPL", "TSLA", "NVDA", "AMD", "MSFT"]

for symbol in candidates:
    signal = get_quick_analysis(symbol, days=25)
    
    if signal["signal"] == "BUY" and signal["strength"] >= 3:
        print(f"\n🎯 STRONG BUY: {symbol}")
        print(f"   Strength: {signal['strength']}/5")
        print(f"   RSI: {signal['rsi']:.1f}")
        print(f"   MACD: {signal['macd_histogram']:.3f}")
```

### Scenario B: Check Current Positions
```python
from agent_tools.tool_alpaca_trade import get_positions
from tools.ta_helper import get_quick_analysis

positions = get_positions()

for pos in positions:
    symbol = pos["symbol"]
    
    # Get current signal
    signal = get_quick_analysis(symbol, days=25)
    
    # Check if we should exit
    if signal["signal"] == "SELL" and signal["strength"] >= 2:
        print(f"🚨 EXIT {symbol}: SELL signal detected!")
        close_position(symbol)
    
    elif signal["rsi"] > 70:
        print(f"⚠️ {symbol} overbought (RSI={signal['rsi']:.1f}) - consider profit taking")
```

### Scenario C: Monitor Position with Stops
```python
from agent_tools.tool_alpaca_trade import get_position, close_position
from tools.technical_indicators import get_technical_indicators

# Check position
pos = get_position("AAPL")
entry_price = pos["avg_entry_price"]
current_price = pos["current_price"]

# Get ATR for stop
indicators = get_technical_indicators("AAPL", "2025-10-01", "2025-10-31")
atr = indicators["ATR"]
stop_loss = entry_price - (2 * atr)

# Check if stop hit
if current_price <= stop_loss:
    print(f"🛑 Stop-loss hit for AAPL at ${current_price:.2f}")
    close_position("AAPL")
    print(f"✅ Position closed - loss limited to {((current_price/entry_price - 1) * 100):.1f}%")
```

---

## 4️⃣ Key Functions Reference

### Market Data
```python
# Get current price
get_latest_price("AAPL")

# Get historical bars (intraday for day trading)
get_stock_bars("AAPL", "2025-10-31", "2025-10-31", "5Min")

# Get real-time snapshot
get_snapshot("AAPL")
```

### Technical Analysis
```python
# Get trading signal (BUY/SELL/NEUTRAL)
get_trading_signals("AAPL", "2025-10-01", "2025-10-31")

# Get all indicators (RSI, MACD, BB, ATR, etc.)
get_technical_indicators("AAPL", "2025-10-01", "2025-10-31")

# Quick analysis (easiest)
get_quick_analysis("AAPL", days=30)
```

### Trading
```python
# Buy stock (market order)
place_order("AAPL", 10, "buy", "market", "day")

# Sell at specific price (limit order)
place_order("AAPL", 10, "sell", "limit", "day", limit_price=255.50)

# Close position
close_position("AAPL")

# Close all positions
close_all_positions()
```

### Account & Positions
```python
# Get account info
get_account()

# Get all positions
get_positions()

# Get specific position
get_position("AAPL")

# Get portfolio summary
get_portfolio_summary()
```

---

## 5️⃣ Signal Interpretation

### Trading Signal Values
| Signal | Strength | Meaning | Action |
|--------|----------|---------|--------|
| BUY | 5 | Very Strong Buy | Enter full position |
| BUY | 3-4 | Strong Buy | Enter position |
| BUY | 2 | Weak Buy | Enter small or wait |
| NEUTRAL | 1-5 | No clear direction | Hold or stay out |
| SELL | 2 | Weak Sell | Consider exit |
| SELL | 3-4 | Strong Sell | Exit position |
| SELL | 5 | Very Strong Sell | Exit immediately |

### RSI Levels
- **< 30**: Oversold → Look for BUY opportunities
- **30-50**: Neutral/Bearish → Wait for confirmation
- **50-70**: Neutral/Bullish → Can hold winners
- **> 70**: Overbought → Take profits / Don't buy

### MACD Signals
- **Positive histogram**: Bullish momentum
- **Negative histogram**: Bearish momentum
- **Crossover (negative → positive)**: BUY signal
- **Crossover (positive → negative)**: SELL signal

### VWAP Position
- **Above VWAP**: Intraday strength → Can buy
- **Below VWAP**: Intraday weakness → Avoid or sell

---

## 6️⃣ Position Sizing Calculator

```python
def calculate_position_size(portfolio_value, current_price, risk_pct=0.10):
    """
    Calculate position size for day trading
    
    Args:
        portfolio_value: Total account value
        current_price: Stock price
        risk_pct: % of portfolio to risk (default 10%)
    
    Returns:
        Number of shares to buy
    """
    max_dollar_amount = portfolio_value * risk_pct
    shares = int(max_dollar_amount / current_price)
    return shares

# Example
portfolio = 10000
price = 250
shares = calculate_position_size(portfolio, price, 0.10)
print(f"Buy {shares} shares (${shares * price:.2f} position)")
# Output: Buy 4 shares ($1000.00 position)
```

---

## 7️⃣ Stop-Loss Calculator

```python
def calculate_stops(entry_price, atr, stop_multiplier=2, target_multiplier=3):
    """
    Calculate stop-loss and take-profit using ATR
    
    Args:
        entry_price: Entry price
        atr: Average True Range value
        stop_multiplier: How many ATRs below entry (default 2)
        target_multiplier: How many ATRs above entry (default 3)
    
    Returns:
        (stop_loss, take_profit)
    """
    stop_loss = entry_price - (stop_multiplier * atr)
    take_profit = entry_price + (target_multiplier * atr)
    return stop_loss, take_profit

# Example
entry = 250.00
atr = 5.00
stop, target = calculate_stops(entry, atr)
print(f"Entry: ${entry:.2f}")
print(f"Stop: ${stop:.2f}")
print(f"Target: ${target:.2f}")
# Output:
# Entry: $250.00
# Stop: $240.00  (2 * $5 = $10 below entry)
# Target: $265.00  (3 * $5 = $15 above entry)
```

---

## 8️⃣ Daily Trading Schedule

### 9:30 AM - Market Open
```python
# 1. Check account
account = get_account()
print(f"Cash: ${account['cash']:.2f}")
print(f"Buying Power: ${account['buying_power']:.2f}")

# 2. Scan for setups
candidates = ["SPY", "QQQ", "AAPL", "TSLA", "NVDA"]
for symbol in candidates:
    signal = get_quick_analysis(symbol, days=25)
    if signal["signal"] == "BUY" and signal["strength"] >= 3:
        print(f"🎯 {symbol}: BUY Strength {signal['strength']}/5")
```

### 10:00 AM - 3:00 PM - Monitor & Trade
```python
# Check positions every 30 minutes
positions = get_positions()
for pos in positions:
    symbol = pos["symbol"]
    pnl_pct = pos["unrealized_plpc"] * 100
    
    # Check if hit target or stop
    if pnl_pct >= 5.0:  # Up 5%+
        print(f"🎯 {symbol} up {pnl_pct:.1f}% - consider taking profits")
    elif pnl_pct <= -2.0:  # Down 2%+
        print(f"🛑 {symbol} down {pnl_pct:.1f}% - hit stop-loss")
        close_position(symbol)
```

### 3:45 PM - Close All Positions
```python
from datetime import datetime

# Close everything before market close
if datetime.now().hour >= 15 and datetime.now().minute >= 45:
    print("⏰ Market closing - closing all positions")
    close_all_positions(cancel_orders=True)
    
    # Check final P/L
    summary = get_portfolio_summary()
    print(f"Day's P/L: ${summary['unrealized_pl']:.2f}")
```

---

## 9️⃣ Common Mistakes to Avoid

❌ **Don't Do:**
1. Buy without checking `get_trading_signals()`
2. Hold positions overnight
3. Average down on losers
4. Ignore stop-losses
5. Use position sizes > 10%
6. Trade without ATR-based stops
7. Hold through SELL signals

✅ **Do:**
1. Always check technical signals first
2. Close ALL positions by 3:45 PM
3. Accept losses quickly
4. Use tight stops (2×ATR)
5. Keep positions small (5-10%)
6. Calculate stops before entering
7. Exit on strong SELL signals

---

## 🔟 Troubleshooting

### Problem: No trading signal available
```python
# Solution: Extend date range
signal = get_quick_analysis("AAPL", days=60)  # Try 60 days instead of 30
```

### Problem: ATR is too high/low
```python
# Solution: Check if using right timeframe
# For day trading, use shorter periods
indicators = get_technical_indicators("AAPL", "2025-10-25", "2025-10-31")
```

### Problem: Position size too large
```python
# Solution: Use smaller percentage
shares = calculate_position_size(portfolio, price, 0.05)  # 5% instead of 10%
```

### Problem: Can't close position
```python
# Solution: Use market order to close immediately
close_position(symbol, qty=None)  # Close all shares at market
```

---

## 📊 Performance Tracking

### Daily Review Template
```python
from agent_tools.tool_alpaca_trade import get_portfolio_summary, get_orders

# Get day's summary
summary = get_portfolio_summary()
print(f"\n=== Daily Performance ===")
print(f"Portfolio Value: ${summary['equity']:.2f}")
print(f"Cash: ${summary['cash']:.2f}")
print(f"Unrealized P/L: ${summary['unrealized_pl']:.2f}")

# Get today's trades
orders = get_orders(status="closed", limit=20)
print(f"\nTrades Today: {len(orders)}")
for order in orders:
    print(f"  {order['side'].upper()} {order['qty']} {order['symbol']} @ ${order['filled_avg_price']}")
```

---

## 🎓 Learning Resources

### Documentation
- `DAY_TRADING_MIGRATION.md` - Full migration details
- `TECHNICAL_ANALYSIS_COMPLETE.md` - TA implementation
- `prompts/technical_analysis_guide.md` - Complete TA reference

### Test Scripts
- `test_ta_analysis.py` - Test TA on any stock
- `test_ta_integration.py` - Verify system integration

---

## ✅ Quick Checklist

**Before Trading:**
- [ ] MCP services running (ports 8004 & 8005)
- [ ] Virtual environment activated
- [ ] Account has buying power
- [ ] Market is open (9:30 AM - 4:00 PM ET)

**For Each Trade:**
- [ ] Get trading signal
- [ ] Check signal strength >= 2
- [ ] Calculate position size (<= 10%)
- [ ] Calculate stop-loss (entry - 2×ATR)
- [ ] Calculate take-profit (entry + 3×ATR)
- [ ] Execute order
- [ ] Monitor position

**End of Day:**
- [ ] Close all positions by 3:45 PM
- [ ] Review day's performance
- [ ] Prepare watchlist for tomorrow

---

**Ready to trade? Start with Step 1 above!** 🚀

Remember: Day trading requires discipline. Follow the signals, use stops, close positions daily!
