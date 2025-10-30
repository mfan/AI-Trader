# Code Cleanup & Migration Plan: Alpaca MCP Integration

**Goal**: Replace AlphaVantage and Jina with Alpaca MCP Server for unified data and trading.

---

## Benefits of Migration

### Current State (Before)
- **AlphaVantage**: Historical price data (limited, rate-limited, outdated)
- **Jina AI**: Web search for market intelligence (generic, not finance-specific)
- **File-based trading**: Simulation only, no real execution

### Target State (After)
- **Alpaca MCP**: Real-time + historical data, trading execution, all in one
- **Simplified architecture**: One API instead of three
- **Real trading capability**: Paper and live trading support
- **Better data quality**: Professional-grade market data

---

## Migration Strategy

### Phase 1: Update MCP Service Configuration ✅
**Files**: `agent/base_agent/base_agent.py`

Replace MCP config to use Alpaca services:

```python
# OLD Configuration
{
    "math": {...},
    "stock_local": {...},      # AlphaVantage data
    "search": {...},           # Jina search
    "trade": {...}             # File-based simulation
}

# NEW Configuration
{
    "math": {...},
    "alpaca_data": {...},      # Alpaca market data (replaces stock_local)
    "alpaca_trade": {...},     # Alpaca trading (replaces trade + search)
}
```

### Phase 2: Update Agent Prompts ✅
**Files**: `prompts/agent_prompt.py`

Update system prompts to reference new tools:
- `get_bar_for_date` instead of `get_price_local`
- `get_latest_price` instead of web search for prices
- `place_order` instead of file-based buy/sell

### Phase 3: Deprecate Old Services 🔄
**Files**: Mark as deprecated but keep for backward compatibility

- `agent_tools/tool_get_price_local.py` → DEPRECATED
- `agent_tools/tool_jina_search.py` → DEPRECATED
- `agent_tools/tool_trade.py` → DEPRECATED (simulation mode)

### Phase 4: Update Configuration 🔄
**Files**: `configs/default_config.json`, `.env`

Add Alpaca-specific configuration:
- Data source toggle (local vs Alpaca)
- Trading mode (simulation vs paper vs live)

### Phase 5: Update Documentation 🔄
**Files**: All README files

Update guides to reflect new architecture.

---

## Implementation Plan

### Step 1: Update BaseAgent MCP Configuration

**File**: `agent/base_agent/base_agent.py`

Change `_get_default_mcp_config()`:

```python
def _get_default_mcp_config(self) -> Dict[str, Dict[str, Any]]:
    """Get default MCP configuration with Alpaca integration"""
    
    # Check if using Alpaca or legacy mode
    use_alpaca = os.getenv("USE_ALPACA_MCP", "true").lower() == "true"
    
    if use_alpaca:
        # NEW: Alpaca MCP integration
        return {
            "math": {
                "transport": "streamable_http",
                "url": f"http://localhost:{os.getenv('MATH_HTTP_PORT', '8000')}/mcp",
            },
            "alpaca_data": {
                "transport": "streamable_http",
                "url": f"http://localhost:{os.getenv('ALPACA_DATA_HTTP_PORT', '8004')}/mcp",
            },
            "alpaca_trade": {
                "transport": "streamable_http",
                "url": f"http://localhost:{os.getenv('ALPACA_TRADE_HTTP_PORT', '8005')}/mcp",
            },
        }
    else:
        # LEGACY: AlphaVantage + Jina mode
        return {
            "math": {...},
            "stock_local": {...},
            "search": {...},
            "trade": {...},
        }
```

### Step 2: Update Agent Prompts

**File**: `prompts/agent_prompt.py`

Update tool descriptions:

```python
# OLD
"""
Available tools:
- get_price_local: Get historical stock prices from local files
- jina_search: Search the web for market information
- buy/sell: Simulate trades in position.jsonl
"""

# NEW
"""
Available tools:
- get_bar_for_date: Get OHLCV data for any date (real-time if current)
- get_latest_price: Get current market price
- place_order: Execute real trades (paper or live)
- get_positions: View current holdings
"""
```

### Step 3: Create Migration Toggle

**File**: `.env`

Add configuration:

```bash
# Alpaca MCP Integration
USE_ALPACA_MCP="true"              # Use Alpaca (true) or legacy (false)
ALPACA_TRADING_MODE="paper"        # paper, live, or simulation
```

### Step 4: Update Start Script

**File**: `main.sh`

Update to start Alpaca MCP services:

```bash
# OLD
python agent_tools/tool_get_price_local.py &
python agent_tools/tool_jina_search.py &
python agent_tools/tool_trade.py &

# NEW
if [ "$USE_ALPACA_MCP" = "true" ]; then
    ./scripts/start_alpaca_mcp.sh &
    python agent_tools/tool_alpaca_data.py &
    python agent_tools/tool_alpaca_trade.py &
else
    # Legacy mode
    python agent_tools/tool_get_price_local.py &
    python agent_tools/tool_jina_search.py &
    python agent_tools/tool_trade.py &
fi
```

---

## Tool Mapping

### Data Tools

| Legacy Tool | Alpaca MCP Tool | Description |
|------------|----------------|-------------|
| `get_price_local(symbol, date)` | `get_bar_for_date(symbol, date)` | Historical OHLCV data |
| N/A | `get_latest_price(symbol)` | Current market price |
| N/A | `get_latest_quote(symbol)` | Current bid/ask |
| N/A | `get_stock_bars(symbol, start, end)` | Historical bars |

### Trading Tools

| Legacy Tool | Alpaca MCP Tool | Description |
|------------|----------------|-------------|
| `buy(symbol, amount, price, date)` | `place_order(symbol, qty, "buy", "market")` | Market buy |
| `sell(symbol, amount, price, date)` | `place_order(symbol, qty, "sell", "market")` | Market sell |
| `view_positions()` | `get_positions()` | View holdings |
| N/A | `close_position(symbol)` | Close position |
| N/A | `get_account()` | Account info |

### Search Tools

| Legacy Tool | Alpaca MCP Tool | Description |
|------------|----------------|-------------|
| `jina_search(query)` | `get_latest_price(symbol)` | Get current prices directly |
| `jina_search(query)` | `get_snapshot(symbol)` | Complete market data |
| `jina_search(query)` | N/A | General search deprecated |

---

## Backward Compatibility

### Simulation Mode (Legacy)

For users who want to continue using file-based simulation:

```bash
# In .env
USE_ALPACA_MCP="false"
```

This keeps:
- AlphaVantage data from local files
- Jina search
- File-based position tracking

### Hybrid Mode (Recommended)

Use Alpaca for data but keep simulation:

```bash
# In .env
USE_ALPACA_MCP="true"
ALPACA_TRADING_MODE="simulation"  # Use Alpaca data, simulate trades
```

Benefits:
- Real-time market data
- No real trading
- Perfect for testing

---

## Code Changes Required

### 1. BaseAgent Update
**File**: `agent/base_agent/base_agent.py`
**Lines**: ~126-145
**Change**: Update `_get_default_mcp_config()`

### 2. Agent Prompt Update
**File**: `prompts/agent_prompt.py`
**Lines**: Throughout
**Change**: Update tool descriptions

### 3. Configuration Update
**File**: `configs/default_config.json`
**Lines**: Add new section
**Change**: Add Alpaca configuration

### 4. Environment Variables
**File**: `.env.example`
**Lines**: Add new variables
**Change**: Add Alpaca toggle settings

### 5. Startup Script
**File**: `main.sh`
**Lines**: Service startup section
**Change**: Conditional service loading

---

## Testing Plan

### Test 1: Alpaca Mode
```bash
# Configure
USE_ALPACA_MCP="true"
ALPACA_TRADING_MODE="paper"

# Start services
./scripts/start_alpaca_mcp.sh

# Run agent
python main.py
```

**Expected**: Agent uses Alpaca MCP tools, real paper trading

### Test 2: Legacy Mode
```bash
# Configure
USE_ALPACA_MCP="false"

# Start services
python agent_tools/start_mcp_services.py

# Run agent
python main.py
```

**Expected**: Agent uses old tools, file-based simulation

### Test 3: Hybrid Mode
```bash
# Configure
USE_ALPACA_MCP="true"
ALPACA_TRADING_MODE="simulation"

# Run agent
python main.py
```

**Expected**: Agent uses Alpaca data, simulates trades

---

## Deprecation Timeline

### Immediate (Now)
- ✅ Add Alpaca MCP integration
- ✅ Make it default mode
- ⚠️ Mark old tools as deprecated

### Short-term (1-2 weeks)
- Document migration path
- Add warnings in old tools
- Ensure backward compatibility

### Long-term (1-2 months)
- Remove AlphaVantage dependency
- Remove Jina dependency
- Archive deprecated tools

---

## File Cleanup

### Files to Deprecate (Keep for now)
- `agent_tools/tool_get_price_local.py`
- `agent_tools/tool_jina_search.py`
- `agent_tools/tool_trade.py` (file-based)
- `tools/price_tools.py` (AlphaVantage logic)

### Files to Keep
- `agent_tools/tool_alpaca_data.py` (NEW)
- `agent_tools/tool_alpaca_trade.py` (NEW)
- `tools/alpaca_mcp_bridge.py` (NEW)
- `tools/alpaca_data_feed.py` (Direct API access)
- `tools/alpaca_trading.py` (Direct API access)

### Files to Update
- `agent/base_agent/base_agent.py`
- `prompts/agent_prompt.py`
- `configs/default_config.json`
- `.env.example`
- `main.sh`

---

## Benefits Summary

### Technical Benefits
✅ **Unified API**: One service instead of three  
✅ **Real-time Data**: Live market data, not historical files  
✅ **Better Quality**: Professional-grade data from Alpaca  
✅ **Real Trading**: Paper and live trading support  
✅ **Simpler Architecture**: Fewer dependencies  

### Operational Benefits
✅ **Lower Costs**: No AlphaVantage API costs  
✅ **Faster Development**: One API to learn  
✅ **Better Support**: Official Alpaca support  
✅ **More Features**: 60+ tools vs 10  

### User Benefits
✅ **Real Trading**: Move from simulation to real  
✅ **Better Prices**: Real-time vs 15-min delayed  
✅ **More Assets**: Stocks, options, crypto  
✅ **Paper Trading**: Risk-free testing with real data  

---

## Next Steps

1. **Review this plan** - Approve migration strategy
2. **Update BaseAgent** - Implement MCP config changes
3. **Update prompts** - Reflect new tools
4. **Test migration** - Ensure backward compatibility
5. **Update docs** - Reflect new architecture
6. **Deploy** - Roll out Alpaca as default

---

**Status**: 📋 **PLAN READY - AWAITING APPROVAL**  
**Estimated Time**: 2-3 hours implementation  
**Risk Level**: Low (backward compatible)  
**Recommendation**: Proceed with migration ✅
