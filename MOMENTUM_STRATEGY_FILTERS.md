# Momentum Trading Strategy - Quality Filters

## Overview

Our momentum scanner identifies top market movers with strict quality filters to avoid junk stocks and ensure clean, tradeable momentum signals.

## Quality Filters (NO JUNK)

### 1. Price Filter: >= $5.00
**Rationale:** Eliminates penny stock behavior
- Below $5: Jumpy gaps, fragile order books, easy manipulation
- High slippage on entry/exit
- Often used in pump-and-dump schemes
- Poor liquidity even with 10M volume

### 2. Market Cap Filter: >= $2 Billion
**Rationale:** Sweet spot for quality momentum

**Why $2B (not $1B)?**
- **$0-$1B (Micro-cap):** Pure junk territory
  - Extreme volatility from news/mania
  - Easy to manipulate
  - Fragile liquidity even with volume spikes
  
- **$1B-$1.5B (Small-cap edge):** Still risky
  - Can get jumpy gaps
  - Order book can be thin
  - Slippage issues on larger orders
  
- **$2B+ (Sweet Spot):** Quality movers ✅
  - Cuts most penny/low-float garbage
  - Still captures stocks doing 3-10%+ daily moves
  - Better fills for intraday/swing systems
  - Institutional flow provides support
  - Aligns with "top 100 only" philosophy

**When to go stricter ($5B+)?**
- If seeing too much noise in results
- Trading larger position sizes
- Want almost exclusively mid/large caps
- Trade-off: Miss some spicy movers, gain quality/liquidity

### 3. Volume Filter: >= 10M Daily
**Rationale:** Ensures liquidity and institutional interest
- 10M-20M: Sweet spot for volatility + liquidity
- 20M-50M: Optimal for larger positions
- Institutional participation = cleaner price action
- Easier entry/exit with minimal slippage

### 4. Universe Filter: S&P 500 & NASDAQ-100 Only
**Rationale:** Pre-vetted quality stocks
- All have $2B+ market cap by design
- Already meet listing requirements
- Regular SEC reporting and oversight
- No OTC or pink sheet stocks
- No pre-revenue biotech junk

### 5. Exclusions
**What we DON'T trade:**
- ❌ OTC and pink sheet stocks (manipulation risk)
- ❌ Leveraged ETFs (TQQQ, SQQQ, UPRO, SPXU, etc.)
  - Decay issues from daily rebalancing
  - Tracking errors compound over time
  - Not suitable for multi-day holds
- ❌ Inverse ETFs (-1x, -2x, -3x)
  - Same decay issues
  - Better to use puts for downside
- ❌ Pre-revenue biotech/pharma (binary FDA risk)
- ❌ SPACs before merger (speculation, no fundamentals)

## Filter Implementation

### Code Constants
```python
MIN_PRICE = 5.0                # $5 minimum price
MIN_VOLUME = 10_000_000        # 10M daily volume
MIN_MARKET_CAP = 2_000_000_000 # $2B market cap
```

### Scan Process
1. **Universe (106 stocks):** S&P 500 + NASDAQ-100 mega/large caps
2. **Fetch data:** Previous day OHLCV for all symbols
3. **Price filter:** Remove any stock < $5 (should be rare in our universe)
4. **Volume filter:** Keep only 10M+ daily volume
5. **Rank:** Sort by price change % (open to close)
6. **Select:** Top 50 gainers + Top 50 losers = 100 total
7. **Cache:** Store to SQLite with TA indicators

### Filter Results (Nov 7, 2025 Example)
- Universe: 106 stocks
- Price >= $5: 105 stocks (99% pass rate)
- Volume >= 10M: 51 stocks (48% pass rate)
- Final selection: 100 stocks (50 gainers + 50 losers)

## Why These Filters Work

### 1. Eliminates Noise
- No penny stocks pumping on chat room hype
- No micro-caps manipulated by small volume
- No leveraged ETF decay eating returns

### 2. Ensures Quality
- Real companies with real businesses
- Institutional ownership and flow
- SEC reporting and oversight
- Analyst coverage and research

### 3. Improves Execution
- Tighter bid-ask spreads
- Lower slippage on fills
- Can scale position sizes
- Options have better liquidity

### 4. Reduces Risk
- Less manipulation risk
- More predictable price action
- Better risk/reward ratios
- Cleaner technical patterns

### 5. Aligns with Strategy
- Momentum swing trading (1-3 days)
- Options for leverage (2-3x returns)
- Market regime alignment
- Elder's risk management (6% rule)

## Monitoring and Adjustment

### If Too Much Noise (can tighten later):
```python
MIN_PRICE = 10.0               # $10 minimum
MIN_MARKET_CAP = 5_000_000_000 # $5B market cap
MIN_VOLUME = 20_000_000        # 20M volume
```

### If Too Restrictive (rare, but possible):
```python
MIN_PRICE = 3.0                # $3 minimum
MIN_MARKET_CAP = 1_000_000_000 # $1B market cap
# Keep volume at 10M (don't go lower)
```

### Current Settings (Recommended Start):
```python
MIN_PRICE = 5.0                # $5 minimum ✅
MIN_MARKET_CAP = 2_000_000_000 # $2B market cap ✅
MIN_VOLUME = 10_000_000        # 10M volume ✅
```

## Expected Results

### Stock Characteristics
- Average market cap: $10B-$100B
- Average daily volume: 15M-50M
- Average price: $50-$200
- Typical daily range: 2-5%
- Options available: Yes (most stocks)
- Institutional ownership: High (60-80%)

### Momentum Quality
- Clean trends (not choppy)
- Decent liquidity (can enter/exit)
- News-driven or technical momentum
- Multi-day potential (1-3 days)
- Options spreads: Reasonable (<2%)

### Risk Profile
- Lower manipulation risk
- More predictable volatility
- Better technical reliability
- Cleaner stop placement
- Scalable position sizing

## Summary

**Our philosophy:** Trade QUALITY momentum, not JUNK momentum.

By using strict filters ($5 price, $2B market cap, 10M volume, major indices only), we ensure we're trading real stocks with real institutional flow, not penny stock garbage that can gap against us or have no liquidity when we need to exit.

**Result:** Cleaner signals, better fills, lower risk, higher probability of success.

---

**Last Updated:** November 8, 2025  
**Status:** Filters implemented and tested ✅  
**Test Results:** Nov 7, 2025 - 105/106 stocks passed price filter, 51 passed volume filter, 100 stocks selected
