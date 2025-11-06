# Understanding the 30-Step Limit (max_steps = 30)

## What is max_steps?

`max_steps` is the **maximum number of AI reasoning iterations** allowed in a single trading session/cycle. Currently configured to **30** in `configs/default_config.json`.

## What Happens in Each "Step"?

Each step is an **AI agent reasoning round** in a conversational loop with tool access:

### Step Flow:
```
1. User sends analysis request → AI Agent
2. AI Agent thinks and responds with:
   - Analysis of portfolio
   - Identification of trading opportunities  
   - Tool calls (get_trading_signals, place_order, etc.)
   - Decisions (BUY/SELL/HOLD)
3. Tools execute and return results → AI Agent
4. AI Agent processes tool results
5. Repeat until AI sends <FINISH_SIGNAL> OR max_steps reached
```

### Example of a Step:
```
🔄 Step 5/30
├─ AI analyzes: "META shows RSI oversold at 26.9, should I buy?"
├─ AI calls tool: get_technical_indicators("META")
├─ Tool returns: Technical data for META
├─ AI decides: "BUY 30 shares META at $625"
├─ AI calls tool: place_order("META", 30, "buy", ...)
└─ Tool returns: Order executed successfully
```

## Why 30 Steps?

### Purpose: **Safety Net** for Complex Decision-Making

The 30-step limit ensures:
1. ✅ **AI has enough room** to analyze complex portfolios
2. ✅ **Prevents infinite loops** if AI gets stuck
3. ✅ **Allows multi-tool workflows**:
   - Check portfolio (1-2 steps)
   - Scan opportunities (2-3 steps)
   - Analyze each position (2-3 steps each)
   - Execute trades (1-2 steps per trade)
   - Confirm results (1-2 steps)

### Typical Real Usage:

**Analysis of Nov 5, 2025 logs:**
- **Total trading sessions:** 109 sessions
- **Average steps used:** ~2-5 steps per session
- **Finish signal sent:** Agent completes EARLY (doesn't use all 30)

**Most sessions follow this pattern:**
```
Step 1: Receive portfolio + market scan
Step 2: AI analyzes and makes decision
Step 3: Execute trades (if any)
Step 4: Send <FINISH_SIGNAL>
```

## Should We Reduce to 5-10 Steps?

### Analysis:

**Current Behavior:**
- ✅ Agent typically uses 2-5 steps
- ✅ Agent sends `<FINISH_SIGNAL>` when done (doesn't wait for 30)
- ✅ No wasted computation (stops early)
- ✅ Safety buffer for complex scenarios

**If Reduced to 5-10:**
- ⚠️ **Risk:** May truncate complex analysis
- ⚠️ **Risk:** If agent needs to analyze 8 positions individually, might run out
- ⚠️ **Risk:** Less room for error recovery/retries
- ✅ **Benefit:** Slightly faster timeout if agent gets stuck
- ✅ **Benefit:** Forces more concise decision-making

### Recommendation:

**KEEP at 30** for the following reasons:

1. **No Performance Impact:**
   - Agent stops early with `<FINISH_SIGNAL>`
   - Unused steps don't consume resources
   - No wasted API calls

2. **Safety Buffer:**
   - Complex portfolios may need deeper analysis
   - Multi-position scenarios (8 positions = potential 16+ steps)
   - Allows for thorough technical analysis per symbol

3. **Current Efficiency:**
   - Logs show agent completes in 2-5 steps typically
   - 30-step limit never reached in practice
   - Acts as emergency brake, not normal ceiling

4. **Tool Interaction Overhead:**
   - Each tool call = 2 steps (call + response processing)
   - Portfolio scan can involve 5-10 tool calls
   - Need headroom for complex workflows

### Alternative: **Reduce to 15 Steps**

If you want a middle ground:

**Pros:**
- ✅ Still provides adequate room (7-8 complete analysis cycles)
- ✅ Faster timeout if agent malfunctions
- ✅ Encourages efficient decision-making

**Cons:**
- ⚠️ May truncate deep analysis in volatile markets
- ⚠️ Less room for complex multi-position management

## Actual Trading Session Example

**Real session from Nov 5, 2025:**

```python
# Trading Cycle Started
Step 1: User provides comprehensive analysis:
  - Portfolio summary (8 positions)
  - Market scan results (14 opportunities)
  - Instructions to analyze and trade

Step 2: AI Agent responds:
  "Current portfolio over-leveraged, need to restructure.
   Plan: Exit SQQQ, LCID. Focus on 3-4 core positions.
   <FINISH_SIGNAL>"

Total steps used: 2 out of 30 (93% unused)
```

**Another example with trading:**

```python
Step 1: User provides analysis
Step 2: AI analyzes portfolio
Step 3: AI calls get_trading_signals("NVDA")
Step 4: Tool returns signals for NVDA
Step 5: AI decides to buy NVDA
Step 6: AI calls place_order("NVDA", 20, "buy", ...)
Step 7: Tool confirms order executed
Step 8: AI sends <FINISH_SIGNAL>

Total steps used: 8 out of 30 (73% unused)
```

## Configuration Details

### Current Setting:
```json
// configs/default_config.json
{
  "agent_config": {
    "max_steps": 30,  // ← Maximum AI reasoning iterations
    "max_retries": 3,  // ← API call retries (different)
    "base_delay": 1.0,
    "initial_cash": 10000.0
  }
}
```

### Where It's Used:
```python
# agent/base_agent/base_agent.py
while current_step < self.max_steps:
    current_step += 1
    print(f"🔄 Step {current_step}/{self.max_steps}")
    
    # Call AI agent with current context
    response = await self._ainvoke_with_retry(message)
    
    # Check if agent is done
    if STOP_SIGNAL in agent_response:
        print("✅ Received stop signal, trading session ended")
        break  # Exit early (doesn't use all 30 steps)
```

## Cost Analysis

### DeepSeek API Pricing:
- **Input:** ~$0.14 per million tokens
- **Output:** ~$0.28 per million tokens

### Typical Session:
- **Input tokens:** ~5,000-10,000 (portfolio data + market scan)
- **Output tokens:** ~1,000-2,000 (AI analysis + decisions)
- **Cost per session:** $0.001-$0.003 (less than a penny)

### Impact of max_steps=30 vs max_steps=10:
- **No difference** if agent stops at step 3
- Only matters if agent uses all steps (rare)
- Potential savings: Negligible (<$0.01/day)

## Conclusion

### **Recommendation: KEEP max_steps = 30**

**Reasoning:**
1. ✅ No performance penalty (agent stops early)
2. ✅ Safety buffer for complex scenarios  
3. ✅ Logs show efficient usage (2-5 steps typical)
4. ✅ Emergency brake for runaway loops
5. ✅ Negligible cost difference

### **If You Want to Optimize:**

**Option 1: Reduce to 15 (Conservative)**
- Adequate room for most scenarios
- Faster timeout if issues occur
- Still safe for complex portfolios

**Option 2: Reduce to 10 (Aggressive)**
- Forces very concise decisions
- Risk: May truncate deep analysis
- Best for simple portfolios (1-3 positions)

### **How to Change:**

```bash
# Edit config
nano configs/default_config.json

# Change max_steps value:
{
  "agent_config": {
    "max_steps": 15,  // ← Reduced from 30
    ...
  }
}

# Restart service to apply
sudo systemctl restart active-trader.service
```

---

**Last Analysis:** November 6, 2025  
**Data Source:** Real logs from deepseek-chat-v3.1  
**Sessions Analyzed:** 109 sessions from Nov 5, 2025
