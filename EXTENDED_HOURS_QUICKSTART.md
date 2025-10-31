# 🕐 Extended Hours Trading - Quick Reference

## Market Schedule (Eastern Time)

```
┌─────────────────────────────────────────────────────────────┐
│  4 AM          9:30 AM            4 PM            8 PM      │
│   │               │                 │               │       │
│   ├───────────────┼─────────────────┼───────────────┤       │
│   │  PRE-MARKET   │    REGULAR      │  POST-MARKET  │       │
│   │   5.5 hrs     │     6.5 hrs     │    4 hrs      │       │
│   └───────────────┴─────────────────┴───────────────┘       │
│                                                              │
│        🌅 16 HOURS OF ACTIVE TRADING PER DAY 🌆            │
└─────────────────────────────────────────────────────────────┘
```

## Quick Commands

### Check Current Market Session
```bash
cd /home/mfan/work/aitrader
source .venv/bin/activate
python -c "from active_trader import is_market_hours; is_open, session = is_market_hours(); print(f'Open: {is_open}, Session: {session}')"
```

### Start Active Trader (All Sessions)
```bash
./start_active_trader.sh
```

### Start Active Trader (Custom Interval)
```bash
# Check every 5 minutes instead of 10
python active_trader.py configs/default_config.json 5
```

## Trading Commands for AI Agent

### Regular Hours Trading
```python
# Auto-detects, no extended_hours needed
buy("AAPL", 10)
sell("MSFT", 5)
```

### Pre-Market Trading (4 AM - 9:30 AM)
```python
buy("AAPL", 10, extended_hours=True)
sell("MSFT", 5, extended_hours=True)
```

### Post-Market Trading (4 PM - 8 PM)
```python
buy("GOOGL", 3, extended_hours=True)
sell("NVDA", 7, extended_hours=True)
```

## Session Detection

The `MARKET_SESSION` config value tells you the current session:

```python
from tools.general_tools import get_config_value

session = get_config_value("MARKET_SESSION")
# Returns: "pre-market", "regular", "post-market", or "closed"

# Use it in your trading logic
if session in ["pre-market", "post-market"]:
    # Use extended hours
    buy("AAPL", 10, extended_hours=True)
else:
    # Regular hours
    buy("AAPL", 10)
```

## MCP Services Status

Check if all services are running:

```bash
lsof -nP -iTCP:8001,8004,8005 -sTCP:LISTEN
```

Expected output:
```
python  74411  8001 LISTEN  (Jina Search)
python  74413  8004 LISTEN  (Alpaca Data)
python  91497  8005 LISTEN  (Alpaca Trade) ✨ UPDATED
```

## Session-Specific Strategies

### 🌅 Pre-Market (4 AM - 9:30 AM)
**Best for:**
- Reacting to overnight news
- Earnings announcements (often 7-8 AM)
- International market movements
- Setting positions before market open

**Cautions:**
- Lower liquidity - use limit orders
- Wider spreads
- Not all stocks active

### ☀️ Regular Hours (9:30 AM - 4 PM)
**Best for:**
- Highest liquidity
- Tightest spreads
- Most active trading
- Large position changes

**Standard trading:**
- Market orders work well
- Full stock availability
- Best execution prices

### 🌆 Post-Market (4 PM - 8 PM)
**Best for:**
- Earnings reactions (many at 4-5 PM)
- Late-breaking news
- Adjusting positions before next day
- Capturing after-hours moves

**Cautions:**
- Liquidity decreases over time
- Spreads widen
- Volume drops significantly after 6 PM

## Troubleshooting

### "Extended hours trading not allowed"
```bash
# Check Alpaca account settings
# Paper trading should have this enabled by default
# Verify in Alpaca dashboard > Settings
```

### Orders not filling
```python
# Use limit orders during extended hours
# Check spread before placing order:
get_stock_price("AAPL")
# Place limit order closer to current price
```

### Wrong timezone
```bash
# System uses pytz for accurate ET time
pip install pytz  # Should already be installed
```

## Testing Checklist

Before live trading in extended hours:

- [ ] Verify MCP services are running (ports 8001, 8004, 8005)
- [ ] Check current market session
- [ ] Test with small position sizes first
- [ ] Monitor spreads on your target stocks
- [ ] Verify Alpaca account has extended hours enabled
- [ ] Review logs after first extended hours trades

## Log Locations

```bash
# MCP service logs
tail -f /tmp/jina.log
tail -f /tmp/alpaca_data.log
tail -f /tmp/alpaca_trade.log

# Active trader output (if run in background)
tail -f nohup.out
```

## Important Reminders

🚨 **Extended hours = Extended risks**
- Lower liquidity
- Wider spreads  
- Higher volatility
- Not all stocks available

✅ **Best practices:**
- Start with small sizes
- Use limit orders
- Monitor spreads
- Check volume
- Be patient with fills

🎯 **Sweet spots:**
- Pre-market: 7:00-9:00 AM (earnings, news)
- Regular: All day (highest liquidity)
- Post-market: 4:00-5:00 PM (earnings reactions)

## Quick Sanity Check

Run this before starting extended hours trading:

```bash
cd /home/mfan/work/aitrader
source .venv/bin/activate

# Check market status
python -c "from active_trader import is_market_hours; print(is_market_hours())"

# Verify services
lsof -nP -iTCP:8001,8004,8005 -sTCP:LISTEN | wc -l
# Should show: 3 (one per service)

# Check account
python -c "from tools.alpaca_trading import get_alpaca_client; client = get_alpaca_client(); print(client.get_account())"
```

All checks pass? **You're ready to trade extended hours!** 🚀

---

**Updated**: October 31, 2025  
**Total Trading Window**: 16 hours/day (4 AM - 8 PM ET)  
**MCP Services**: ✅ Running with extended hours support
