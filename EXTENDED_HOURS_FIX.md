# Extended Hours Trading Fix

## Issue Summary
**Critical Bug**: Orders placed during post-market hours (4:00 PM - 8:00 PM ET) were being submitted as regular orders without the `extended_hours=True` parameter. This caused orders to be queued until the next trading day instead of executing immediately.

## Problem Details

### Symptoms
- Orders placed after 4:00 PM ET remained in "pending" status
- Orders would not fill until 9:30 AM ET the next day
- Example: NVDA buy orders submitted at ~4:13 PM stayed pending overnight

### Root Cause
The MCP trading tools (`buy()`, `sell()`, `close_position()`) had `extended_hours` parameter defaulting to `False`, and there was no automatic detection of market session. The agent would need to explicitly pass `extended_hours=True`, which it wasn't doing.

## Solution Implemented

### 1. Auto-Detection Function
Added `_is_extended_hours()` helper function in `agent_tools/tool_alpaca_trade.py`:
```python
def _is_extended_hours() -> bool:
    """
    Auto-detect if we're in extended hours (pre-market or post-market)
    
    Returns:
        True if in pre-market or post-market, False if in regular hours or closed
    """
    # Checks current time in Eastern timezone
    # Pre-market: 4:00 AM - 9:30 AM ET
    # Post-market: 4:00 PM - 8:00 PM ET
    # Returns True for extended hours, False for regular hours or closed
```

### 2. Updated MCP Tools

#### buy() Function
**Before:**
```python
def buy(symbol: str, quantity: int, order_type: str = "market", 
        extended_hours: bool = False) -> Dict[str, Any]:
```

**After:**
```python
def buy(symbol: str, quantity: int, order_type: str = "market", 
        extended_hours: bool = None) -> Dict[str, Any]:
    # Auto-detect extended hours if not specified
    if extended_hours is None:
        extended_hours = _is_extended_hours()
        if extended_hours:
            print(f"🌙 Auto-detected extended hours trading for {symbol}")
```

#### sell() Function
**Before:**
```python
def sell(symbol: str, quantity: int, order_type: str = "market", 
         extended_hours: bool = False) -> Dict[str, Any]:
```

**After:**
```python
def sell(symbol: str, quantity: int, order_type: str = "market", 
         extended_hours: bool = None) -> Dict[str, Any]:
    # Auto-detect extended hours if not specified
    if extended_hours is None:
        extended_hours = _is_extended_hours()
        if extended_hours:
            print(f"🌙 Auto-detected extended hours trading for {symbol}")
```

#### close_position() Function
**Before:**
```python
def close_position(symbol: str) -> Dict[str, Any]:
    # Used SDK's close_position (no extended_hours support)
    result = alpaca_client.close_position(symbol)
```

**After:**
```python
def close_position(symbol: str, extended_hours: bool = None) -> Dict[str, Any]:
    # Auto-detect extended hours if not specified
    if extended_hours is None:
        extended_hours = _is_extended_hours()
        if extended_hours:
            print(f"🌙 Auto-detected extended hours for closing {symbol}")
    
    # Use sell_market with extended_hours parameter
    qty = int(float(position["qty"]))
    result = alpaca_client.sell_market(symbol, qty, extended_hours=extended_hours)
```

## Trading Sessions

### Extended Hours Schedule (Eastern Time)
- **Pre-market**: 4:00 AM - 9:30 AM ET
- **Regular**: 9:30 AM - 4:00 PM ET  
- **Post-market**: 4:00 PM - 8:00 PM ET

### Auto-Detection Behavior
| Current Time | Session | extended_hours |
|--------------|---------|----------------|
| 3:00 AM ET | Closed | False |
| 4:15 AM ET | Pre-market | True |
| 10:00 AM ET | Regular | False |
| 2:00 PM ET | Regular | False |
| 4:30 PM ET | Post-market | True |
| 9:00 PM ET | Closed | False |

## Benefits

### 1. Automatic Correction
- **No manual intervention required**: Orders automatically use correct parameters
- **Session-aware**: System knows when it's in extended hours
- **Backward compatible**: Agent can still explicitly set `extended_hours=True/False` if needed

### 2. Improved Execution
- **Immediate fills**: Post-market orders execute right away (within liquidity constraints)
- **No overnight delays**: Orders don't wait until next day
- **Better pricing**: Capture opportunities as they happen

### 3. Safety Features
- **Fail-safe default**: If session detection fails, defaults to `False` (safer)
- **Logging**: System logs when extended hours are auto-detected
- **Explicit override**: Agent can still force extended hours on/off

## Testing

### Test Results (4:13 PM ET - Post-Market)
```bash
Current time (ET): 16:13:27 (4:13 PM)
Weekday: 0 (Monday)
Extended hours: True
Session type: post-market

✅ Orders will automatically use extended_hours=True
```

### Verification Commands
```bash
# Check if services are running
sudo systemctl status alpaca-trade.service
sudo systemctl status active-trader.service

# Monitor logs for extended hours detection
tail -f logs/active_trader_stdout.log | grep "extended hours"

# Check recent orders
# (Orders placed after 4PM should show extended_hours: true)
```

## Impact on Existing System

### Files Modified
1. **agent_tools/tool_alpaca_trade.py**
   - Added `_is_extended_hours()` function
   - Updated `buy()`, `sell()`, `close_position()` functions
   - Changed default from `False` to `None` (auto-detect)

### No Changes Needed
- ❌ Agent prompts (automatic now)
- ❌ active_trader.py (already passing session info)
- ❌ Configuration files
- ❌ alpaca_trading.py (already supports extended_hours)

### Deployment
```bash
# Restart services to apply fix
sudo systemctl restart alpaca-trade.service
sudo systemctl restart active-trader.service

# Verify services running
sudo systemctl status active-trader.service
```

## Examples

### Before Fix (Broken)
```
4:13 PM ET: Agent wants to buy NVDA
→ buy("NVDA", 78, "market")  # extended_hours defaults to False
→ Order submitted WITHOUT extended_hours flag
→ Order status: "pending"
→ Waits until 9:30 AM next day
❌ LOST: 18+ hours of potential price movement
```

### After Fix (Working)
```
4:13 PM ET: Agent wants to buy NVDA
→ buy("NVDA", 78, "market")  # extended_hours=None (auto-detect)
→ System detects: 4:13 PM = post-market
→ Auto-sets: extended_hours=True
→ Order submitted WITH extended_hours flag
→ Order fills immediately (assuming liquidity)
✅ GAINED: Immediate execution at desired price
```

## Important Notes

### Extended Hours Constraints
1. **Liquidity**: Lower volume than regular hours
2. **Spreads**: Wider bid-ask spreads
3. **Order Types**: Market orders may have wider fills
4. **Best Practice**: Consider using limit orders in extended hours

### Agent Behavior
- Agent will continue trading through all three sessions
- Positions flow continuously from pre-market → regular → post-market
- Only forced close time: 7:55 PM ET (end of trading day)
- System automatically handles session transitions

## Monitoring

### Check for Auto-Detection
Look for these log messages:
```
🌙 Auto-detected extended hours trading for NVDA
🌙 Auto-detected extended hours for closing AAPL
```

### Verify Order Parameters
When checking order results, look for:
```json
{
  "success": true,
  "order_id": "abc123",
  "symbol": "NVDA",
  "extended_hours": true,  // ✅ Should be true after 4PM
  "status": "filled"        // ✅ Should fill immediately
}
```

## Date
November 3, 2025

## Status
✅ **FIXED** - Extended hours trading now works automatically
