# Alpaca Official MCP Server - Architecture & Integration

This document explains the technical architecture of integrating Alpaca's official MCP server with AI-Trader.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     AI-Trader System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────┐           ┌──────────────────┐         │
│  │  AI Agents     │◄─────────►│  LangChain Core  │         │
│  │  (GPT, DeepSeek)│          │                  │         │
│  └────────────────┘           └──────────────────┘         │
│          │                            │                     │
│          │                            │                     │
│          ▼                            ▼                     │
│  ┌────────────────────────────────────────────┐            │
│  │      MCP Tools Adapter Layer               │            │
│  │  (langchain-mcp-adapters)                  │            │
│  └────────────────────────────────────────────┘            │
│          │                                                  │
│          ├──────────┬──────────┬─────────┬────────┐        │
│          ▼          ▼          ▼         ▼        ▼        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────┐│
│  │  Math   │ │ Search  │ │  Trade  │ │  Price  │ │Alpaca││
│  │  Tools  │ │  Tools  │ │  Tools  │ │  Tools  │ │ MCP  ││
│  │  :8000  │ │  :8001  │ │  :8002  │ │  :8003  │ │ :8004││
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────┘│
│                                                      │      │
└──────────────────────────────────────────────────────│──────┘
                                                       │
                                                       ▼
                           ┌───────────────────────────────────┐
                           │  Alpaca Official MCP Server       │
                           │  (alpaca-mcp-server)              │
                           ├───────────────────────────────────┤
                           │  • 60+ Trading Tools              │
                           │  • Real-time Market Data          │
                           │  • Account Management             │
                           │  • Options & Crypto Support       │
                           └───────────────────────────────────┘
                                           │
                                           ▼
                           ┌───────────────────────────────────┐
                           │  Alpaca Trading API               │
                           │  (api.alpaca.markets)             │
                           ├───────────────────────────────────┤
                           │  • Paper Trading                  │
                           │  • Live Trading                   │
                           │  • Market Data Feed               │
                           └───────────────────────────────────┘
```

## Component Details

### 1. Alpaca Official MCP Server (Port 8004)

**What it is**: Official Alpaca implementation of Model Context Protocol
**Maintained by**: Alpaca Markets team
**Version**: 1.0.2+

**Key Features**:
- 60+ pre-built trading and data tools
- Production-tested and maintained
- Full API coverage (stocks, options, crypto)
- Natural language interface optimized for AI

**Tools Provided** (categories):

1. **Account Tools** (4 tools)
   - `get_account` - Account info and balances
   - `get_account_configurations` - Account settings
   - `update_account_configurations` - Modify settings
   - `get_account_activities` - Account activity history

2. **Position Tools** (4 tools)
   - `get_positions` - All open positions
   - `get_position` - Specific position details
   - `close_position` - Close position (full/partial)
   - `close_all_positions` - Liquidate everything

3. **Order Tools** (8 tools)
   - `place_order` - Stock/ETF orders
   - `place_option_order` - Option orders
   - `place_crypto_order` - Crypto orders
   - `get_orders` - Order history
   - `get_order` - Single order details
   - `cancel_order` - Cancel specific order
   - `cancel_all_orders` - Cancel all orders
   - `replace_order` - Modify existing order

4. **Market Data Tools** (12 tools)
   - `get_latest_trade` - Last trade price
   - `get_latest_quote` - Current bid/ask
   - `get_latest_bar` - Latest OHLCV bar
   - `get_snapshot` - Complete market snapshot
   - `get_bars` - Historical bars
   - `get_trades` - Historical trades
   - `get_quotes` - Historical quotes
   - `get_latest_crypto_trade` - Crypto trade
   - `get_latest_crypto_quote` - Crypto quote
   - `get_latest_crypto_bar` - Crypto bar
   - `get_crypto_snapshot` - Crypto snapshot
   - `get_crypto_bars` - Crypto history

5. **Options Tools** (6 tools)
   - `search_option_contracts` - Find contracts
   - `get_option_contract` - Contract details
   - `get_latest_option_trade` - Option trade
   - `get_latest_option_quote` - Option quote with Greeks
   - `get_option_snapshot` - Complete option data
   - `exercise_option` - Exercise contract

6. **Watchlist Tools** (6 tools)
   - `create_watchlist` - New watchlist
   - `get_watchlists` - All watchlists
   - `get_watchlist` - Specific watchlist
   - `update_watchlist` - Modify watchlist
   - `add_asset_to_watchlist` - Add symbol
   - `remove_asset_from_watchlist` - Remove symbol

7. **Market Info Tools** (5 tools)
   - `get_market_clock` - Market hours
   - `get_market_calendar` - Trading calendar
   - `get_corporate_actions` - Dividends, splits
   - `search_assets` - Find tradable assets
   - `get_asset` - Asset details

8. **News Tools** (1 tool)
   - `get_news` - Market news and sentiment

### 2. AlpacaMCPBridge (tools/alpaca_mcp_bridge.py)

**What it is**: Python wrapper that provides synchronous interface to Alpaca MCP server
**Purpose**: Make official MCP tools easy to use in existing AI-Trader code

**Key Methods**:

```python
# Account Management
bridge.get_account() → Dict[account_info]
bridge.get_account_configurations() → Dict[settings]

# Position Management
bridge.get_positions() → List[positions]
bridge.get_position(symbol) → Dict[position]
bridge.close_position(symbol, qty, percentage) → Dict[order]
bridge.close_all_positions(cancel_orders) → List[orders]

# Order Management
bridge.place_order(symbol, qty, side, type, ...) → Dict[order]
bridge.get_orders(status, limit) → List[orders]
bridge.cancel_order(order_id) → Dict[confirmation]
bridge.cancel_all_orders() → List[cancelled]

# Market Data
bridge.get_latest_trade(symbol) → Dict[trade]
bridge.get_latest_quote(symbol) → Dict[quote]
bridge.get_latest_bar(symbol) → Dict[bar]
bridge.get_snapshot(symbol) → Dict[snapshot]
bridge.get_bars(symbol, start, end, timeframe) → List[bars]

# Convenience Methods (backward compatible)
bridge.get_latest_price(symbol) → float
bridge.buy_market(symbol, qty) → Dict[order]
bridge.sell_market(symbol, qty) → Dict[order]
bridge.buy_limit(symbol, qty, price) → Dict[order]
bridge.sell_limit(symbol, qty, price) → Dict[order]
bridge.get_portfolio_summary() → Dict[summary]
```

**Bridge Implementation**:
```python
class AlpacaMCPBridge:
    def __init__(self, port=8004):
        self.base_url = f"http://localhost:{port}"
    
    def _call_tool(self, tool_name, arguments):
        # Make HTTP request to MCP server
        response = requests.post(
            f"{self.base_url}/tools/{tool_name}",
            json={"arguments": arguments}
        )
        return response.json()
    
    def get_account(self):
        return self._call_tool("get_account", {})
```

### 3. Integration Points

#### A. Direct Agent Integration

AI agents can call bridge methods directly:

```python
from tools.alpaca_mcp_bridge import AlpacaMCPBridge

class TradingAgent:
    def __init__(self):
        self.alpaca = AlpacaMCPBridge()
    
    def execute_trade(self, symbol, quantity):
        # Check account
        account = self.alpaca.get_account()
        buying_power = account['buying_power']
        
        # Get price
        price = self.alpaca.get_latest_price(symbol)
        cost = price * quantity
        
        # Execute if affordable
        if cost <= buying_power:
            order = self.alpaca.buy_market(symbol, quantity)
            return order
```

#### B. LangChain Tool Integration

Register MCP tools as LangChain tools:

```python
from langchain_mcp_adapters import MCPToolAdapter

# Create adapter for Alpaca MCP server
alpaca_adapter = MCPToolAdapter(
    server_url="http://localhost:8004",
    tools=[
        "get_account",
        "get_positions", 
        "place_order",
        "get_latest_price"
    ]
)

# Register with agent
agent.tools.extend(alpaca_adapter.get_tools())
```

#### C. Natural Language Interface

AI agents understand natural language commands:

```python
User: "Buy 100 shares of AAPL"
Agent: [Parses intent → calls bridge.buy_market("AAPL", 100)]
Response: "Executed: bought 100 shares of AAPL at $175.23"

User: "What's my portfolio worth?"
Agent: [Calls bridge.get_portfolio_summary()]
Response: "Portfolio value: $125,432.50 (3 positions)"

User: "Show me my TSLA position"
Agent: [Calls bridge.get_position("TSLA")]
Response: "TSLA: 50 shares @ avg $245.00, current $250.00 (+$250 unrealized)"
```

## Data Flow Example

### Example: Placing a Market Order

```
1. User Input (Natural Language)
   "Buy 10 shares of AAPL at market price"
                    ↓
2. AI Agent (GPT/DeepSeek)
   Parses intent: {action: "buy", symbol: "AAPL", qty: 10, type: "market"}
                    ↓
3. LangChain Tool Selection
   Selects: alpaca_place_order tool
                    ↓
4. AlpacaMCPBridge.place_order()
   bridge.place_order("AAPL", 10, "buy", "market")
                    ↓
5. HTTP Request to MCP Server
   POST http://localhost:8004/tools/place_order
   {"arguments": {"symbol": "AAPL", "qty": 10, "side": "buy", "type": "market"}}
                    ↓
6. Alpaca MCP Server
   Validates request, calls Alpaca API
                    ↓
7. Alpaca Trading API
   Executes order on paper/live account
                    ↓
8. Response Chain (bubbles back up)
   API → MCP → Bridge → Agent → User
   "Order placed: 10 shares of AAPL @ $175.23"
```

## Communication Protocols

### HTTP Transport (Used by AI-Trader)

```
Client (Bridge) ←→ MCP Server (HTTP REST API)

Request:
POST /tools/{tool_name}
Content-Type: application/json
{
  "arguments": {
    "symbol": "AAPL",
    "qty": 10
  }
}

Response:
{
  "result": {
    "id": "order-123",
    "symbol": "AAPL",
    "qty": 10,
    "filled_avg_price": 175.23
  }
}
```

### Standard I/O Transport (Alternative)

Used by Claude Desktop, Cursor, VS Code:

```
Client ←→ MCP Server (stdio)

Messages via stdin/stdout using JSON-RPC protocol
Suitable for IDE integrations
Not used by AI-Trader (uses HTTP)
```

## Configuration Management

### Environment Variables (.env)

```bash
# Alpaca API Credentials
ALPACA_API_KEY="PKXXXXXXXX"           # Required
ALPACA_SECRET_KEY="XXXXXXXX"          # Required
ALPACA_PAPER_TRADING="true"           # Optional (default: true)

# MCP Server Configuration  
ALPACA_MCP_PORT=8004                  # Port for MCP server
ALPACA_BASE_URL=""                    # Optional override
```

### Runtime Configuration

MCP server started with environment variables:

```bash
ALPACA_API_KEY="$ALPACA_API_KEY" \
ALPACA_SECRET_KEY="$ALPACA_SECRET_KEY" \
uvx alpaca-mcp-server serve --port 8004
```

## Error Handling

### Connection Errors

```python
try:
    bridge = AlpacaMCPBridge()
    account = bridge.get_account()
except ConnectionError:
    print("MCP server not running. Start with: ./scripts/start_alpaca_mcp.sh")
```

### API Errors

```python
try:
    order = bridge.place_order("AAPL", 1000000, "buy", "market")
except Exception as e:
    # Handle insufficient buying power, invalid symbols, etc.
    print(f"Order failed: {e}")
```

### Graceful Degradation

AI-Trader can fall back to file-based simulation if MCP server unavailable:

```python
try:
    price = bridge.get_latest_price(symbol)
except ConnectionError:
    # Fall back to local data
    price = get_price_from_local_file(symbol, date)
```

## Performance Considerations

### Latency

- **Local HTTP**: <10ms (MCP server on localhost)
- **Alpaca API**: 50-200ms (network request)
- **Total**: ~100-300ms per tool call

### Caching

Bridge can implement caching for frequently accessed data:

```python
class AlpacaMCPBridge:
    def __init__(self):
        self._price_cache = {}
        self._cache_ttl = 1  # 1 second
    
    def get_latest_price(self, symbol):
        # Check cache first
        if symbol in self._price_cache:
            cached_time, price = self._price_cache[symbol]
            if time.time() - cached_time < self._cache_ttl:
                return price
        
        # Fetch from API
        price = self._call_tool("get_latest_trade", {"symbol": symbol})
        self._price_cache[symbol] = (time.time(), price)
        return price
```

### Batch Operations

Use batch tools when available:

```python
# Inefficient: Multiple calls
prices = [bridge.get_latest_price(sym) for sym in symbols]

# Efficient: Single batch call
snapshots = bridge._call_tool("get_snapshots", {"symbols": symbols})
prices = [s["latest_trade"]["price"] for s in snapshots]
```

## Security

### API Key Protection

- Keys stored in `.env` file (gitignored)
- Never logged or exposed in responses
- MCP server process has exclusive access

### Network Security

- MCP server binds to localhost only (not exposed externally)
- HTTP transport without authentication (local only)
- Production: Use TLS/authentication for remote deployments

### Trade Authorization

- All trades require valid API credentials
- Paper trading enabled by default
- Explicit configuration required for live trading

## Monitoring & Debugging

### Server Logs

```bash
# View real-time logs
tail -f logs/alpaca_mcp.log

# Check for errors
grep ERROR logs/alpaca_mcp.log
```

### Bridge Debugging

```python
# Enable debug mode
import logging
logging.basicConfig(level=logging.DEBUG)

bridge = AlpacaMCPBridge()
account = bridge.get_account()
# Logs all HTTP requests/responses
```

### Tool Testing

```bash
# Test individual tools
python tools/alpaca_mcp_bridge.py

# Output:
# 1. Testing get_account()... ✅
# 2. Testing get_positions()... ✅  
# 3. Testing get_latest_price('AAPL')... ✅
```

## Summary

The Alpaca official MCP server integration provides:

- ✅ **Production-Ready**: Battle-tested by thousands of users
- ✅ **Feature-Complete**: 60+ tools covering all trading operations
- ✅ **Maintainable**: Official support and automatic updates
- ✅ **Flexible**: Works with natural language and programmatic interfaces
- ✅ **Secure**: API keys protected, localhost-only by default

**Best for**: Production trading systems, long-term projects, teams wanting official support

**Alternative**: Custom wrappers for specific use cases, offline operation, or legacy code compatibility
