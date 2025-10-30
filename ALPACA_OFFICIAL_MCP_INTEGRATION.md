# Alpaca Official MCP Server Integration Guide

This guide shows how to integrate AI-Trader with Alpaca's official MCP server instead of custom wrappers.

## Overview

Alpaca provides an official Model Context Protocol (MCP) server that offers:
- ✅ **Professional Support**: Maintained by Alpaca team
- ✅ **Complete Feature Set**: All trading, data, and account management tools
- ✅ **Regular Updates**: Always compatible with latest Alpaca API
- ✅ **Production Ready**: Battle-tested by thousands of users
- ✅ **Natural Language Interface**: Designed for AI assistants

**Official Repository**: https://github.com/alpacahq/alpaca-mcp-server

---

## Why Use Official MCP Server?

### Advantages Over Custom Wrappers

| Feature | Official MCP Server | Custom Wrapper |
|---------|-------------------|----------------|
| **Maintenance** | Alpaca team maintains | You maintain |
| **Updates** | Automatic via PyPI | Manual updates |
| **Features** | Complete API coverage | Partial implementation |
| **Support** | Official support channels | Self-support |
| **Testing** | Production-tested | Limited testing |
| **Documentation** | Official docs | Custom docs |

### Features Included

1. **Market Data**
   - Real-time quotes, trades, bars (stocks, crypto, options)
   - Historical data with flexible timeframes
   - Stock snapshots and trade history
   - Option Greeks and implied volatility

2. **Trading Operations**
   - Stocks, ETFs, crypto, options trading
   - Market, limit, stop, stop-limit, trailing-stop orders
   - Single-leg and multi-leg options strategies
   - Position management and liquidation

3. **Account Management**
   - Balance, buying power, account status
   - Open and closed positions
   - Order history and management
   - Watchlist management

4. **Market Information**
   - Market open/close times
   - Market calendar
   - Corporate actions (dividends, splits, etc.)

---

## Installation

### Prerequisites

1. **Python 3.10+** (AI-Trader already requires Python 3.8+)
2. **uv package manager** (recommended by Alpaca)
3. **Alpaca API keys** (paper or live trading)

### Step 1: Install uv Package Manager

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv

# Restart terminal after installation
exec $SHELL
```

### Step 2: Install Alpaca MCP Server

```bash
# Quick installation using uvx (recommended)
uvx alpaca-mcp-server init

# Or install globally
pip install alpaca-mcp-server
```

### Step 3: Verify Installation

```bash
# Check if installed
alpaca-mcp-server --version

# Should output: alpaca-mcp-server, version 1.0.2 (or later)
```

---

## Configuration for AI-Trader

### Option A: Standalone MCP Server (Recommended)

Run Alpaca MCP server as a separate service alongside AI-Trader's existing MCP services.

#### 1. Update `.env` File

Add Alpaca configuration to your `.env`:

```bash
# Alpaca Official MCP Server Configuration
ALPACA_API_KEY="your_alpaca_api_key_here"
ALPACA_SECRET_KEY="your_alpaca_secret_key_here"
ALPACA_PAPER_TRADING="true"  # Use paper trading by default
ALPACA_MCP_PORT=8004         # Port for Alpaca MCP server
```

#### 2. Create Startup Script

Create `start_alpaca_mcp.sh`:

```bash
#!/bin/bash
# Start Alpaca Official MCP Server

# Load environment variables
source .env

# Start Alpaca MCP server
echo "🚀 Starting Alpaca Official MCP Server..."
uvx alpaca-mcp-server serve \
  --port ${ALPACA_MCP_PORT:-8004} \
  --env ALPACA_API_KEY="${ALPACA_API_KEY}" \
  --env ALPACA_SECRET_KEY="${ALPACA_SECRET_KEY}"
```

#### 3. Make Script Executable

```bash
chmod +x start_alpaca_mcp.sh
```

#### 4. Update Service Manager

Modify `agent_tools/start_mcp_services.py` to include Alpaca MCP:

```python
# Add to service configurations
'alpaca_official': {
    'script': '../start_alpaca_mcp.sh',
    'name': 'AlpacaOfficial',
    'port': int(os.getenv('ALPACA_MCP_PORT', '8004'))
}
```

### Option B: Direct Integration with LangChain

Integrate Alpaca MCP tools directly into AI agents.

#### 1. Install MCP Client Library

```bash
pip install mcp
```

#### 2. Create Bridge Module

Create `tools/alpaca_mcp_bridge.py`:

```python
"""
Bridge between AI-Trader agents and Alpaca Official MCP Server
"""
import os
from typing import Dict, Any, List
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class AlpacaMCPBridge:
    """Bridge to Alpaca's official MCP server"""
    
    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.session = None
    
    async def connect(self):
        """Connect to Alpaca MCP server"""
        server_params = StdioServerParameters(
            command="uvx",
            args=["alpaca-mcp-server", "serve"],
            env={
                "ALPACA_API_KEY": self.api_key,
                "ALPACA_SECRET_KEY": self.secret_key
            }
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                return session
    
    async def get_account(self) -> Dict[str, Any]:
        """Get account information"""
        result = await self.session.call_tool("get_account", {})
        return result
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all positions"""
        result = await self.session.call_tool("get_positions", {})
        return result
    
    async def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = "market",
        **kwargs
    ) -> Dict[str, Any]:
        """Place a trading order"""
        params = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": order_type,
            **kwargs
        }
        result = await self.session.call_tool("place_order", params)
        return result
    
    async def get_latest_price(self, symbol: str) -> Dict[str, Any]:
        """Get latest price for symbol"""
        result = await self.session.call_tool("get_latest_trade", {"symbol": symbol})
        return result
```

---

## Usage in AI-Trader

### Updating Agent Configuration

Modify `agent/base_agent/base_agent.py` to use Alpaca MCP tools:

```python
# Add to agent initialization
from tools.alpaca_mcp_bridge import AlpacaMCPBridge

class BaseAgent:
    def __init__(self):
        # ...existing code...
        self.alpaca_bridge = AlpacaMCPBridge()
    
    async def initialize(self):
        """Initialize agent with Alpaca MCP"""
        await self.alpaca_bridge.connect()
        
        # Register Alpaca tools
        self.tools.extend([
            "get_account",
            "get_positions", 
            "place_order",
            "get_latest_price",
            "get_latest_quote",
            "cancel_order",
            "close_position"
        ])
```

### Natural Language Trading Examples

Once integrated, AI agents can execute trades using natural language:

```python
# Example agent prompts that work with Alpaca MCP:

"What's my current account balance and buying power?"
→ Calls get_account tool

"Show me all my open positions"
→ Calls get_positions tool

"Buy 10 shares of AAPL at market price"
→ Calls place_order tool with symbol=AAPL, qty=10, side=buy

"What's the current price of TSLA?"
→ Calls get_latest_price tool with symbol=TSLA

"Place a limit order to sell 5 shares of NVDA at $500"
→ Calls place_order with type=limit, limit_price=500

"Close all my positions in MSFT"
→ Calls close_position tool with symbol=MSFT
```

---

## Available Tools Reference

### Account Management
- `get_account` - Get account balance, buying power, status
- `get_account_configurations` - Get account settings
- `update_account_configurations` - Update account settings

### Position Management
- `get_positions` - Get all open positions
- `get_position` - Get specific position by symbol
- `close_position` - Close position (full or partial)
- `close_all_positions` - Liquidate all positions

### Order Management
- `place_order` - Place stock/ETF/crypto order
- `place_option_order` - Place options order
- `get_orders` - Get order history
- `get_order` - Get specific order details
- `cancel_order` - Cancel specific order
- `cancel_all_orders` - Cancel all open orders

### Market Data
- `get_latest_trade` - Latest trade price
- `get_latest_quote` - Latest bid/ask quote
- `get_latest_bar` - Latest OHLCV bar
- `get_snapshot` - Complete market snapshot
- `get_bars` - Historical price bars
- `get_trades` - Historical trade data

### Options Trading
- `search_option_contracts` - Find option contracts
- `get_option_contract` - Get contract details
- `get_latest_option_quote` - Option quote with Greeks
- `get_option_snapshot` - Complete option data
- `exercise_option` - Exercise option contract

### Watchlist Management
- `create_watchlist` - Create new watchlist
- `get_watchlists` - Get all watchlists
- `add_asset_to_watchlist` - Add symbol to watchlist
- `remove_asset_from_watchlist` - Remove symbol

### Market Information
- `get_market_clock` - Market open/close times
- `get_market_calendar` - Trading calendar
- `get_corporate_actions` - Dividends, splits, etc.

---

## Migration from Custom Wrapper

### Before (Custom Wrapper)
```python
from tools.alpaca_trading import AlpacaTradingClient

client = AlpacaTradingClient()
account = client.get_account()
positions = client.get_positions()
```

### After (Official MCP Server)
```python
from tools.alpaca_mcp_bridge import AlpacaMCPBridge

bridge = AlpacaMCPBridge()
await bridge.connect()
account = await bridge.get_account()
positions = await bridge.get_positions()
```

### Key Differences

1. **Async/Await**: Official MCP uses async/await pattern
2. **Tool-Based**: Functions are exposed as MCP tools
3. **Standardized**: Follows MCP protocol specifications
4. **Natural Language**: Designed for AI assistant integration

---

## Testing the Integration

### Step 1: Test MCP Server Standalone

```bash
# Start Alpaca MCP server manually
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"
uvx alpaca-mcp-server serve
```

### Step 2: Test with AI-Trader

```bash
# Start all services including Alpaca MCP
cd agent_tools
python start_mcp_services.py

# In another terminal, run AI-Trader
python main.py
```

### Step 3: Verify Tools Available

Check that agents can access Alpaca MCP tools:

```python
# In agent code
print("Available tools:", agent.list_tools())
# Should show: get_account, get_positions, place_order, etc.
```

---

## Comparison: Custom vs Official

### When to Use Official MCP Server

✅ **Use Official When:**
- You want production-ready, tested code
- You need full API coverage (options, crypto, etc.)
- You want automatic updates and bug fixes
- You need official support channels
- You're building long-term systems

### When to Keep Custom Wrapper

⚠️ **Keep Custom When:**
- You need specific customizations
- You want synchronous API (not async)
- You have legacy code dependencies
- You need offline/local-only operation

### Hybrid Approach (Recommended)

Use **both** simultaneously:
- **Official MCP** for AI agent interactions (natural language)
- **Custom wrapper** for programmatic trading logic
- Switch between them as needed

---

## Troubleshooting

### Issue: "uvx command not found"

**Solution**: Install uv and restart terminal
```bash
pip install uv
exec $SHELL
```

### Issue: "Connection refused to MCP server"

**Solution**: Check if server is running
```bash
ps aux | grep alpaca-mcp-server
```

### Issue: "Invalid API credentials"

**Solution**: Verify `.env` configuration
```bash
echo $ALPACA_API_KEY
echo $ALPACA_SECRET_KEY
```

### Issue: "Tools not showing in agent"

**Solution**: Check agent tool registration
```python
# Ensure tools are registered in agent initialization
agent.register_mcp_server("alpaca", bridge)
```

---

## Next Steps

1. **Install Official MCP Server**
   ```bash
   uvx alpaca-mcp-server init
   ```

2. **Update Configuration**
   - Add API keys to `.env`
   - Configure MCP port settings

3. **Create Bridge Module**
   - Implement `alpaca_mcp_bridge.py`
   - Connect to official server

4. **Update Agents**
   - Modify agent initialization
   - Register Alpaca MCP tools

5. **Test Integration**
   - Test standalone MCP server
   - Test with AI agents
   - Verify natural language trading

---

## Resources

- **Official Repository**: https://github.com/alpacahq/alpaca-mcp-server
- **Alpaca Documentation**: https://docs.alpaca.markets/
- **MCP Protocol**: https://modelcontextprotocol.io/
- **AI-Trader Documentation**: See `Claude.md` and `ALPACA_INTEGRATION.md`

---

## Summary

The official Alpaca MCP server provides:
- ✅ **60+ Trading Tools** out of the box
- ✅ **Production-Ready** code maintained by Alpaca
- ✅ **Natural Language** interface for AI agents
- ✅ **Complete API Coverage** (stocks, options, crypto)
- ✅ **Regular Updates** via PyPI

**Recommendation**: Migrate to official MCP server for production use while keeping custom wrappers for development/testing.
