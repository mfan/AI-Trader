# Trading Strategy Updates - November 19, 2025

## Summary
Updated trading strategy based on Nov 18 performance analysis to improve risk management, margin utilization, and end-of-day procedures.

## Changes Made

### 1. Margin Buffer Rule (NEW)
**Problem:** 8 short selling attempts failed on Nov 18 due to insufficient buying power (agent over-leveraged with $12M long positions).

**Solution:** Maintain 30% buying power buffer
- Use maximum 70% of buying_power for long positions
- Reserve 30% for short opportunities and margin requirements
- Before shorting: Check if buying_power < 30% → Close weakest long first
- Never let buying_power drop below 20% (danger zone)

**Example:**
```
Buying Power: $1,500,000
Max Long Exposure: $1,050,000 (70%)
Reserved for Shorts: $450,000 (30%)
```

### 2. Mandatory End-of-Day Close (ENHANCED)
**Problem:** Need to ensure no overnight positions that could gap against us.

**Solution:** Strict 3:50 PM ET close procedure
- **3:50 PM ET:** MANDATORY close of ALL positions (10 min before market close)
- No new trades after 3:45 PM
- Run `close_all_positions()` at 3:50 PM
- Verify with `get_positions()` returns empty
- 10-minute buffer avoids last-minute slippage

**Why 3:50 PM (not 3:55 PM):**
- Gives buffer time for executions
- Avoids market maker spread widening in final minutes
- Ensures clean flat position before close
- Eliminates gap risk from overnight news

### 3. Position Sizing Discipline (REINFORCED)
**Problem:** Agent needs to check actual account values before every trade.

**Enhanced Checklist:**
```
Before EVERY Trade:
1. get_account() → Get current equity, cash, buying_power
2. Verify buying_power buffer: using < 70%?
3. Calculate position size: (equity × 2%) / (entry - stop)
4. Verify: position_value < (buying_power × 0.70)
5. If over 70% → Close weakest position first
6. Time check: Before 3:45 PM?
```

### 4. Active Position Management (IMPROVED)
**New Monitoring Requirements:**
- Check every 30-60 minutes:
  - Trade thesis valid?
  - Buying power still > 30%?
  - Time approaching 3:50 PM?
  
**If buying_power drops < 30%:**
1. Identify weakest performing position
2. Close it to restore margin buffer
3. Frees capital for short opportunities

### 5. Updated Exit Rules
**Immediate Exit Triggers:**
- Stop-loss hit
- SELL signal ≥ 2
- RSI > 75
- Volume dries up
- VWAP broken
- Impulse color change
- **3:50 PM ET reached (NEW - MANDATORY)**

## Implementation Status

✅ Strategy prompt updated in `prompts/agent_prompt.py`
✅ Active-trader service restarted (Nov 19 04:29:19 UTC)
✅ Alpaca-trade MCP service running with short selling enabled
✅ Enhanced trade logging operational (capturing filled details)

## Expected Benefits

1. **Better Short Execution:** 30% margin buffer prevents "insufficient buying power" failures
2. **Reduced Gap Risk:** 3:50 PM mandatory close eliminates overnight exposure
3. **Improved Risk Management:** Position sizing with real-time account checks
4. **More Balanced Trading:** Can trade both long and short without over-leveraging

## Verification

Monitor next trading day (Nov 19) for:
- [ ] All positions closed by 3:50 PM ET
- [ ] Buying power stays > 30% during trading
- [ ] Short positions execute successfully when signals appear
- [ ] Position sizing based on actual get_account() values
- [ ] Trade logs show filled execution details

## Key Rules Summary

**The 3 New Critical Rules:**
1. **30% Buffer Rule:** Use max 70% of buying_power (reserve 30% for shorts)
2. **3:50 PM Close Rule:** Close ALL positions 10 min before market close
3. **Pre-Trade Check:** Always run get_account() before sizing positions

**Risk Management Hierarchy:**
1. 6% Monthly Rule (stop trading if down 6% in month)
2. 2% Per-Trade Rule (risk max 2% equity per trade)
3. 30% Margin Buffer (keep 30% buying power available)
4. 3:50 PM Close (no overnight exposure)

---
*Updated: November 19, 2025*
*Status: ACTIVE*
