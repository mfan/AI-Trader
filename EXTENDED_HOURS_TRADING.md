# Extended Hours Trading Guide

## Overview

The AI Trader now supports **extended hours trading** including pre-market and post-market sessions through Alpaca's API.

## Market Sessions

### Trading Hours (Eastern Time)

| Session | Time (ET) | Duration |
|---------|-----------|----------|
| **Pre-Market** | 4:00 AM - 9:30 AM | 5.5 hours |
| **Regular** | 9:30 AM - 4:00 PM | 6.5 hours |
| **Post-Market** | 4:00 PM - 8:00 PM | 4 hours |
| **Closed** | 8:00 PM - 4:00 AM | 8 hours |

### Total Trading Window
- **16 hours per day** (4 AM - 8 PM ET) on weekdays
- No trading on weekends

## How It Works

### 1. Market Hours Detection

The `active_trader.py` automatically detects which session you're in:

```python
is_open, session_type = is_market_hours()
# Returns: (True, "pre-market") or (True, "regular") or (True, "post-market") or (False, "closed")
```

### 2. Extended Hours Orders

When placing orders during pre-market or post-market hours, set `extended_hours=True`:

**Buy Order:**
```python
# During regular hours (extended_hours defaults to False)
result = buy("AAPL", 10)

# During pre-market or post-market (extended_hours=True)
result = buy("AAPL", 10, extended_hours=True)
```

**Sell Order:**
```python
# Regular hours
result = sell("AAPL", 5)

# Extended hours
result = sell("AAPL", 5, extended_hours=True)
```

### 3. Active Trader Integration

The active trader now:
- ✅ Monitors portfolio from 4 AM to 8 PM ET
- ✅ Automatically detects current market session
- ✅ Adjusts trading strategy based on session type
- ✅ Logs session type in trading records

## MCP Tool Updates

### Buy Tool

```python
@mcp.tool()
def buy(symbol: str, quantity: int, order_type: str = "market", extended_hours: bool = False):
    """
    Place a buy order for a stock
    
    Args:
        symbol: Stock symbol (e.g., "AAPL")
        quantity: Number of shares
        order_type: "market" or "limit"
        extended_hours: Allow pre-market/post-market execution (default: False)
    """
```

### Sell Tool

```python
@mcp.tool()
def sell(symbol: str, quantity: int, order_type: str = "market", extended_hours: bool = False):
    """
    Place a sell order for a stock
    
    Args:
        symbol: Stock symbol (e.g., "AAPL")  
        quantity: Number of shares
        order_type: "market" or "limit"
        extended_hours: Allow pre-market/post-market execution (default: False)
    """
```

## AI Agent Instructions

The AI agent should automatically determine whether to use `extended_hours=True` based on:

1. **Session Detection**: Check the `MARKET_SESSION` config value
2. **Order Timing**: If in "pre-market" or "post-market", set `extended_hours=True`
3. **Liquidity Awareness**: Consider that extended hours typically have:
   - Lower trading volume
   - Wider bid-ask spreads
   - Potentially higher volatility
   - Not all stocks available

## Running the Active Trader

### Standard Run (all hours)
```bash
./start_active_trader.sh
```

### Custom Interval (check every 5 minutes)
```bash
cd /home/mfan/work/aitrader
source .venv/bin/activate
python active_trader.py configs/default_config.json 5
```

### Output Example
```
🟢 Market is open - PRE-MARKET session
🔄 TRADING CYCLE #1 - PRE-MARKET SESSION
⏰ Time: 2025-10-31 07:30:15

...

🟢 Market is open - REGULAR session
🔄 TRADING CYCLE #5 - REGULAR SESSION
⏰ Time: 2025-10-31 10:15:42

...

🟢 Market is open - POST-MARKET session
🔄 TRADING CYCLE #12 - POST-MARKET SESSION
⏰ Time: 2025-10-31 17:45:23
```

## Important Considerations

### Extended Hours Risks

1. **Lower Liquidity**
   - Fewer market participants
   - Harder to execute large orders
   - May get worse prices

2. **Wider Spreads**
   - Bid-ask spreads typically wider
   - Market orders may execute at unfavorable prices
   - Consider using limit orders

3. **Limited Stock Availability**
   - Not all stocks trade during extended hours
   - Check if your target stocks are available

4. **News Impact**
   - Pre-market often reacts to overnight news
   - Post-market reacts to earnings reports
   - Higher volatility around news events

### Best Practices

1. **Use Limit Orders** in extended hours when possible
2. **Monitor spreads** before placing orders
3. **Start small** during extended hours until comfortable
4. **Check volume** for your target stocks
5. **Set alerts** for significant news events

## Configuration

### Enable/Disable Extended Hours

To trade only during regular hours, modify `active_trader.py`:

```python
def is_market_hours():
    # ... timezone setup ...
    
    # Only trade during regular hours
    if regular_start <= current_time < regular_end:
        return True, "regular"
    else:
        return False, "closed"
```

### Adjust Check Intervals by Session

You could customize intervals based on session:

```python
# More frequent during regular hours
if session_type == "regular":
    interval = 10  # Check every 10 minutes
elif session_type in ["pre-market", "post-market"]:
    interval = 20  # Check every 20 minutes (less active)
```

## Testing

### Test Extended Hours Locally

1. **Check current session:**
```python
python -c "
from active_trader import is_market_hours
is_open, session = is_market_hours()
print(f'Market open: {is_open}, Session: {session}')
"
```

2. **Test extended hours order:**
```python
# In your test script
result = buy("AAPL", 1, extended_hours=True)
print(result)
```

## Alpaca Requirements

### API Permissions

Make sure your Alpaca account has:
- ✅ Extended hours trading enabled
- ✅ Paper trading API keys configured
- ✅ Proper account permissions

### Check Your Account Settings

1. Log into Alpaca dashboard
2. Go to Account Settings
3. Verify "Extended Hours Trading" is enabled
4. For paper trading, this is typically enabled by default

## Troubleshooting

### "Extended hours trading not allowed"

**Solution**: Check your Alpaca account settings and ensure extended hours is enabled.

### Orders not filling in extended hours

**Possible causes**:
- Stock not available during extended hours
- Price too far from market (use limit orders closer to market price)
- Very low volume for that stock

### Time zone issues

The system uses `pytz` to handle Eastern Time properly. Make sure you have it installed:
```bash
pip install pytz
```

## Summary

✅ **Extended hours support added** (4 AM - 8 PM ET)  
✅ **Automatic session detection** (pre-market, regular, post-market)  
✅ **MCP tools updated** with `extended_hours` parameter  
✅ **Active trader enhanced** to trade across all sessions  
✅ **Proper timezone handling** with pytz  

Your AI trader can now monitor and trade:
- **Pre-market**: React to overnight news and earnings
- **Regular hours**: Full liquidity and participation  
- **Post-market**: Capture after-hours movements

**Total active trading window: 16 hours per day** 🚀
