# Momentum-Based Swing Trading System - Implementation Complete

## 🎯 Overview

Successfully implemented a **dynamic momentum-based stock selection system** that replaces the fixed watchlist with daily scans of actual market movers. This system identifies the top 100 highest-volume stocks from the previous day and trades them using swing trading strategies (1-3 day holds) with optional options leverage.

## ✅ Components Implemented

### 1. **Momentum Scanner** (`tools/momentum_scanner.py`)
   - Scans previous trading day's market data
   - Filters stocks with 10M-20M+ daily volume
   - Ranks by price change percentage (momentum strength)
   - Selects top 50 gainers + top 50 losers
   - Returns 100-stock dynamic watchlist with TA indicators
   
### 2. **SQLite Cache Database** (`tools/momentum_cache.py`)
   - Fast indexed queries for intraday trading
   - Stores: symbol, OHLCV data, volume, momentum scores, TA indicators
   - Automatic cache expiration after market close
   - Historical tracking (30 days retention)
   - Market regime tracking (bullish/bearish/neutral)
   - Thread-safe operations
   
### 3. **Pre-Market Scan Integration** (`active_trader.py`)
   - Runs momentum scan 5 minutes before market open (9:25 AM ET)
   - Caches results to SQLite for fast access during trading
   - Replaces fixed watchlist with dynamic momentum list
   - Fallback to static watchlist if scan fails
   - Logs detailed scan statistics
   
### 4. **Updated Trading Strategy** (`prompts/agent_prompt.py`)
   - Swing trading focus (1-3 day holds, not intraday)
   - Momentum continuation strategy (ride yesterday's movers)
   - Market regime alignment (never counter-trend)
   - Options trading guidelines (calls/puts for 2-3x leverage)
   - Position sizing for overnight risk
   - Clear entry/exit rules for swing trades

## 🚀 How It Works

### Morning Routine (Pre-Market 9:00-9:25 AM ET):

```
1. System wakes up at 9:00 AM ET
2. Runs momentum scan on previous day's data
3. Filters for 10M-20M+ volume stocks
4. Ranks by price change % (gainers and losers)
5. Selects top 50 gainers + top 50 losers = 100 stocks
6. Calculates technical indicators for each
7. Caches to SQLite database
8. Determines market regime (bullish/bearish/neutral)
9. Agent loads dynamic watchlist for the day
```

### Trading Day (9:30 AM - 4:00 PM ET):

```
1. Agent focuses ONLY on today's 100 momentum stocks
2. Looks for continuation patterns:
   • GAINERS: Pullbacks to support → Buy calls or go long
   • LOSERS: Bounces to resistance → Buy puts or short
3. Aligns trades with market regime:
   • Bullish market → Focus on gainers (long bias)
   • Bearish market → Focus on losers (short bias)
4. Uses swing trading approach:
   • Hold 1-3 days (not intraday)
   • Wider stops for overnight moves
   • Options for 2-3x leverage
5. Fast cache queries (no repeated API calls)
```

## 📊 Momentum Selection Criteria

### Volume Filter:
- **Minimum**: 10M daily volume
- **Ideal**: 20M+ daily volume
- **Why**: Ensures liquidity and institutional interest

### Momentum Ranking:
- **Top 50 Gainers**: Highest % price increase yesterday
- **Top 50 Losers**: Highest % price decrease yesterday
- **Why**: Momentum tends to persist 1-3 days

### Market Regime:
- **Bullish Tide**: SPY/QQQ up → Trade gainers (long bias)
- **Bearish Tide**: SPY/QQQ down → Trade losers (short bias)
- **Neutral**: Mixed signals → Both directions OK

## 🎯 Swing Trading Rules

### Entry Rules:
✅ Momentum continues from previous day
✅ Market regime supports the direction
✅ Technical setup confirms (Triple Screen)
✅ Volume above average
✅ Options have good liquidity

### Exit Rules:
✅ Target hit (resistance/support levels)
✅ Momentum reverses (Impulse System color change)
✅ Stop hit (2% account risk or SafeZone stop)
✅ Day 3 reached (take profits if no strong reason to hold)
✅ Market regime changes

### Position Sizing:
- **Options**: 1-2% risk per position
- **Stock**: 2% risk per position (slightly larger size OK)
- **Max Positions**: 3-5 swings at once
- **Leverage**: 2-3x via options, avoid over-leveraging

## ⚡ Options Trading Strategy

### Call Options (Bullish Momentum):
```
Stock: In yesterday's GAINERS list
Strike: At-the-money (ATM) or slightly OTM
Expiration: 2-4 weeks out
Entry: Pullback to support or breakout
Target: 50-100% profit
Stop: 25-50% loss
Max Loss: Premium paid (defined risk)
```

### Put Options (Bearish Momentum):
```
Stock: In yesterday's LOSERS list
Strike: At-the-money (ATM) or slightly OTM
Expiration: 2-4 weeks out
Entry: Bounce to resistance or breakdown
Target: 50-100% profit
Stop: 25-50% loss
Max Loss: Premium paid (defined risk)
```

### Why Options for Swings:
1. **Limited Risk**: Max loss = premium (no overnight gap destroying account)
2. **Leverage**: Control more stock with less capital
3. **Defined Risk**: Perfect for overnight holds
4. **Time Decay**: 1-3 day holds minimize theta
5. **Directional Clarity**: Calls = bullish, Puts = bearish

## 📁 File Structure

```
/home/mfan/work/aitrader/
├── tools/
│   ├── momentum_scanner.py          ✅ NEW - Daily momentum scanning
│   └── momentum_cache.py            ✅ NEW - SQLite caching system
├── prompts/
│   └── agent_prompt.py              ✅ UPDATED - Swing trading strategy
├── active_trader.py                 ✅ UPDATED - Pre-market scan integration
└── data/
    ├── momentum_cache.db            ✅ NEW - Cached momentum data
    └── agent_data/
        └── {model_name}/
            └── momentum_cache.db    ✅ NEW - Model-specific cache
```

## 🔄 Daily Workflow

### Pre-Market (9:00-9:30 AM):
```
09:00 AM: System wakes up
09:00 AM: Momentum scan starts
09:05 AM: Scan completes, data cached
09:10 AM: Agent reviews top movers
09:15 AM: Market regime determined
09:20 AM: Potential setups identified
09:25 AM: Final prep before open
09:30 AM: Market opens, ready to trade
```

### Trading Hours (9:30 AM-4:00 PM):
```
09:30-10:30 AM: Monitor opening moves
10:30-11:00 AM: Enter swing trades if setups trigger
11:00-03:00 PM: Manage existing positions
03:00-03:55 PM: Evaluate whether to hold overnight
03:55 PM: Close day trades, keep swing trades
04:00 PM: Market close, review performance
```

### After Hours:
```
04:00-05:00 PM: Review day's trades
05:00-06:00 PM: Plan for tomorrow
               Check overnight news
               Review momentum for current holdings
               Prepare watchlist notes
```

## 📊 Database Schema

### `daily_movers` Table:
```sql
- scan_date: Date of scan
- symbol: Stock ticker
- direction: 'gainer' or 'loser'
- rank: Position in momentum ranking
- open, high, low, close: OHLC data
- volume: Trading volume
- change_pct: Price change percentage
- indicators: JSON with TA data
- momentum_score: Absolute value of change_pct
```

### `market_regime` Table:
```sql
- scan_date: Date of scan
- regime: 'bullish', 'bearish', or 'neutral'
- spy_change_pct: SPY price change
- qqq_change_pct: QQQ price change
- market_score: Average of SPY/QQQ
```

## 🎓 Strategy Advantages

### vs Fixed Watchlist:
✅ **Dynamic**: Adapts to current market conditions
✅ **Proven Movers**: These stocks actually moved yesterday
✅ **High Volume**: Ensures liquidity for entries/exits
✅ **Both Directions**: Profit from up AND down moves
✅ **Fresh Every Day**: No stale stocks that don't move

### vs Day Trading:
✅ **Less Stress**: Not staring at screen all day
✅ **Bigger Moves**: Capture multi-day trends (more profit potential)
✅ **Lower Frequency**: 2-3 good swings > 10 day trades
✅ **Options Leverage**: 2-3x returns with defined risk
✅ **Time Efficiency**: Check morning and evening, not every minute

### vs Buy and Hold:
✅ **Active Management**: Not waiting months/years
✅ **Momentum Edge**: Ride proven winners, avoid losers
✅ **Defined Exits**: Clear targets and stops
✅ **Flexibility**: Can go long or short based on market
✅ **Capital Efficiency**: Rotate to best opportunities

## 🚨 Risk Management Integration

### Elder's 6% Monthly Rule:
- Still enforced for swing trading
- Tracks total equity (cash + positions)
- Suspends trading if down 6% in month
- Automatic resume next month

### Position Sizing:
- **Options**: 1-2% risk per trade (premium as max loss)
- **Stock**: 2% risk per trade (stop distance)
- **Total Portfolio**: Max 6% at risk across all positions

### Stop Loss:
- **Day 1**: Set stop at entry or SafeZone level
- **Day 2**: Move to breakeven if +50% profit
- **Day 3**: Trail stop or take profits

## 🔧 Configuration

### Momentum Scanner Settings:
```python
MIN_VOLUME = 10_000_000      # 10M minimum
IDEAL_VOLUME = 20_000_000    # 20M+ ideal
TOP_GAINERS_COUNT = 50       # Top 50 gainers
TOP_LOSERS_COUNT = 50        # Top 50 losers
TOTAL_WATCHLIST_SIZE = 100   # Combined list
```

### Cache Settings:
```python
DEFAULT_DB_PATH = "data/momentum_cache.db"
MARKET_CLOSE_TIME = time(16, 0)  # 4:00 PM ET
CACHE_RETENTION_DAYS = 30        # Historical data kept
```

## 📈 Expected Performance Improvements

### vs Fixed Watchlist:
- **Higher Win Rate**: Trading proven movers vs random picks
- **Better Entries**: Momentum continuation patterns
- **More Opportunities**: 100 stocks vs ~20 active traders
- **Market Alignment**: Auto-adjusts to bullish/bearish conditions

### Options Leverage Benefits:
- **2-3x Returns**: Options amplify moves
- **Defined Risk**: Max loss = premium paid
- **Capital Efficiency**: Control more with less
- **Overnight Safety**: No gap risk beyond premium

## 🧪 Testing Checklist

- [ ] Run momentum scan with real Alpaca data
- [ ] Verify SQLite cache creation and queries
- [ ] Test with 10 stocks to validate speed
- [ ] Test with 100 stocks to check performance
- [ ] Validate momentum rankings accuracy
- [ ] Check market regime detection (bullish/bearish)
- [ ] Test options order placement (if available)
- [ ] Verify cache expiration after market close
- [ ] Test fallback to static watchlist on scan failure
- [ ] Run backtest on historical data (optional)

## 🚀 How to Use

### Start Trading with Momentum System:

```bash
# 1. System will automatically run pre-market scan at 9:00 AM
# 2. Cache populated with top 100 momentum stocks
# 3. Agent trades only these stocks during the day

# Check momentum cache manually:
python3 -c "from tools.momentum_cache import MomentumCache; MomentumCache().print_cache_summary()"

# View today's watchlist:
python3 -c "from tools.momentum_cache import get_momentum_watchlist; print(get_momentum_watchlist())"

# Check market regime:
python3 -c "from tools.momentum_cache import get_market_regime; print(get_market_regime())"
```

### Monitor Pre-Market Scan:

```bash
# Watch logs during pre-market scan (9:00-9:30 AM):
sudo journalctl -u active-trader -f

# Look for:
# 🔍 PRE-MARKET MOMENTUM SCAN
# ✅ MOMENTUM SCAN COMPLETE
# 📈 Gainers: 50
# 📉 Losers: 50
# 🎯 Market Regime: BULLISH
```

## 📚 Key Concepts

### Momentum Persistence:
> "Objects in motion tend to stay in motion"
> 
> Stocks that moved strongly yesterday often continue for 1-3 days
> before momentum fades. We ride this wave.

### Volume = Conviction:
> "High volume = big players are involved"
> 
> 10M-20M+ volume means institutions are trading, not just retail.
> This provides liquidity and continuation probability.

### Swing Trading Sweet Spot:
> "Too fast to miss the move, too slow to lose momentum"
> 
> 1-3 days captures the meat of the move without day trading stress
> or buy-and-hold stagnation.

### Options for Leverage:
> "Control more stock with less capital, limit downside risk"
> 
> Options provide 2-3x leverage while defining max loss to premium paid.
> Perfect for overnight holds where gaps can hurt.

---

**Status**: ✅ Core System Complete - Ready for Testing
**Next**: Implement Alpaca API integration + Options support + Backtesting
**Date**: 2025-11-08
