# Sleep Mode Bug Fix - November 14, 2025

## Critical Bug Discovered

**Date**: November 14, 2025 01:42 AM UTC  
**Impact**: System slept through entire trading day on November 13, 2025  
**Severity**: CRITICAL - Missed all trading opportunities  

## Root Cause Analysis

### The Bug
The system entered an **infinite sleep loop** at market open (9:30 AM ET) on November 13, 2025.

**Timeline of Failure (Nov 13, 2025):**
- **1:20 AM**: Correctly calculated "Next market opens: Thursday, November 13 at 09:30 AM ET"
- **1:20 AM**: Correctly set "Sleeping until 09:25:00 AM ET (wake up 5 min before market)"
- **9:29:54 AM**: System woke up at UTC 14:29:54 = 09:29:54 AM ET
- **9:29:54 AM - 2:24 PM**: INFINITE LOOP - System continuously logged:
  ```
  💤 Sleep mode active - Wake up in: 4h 53m
  💤 Sleep mode active - Wake up in: 3h 23m
  💤 Sleep mode active - Wake up in: 1h 23m
  ```
- **2:25 PM**: Finally woke up saying "WAKE UP - Preparing for market open in 5 minutes"
- **Result**: 5 hours late, missed entire trading day

### Why It Happened

**Problem 1: Market Hours Check Too Precise**
```python
# active_trader.py line 400 (BEFORE)
regular_start = time(9, 29, 55)    # 9:29:55 AM ET (5 sec buffer)
```
- System checked: `is_market_hours()` requires time >= 9:29:55
- System woke at: 9:29:54 AM (1 second too early!)
- Check returned: `False` (market "closed")

**Problem 2: Infinite Loop Logic**
```python
# active_trader.py lines 858-864 (BEFORE)
if sleep_seconds < 10:
    logger.info(f"⏰ Market opening imminent (in {max(0, int(sleep_seconds))}s) - exiting sleep mode")
    if sleep_seconds > 0:
        await asyncio.sleep(sleep_seconds)
    # Exit sleep mode - will check market hours again on next iteration
    continue
```

**The Loop:**
1. Wake at 9:29:54 AM
2. Calculate wake_time = 9:30 AM - 5 min = 9:25 AM
3. sleep_seconds = 9:25 AM - 9:29:54 AM = **negative value**
4. Since `sleep_seconds < 10`, log "Market opening imminent (in 0s)"
5. `continue` back to top of loop
6. Check `is_market_hours()` → returns `False` (still 9:29:54, needs 9:29:55)
7. Go to sleep mode logic again
8. Repeat steps 1-7 forever

### Evidence from Logs

```
2025-11-13 14:29:54 - ActiveTrader - INFO - ⏰ Current time: Thursday, November 13, 2025 at 09:29:54 AM ET
2025-11-13 14:29:54 - ActiveTrader - INFO - ⏭️  Next market opens: Thursday, November 13 at 09:30 AM ET
2025-11-13 14:29:54 - ActiveTrader - INFO - ⏳ Time until open: 0m 5s
2025-11-13 14:29:54 - ActiveTrader - INFO - ⏰ Market opening imminent (in 0s) - exiting sleep mode
[REPEATS HUNDREDS OF TIMES]
2025-11-13 14:29:54 - ActiveTrader - INFO - 💤 MARKET CLOSED - INTELLIGENT SLEEP MODE
2025-11-13 14:29:54 - ActiveTrader - INFO - ⏰ Current time: Thursday, November 13, 2025 at 09:29:54 AM ET
```

System got stuck at 9:29:54 AM, thinking market was about to open but never actually opening.

## The Fix

### Fix 1: Exact Market Hours Check
```python
# active_trader.py line 400 (AFTER)
regular_start = time(9, 30, 0)     # 9:30:00 AM ET (exact market open)
regular_end = time(16, 0)          # 4:00 PM ET
```
**Reason**: No need for 5-second buffer. Market opens exactly at 9:30:00.

### Fix 2: Smart Wake-Up Logic
```python
# active_trader.py lines 858-876 (AFTER)
if sleep_seconds < 10:
    # Calculate time until actual market open (not wake time)
    seconds_until_open = (next_open - now).total_seconds()
    
    # If we're past wake time but market hasn't opened yet, wait for market open
    if seconds_until_open > 0 and seconds_until_open <= 300:  # Within 5 minutes of open
        logger.info(f"⏰ Market opens in {int(seconds_until_open)}s - waiting for market open...")
        await asyncio.sleep(seconds_until_open + 1)  # Add 1 second buffer
        # Market should be open now - exit sleep mode
        logger.info(f"✅ Market is now open - exiting sleep mode")
        continue
    elif seconds_until_open <= 0:
        # Market should already be open - exit immediately
        logger.info(f"✅ Market should be open - exiting sleep mode")
        continue
    else:
        # Still more than 5 minutes until open - shouldn't happen
        logger.warning(f"⚠️  Unexpected state: wake_up in {sleep_seconds}s, market in {seconds_until_open}s")
        await asyncio.sleep(60)
        continue
```

**Reason**: Instead of checking wake_time, check actual market open time. If we're within 5 minutes but market hasn't opened, wait the remaining seconds then exit.

### Fix 3: Failsafe Market Hours Override
```python
# active_trader.py lines 814-825 (AFTER)
# FAILSAFE: Double-check market hours before entering sleep mode
# Prevents infinite sleep loops due to timing edge cases
if not is_open:
    import pytz
    from datetime import time
    eastern = pytz.timezone('US/Eastern')
    now_verify = datetime.now(eastern)
    current_time_verify = now_verify.time()
    regular_start = time(9, 30, 0)
    regular_end = time(16, 0, 0)
    
    # If we're actually IN market hours but check returned False, override
    if (now_verify.weekday() < 5 and 
        regular_start <= current_time_verify < regular_end):
        logger.warning(f"⚠️  FAILSAFE: Market IS open at {now_verify.strftime('%I:%M:%S %p ET')} - overriding sleep mode")
        is_open = True
        session = "regular"
```

**Reason**: Catches edge cases where timing issues cause wrong market detection. If current time is actually within 9:30 AM - 4:00 PM on weekday, force system to recognize market as open.

## Testing & Validation

### Manual Restart Required
After applying the fix, the service must be restarted:

```bash
sudo systemctl restart active-trader.service
```

### What to Monitor (Nov 14, 2025)

**Critical Check Times:**
- **9:25 AM ET**: System should wake up and log "WAKE UP - Preparing for market open"
- **9:30 AM ET**: System should recognize market is open and start trading
- **9:30 AM - 4:00 PM ET**: Continuous trading activity every 2 minutes
- **4:00 PM ET**: Close all positions and enter sleep mode

**Log Commands:**
```bash
# Watch wake-up at 9:25 AM
sudo journalctl -u active-trader.service -f | grep -E "WAKE|MARKET|Trading"

# Verify market open detection at 9:30 AM
sudo journalctl -u active-trader.service --since "09:25" --until "09:35" | grep -E "open|TRADING"

# Check for failsafe triggers (should NOT appear if fix works)
sudo journalctl -u active-trader.service | grep "FAILSAFE"
```

### Success Criteria
- ✅ System wakes at 9:25 AM ET
- ✅ Market detected as open at 9:30 AM ET  
- ✅ First trading cycle starts by 9:32 AM ET
- ✅ Agent logs created in `data/agent_data/xai-grok-4-fast/log/2025-11-14/`
- ✅ Trades executed throughout trading day
- ✅ No infinite loop messages
- ✅ No failsafe triggers

## Impact Assessment

### Nov 13, 2025 Losses
- **Trading Hours Missed**: 9:30 AM - 2:25 PM (4 hours 55 minutes)
- **Market Condition**: "Perfect down day" - strong bearish market
- **Opportunity Cost**: Newly-implemented shorting strategy untested
- **Trades Executed**: **ZERO**
- **Agent Logs**: None (agent never initialized)
- **Potential Profit**: Unknown, but user indicated significant opportunity

### Prevention Measures
1. **Fixed timing precision** - No more 5-second buffers causing edge cases
2. **Added failsafe** - Catches any future timing bugs
3. **Improved wake logic** - Waits for actual market open, not wake-up time
4. **Better logging** - Will log exact timestamps and conditions

## Files Modified

1. **active_trader.py**
   - Line 400: Changed `regular_start = time(9, 29, 55)` to `time(9, 30, 0)`
   - Lines 814-825: Added failsafe market hours check
   - Lines 858-876: Fixed wake-up logic to check market open time

## Deployment Instructions

**Step 1: Verify Fix Applied**
```bash
cd /home/mfan/work/aitrader
grep -n "regular_start = time(9, 30, 0)" active_trader.py
# Should show line 400 with the fixed code
```

**Step 2: Restart Service**
```bash
sudo systemctl restart active-trader.service
```

**Step 3: Verify Restart**
```bash
sudo systemctl status active-trader.service
# Should show "active (running)" status
```

**Step 4: Monitor Logs**
```bash
sudo journalctl -u active-trader.service -f
# Watch for normal sleep mode or trading activity
```

**Step 5: Next Morning Verification (Nov 14, 9:25 AM)**
```bash
# At 9:20 AM, start watching logs
sudo journalctl -u active-trader.service -f

# Should see at 9:25 AM:
# "⏰ WAKE UP - Preparing for market open in 5 minutes"

# Should see at 9:30 AM:
# "🟢 MARKET OPEN" or similar
# "🔄 TRADING CYCLE #1"
```

## Long-term Monitoring

### Daily Checks
- [ ] Verify system wakes at 9:25 AM
- [ ] Confirm trading starts at 9:30 AM
- [ ] Check agent logs exist for each day
- [ ] Verify positions closed by 4:00 PM

### Weekly Checks
- [ ] Review all failsafe triggers (should be zero)
- [ ] Check for any sleep mode anomalies
- [ ] Verify no infinite loop patterns
- [ ] Confirm consistent trading activity

### Monthly Checks
- [ ] Analyze timing accuracy across all trading days
- [ ] Review sleep/wake cycle performance
- [ ] Check for any new edge cases
- [ ] Update documentation if needed

## Related Issues

### Similar Bugs to Watch For
1. **Daylight Saving Time transitions** - DST changes could cause similar timing issues
2. **Market holidays** - System should detect holidays properly
3. **Early market closes** - Special schedules (e.g., day before holiday)
4. **Leap seconds** - Extremely rare but possible timing drift

### Preventive Measures
- Use Alpaca's `get_clock()` API as source of truth for market status
- Cross-reference pytz timezone with Alpaca API
- Add more comprehensive logging around market hours detection
- Consider adding alerts for unexpected sleep/wake patterns

## Lessons Learned

1. **Don't use timing buffers near critical boundaries** - The 5-second buffer (9:29:55) caused edge case
2. **Always have failsafes** - The failsafe check will prevent future similar bugs
3. **Test timing edge cases** - Need to test wake-up scenarios at exact market open time
4. **Use authoritative time sources** - Consider using Alpaca API clock instead of local time
5. **Log everything** - Comprehensive logging helped identify exact failure point

## Status

- [x] Bug identified and root cause analyzed
- [x] Fix implemented in active_trader.py
- [x] Documentation created
- [ ] Service restarted (requires sudo password)
- [ ] Fix verified (will verify Nov 14 at 9:30 AM)
- [ ] Long-term monitoring in place

## Contact

**Bug Reporter**: User (mfan)  
**Bug Discovered**: November 14, 2025 01:39 AM UTC  
**Bug Fixed**: November 14, 2025 01:50 AM UTC  
**Next Verification**: November 14, 2025 09:30 AM ET  

---

**Priority**: CRITICAL  
**Status**: FIX DEPLOYED, AWAITING RESTART  
**Next Action**: Restart service and monitor Nov 14 morning wake-up
