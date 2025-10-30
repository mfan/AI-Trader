# Quick Start: Alpaca Official MCP Server Integration

This guide helps you quickly integrate Alpaca's official MCP server with AI-Trader in **5 minutes**.

## Prerequisites

- Python 3.10+ installed
- AI-Trader project set up
- Alpaca API keys (from https://app.alpaca.markets)

---

## Step 1: Install Dependencies (2 minutes)

```bash
# 1. Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
exec $SHELL  # Restart terminal

# 2. Install Alpaca MCP Server
pip install alpaca-mcp-server

# 3. Verify installation
alpaca-mcp-server --version
```

**Expected output**: `alpaca-mcp-server, version 1.0.2`

---

## Step 2: Configure API Keys (1 minute)

Add to your `.env` file:

```bash
# Alpaca Official MCP Server
ALPACA_API_KEY="your_alpaca_api_key_here"
ALPACA_SECRET_KEY="your_alpaca_secret_key_here"
ALPACA_PAPER_TRADING="true"
ALPACA_MCP_PORT=8004
```

**Get API keys**: https://app.alpaca.markets/paper/dashboard/overview

---

## Step 3: Start MCP Server (1 minute)

```bash
# Make script executable
chmod +x scripts/start_alpaca_mcp.sh

# Start the server
./scripts/start_alpaca_mcp.sh
```

**Expected output**:
```
🚀 Starting Alpaca Official MCP Server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Configuration:
  • Port: 8004
  • Paper Trading: true
  • API Key: PKXXXXXXXX...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 Starting server...
✅ Server running on port 8004
```

---

## Step 4: Test Integration (1 minute)

In a new terminal, run the test:

```bash
python tools/alpaca_mcp_bridge.py
```

**Expected output**:
```
Testing Alpaca MCP Bridge...
==================================================

1. Testing get_account()...
   ✅ Account: $100,000.00

2. Testing get_positions()...
   ✅ Positions: 0 open

3. Testing get_latest_price('AAPL')...
   ✅ AAPL Price: $175.23

4. Testing get_portfolio_summary()...
   ✅ Portfolio Value: $100,000.00
   ✅ Positions: 0

==================================================
✅ All tests passed!
```

---

## Step 5: Use in AI Agents (Interactive)

### Python Code Example

```python
from tools.alpaca_mcp_bridge import AlpacaMCPBridge

# Initialize bridge
bridge = AlpacaMCPBridge()

# Get account info
account = bridge.get_account()
print(f"Balance: ${account['portfolio_value']}")

# Get current price
price = bridge.get_latest_price("AAPL")
print(f"AAPL: ${price}")

# Place order (paper trading)
order = bridge.buy_market("AAPL", 10)
print(f"Order placed: {order['id']}")

# Check positions
positions = bridge.get_positions()
for pos in positions:
    print(f"{pos['symbol']}: {pos['qty']} shares @ ${pos['avg_entry_price']}")
```

### Natural Language (AI Agent)

Once integrated, your AI agents can execute trades using natural language:

```
User: "What's my account balance?"
Agent: [Calls bridge.get_account()]
       "Your account has $100,000 with $100,000 buying power."

User: "Buy 10 shares of AAPL at market price"
Agent: [Calls bridge.buy_market("AAPL", 10)]
       "Order placed: bought 10 shares of AAPL at $175.23"

User: "Show me all my positions"
Agent: [Calls bridge.get_positions()]
       "You have 1 position: AAPL - 10 shares @ $175.23"
```

---

## What You Get

### 60+ Tools Available

**Trading Operations**:
- `place_order` - Stocks, ETFs, crypto, options
- `cancel_order` / `cancel_all_orders`
- `close_position` / `close_all_positions`
- `get_orders` - Order history

**Market Data**:
- `get_latest_trade` / `get_latest_quote` / `get_latest_bar`
- `get_snapshot` - Complete market data
- `get_bars` - Historical OHLCV data
- `get_trades` - Trade history

**Account Management**:
- `get_account` - Balance, buying power
- `get_positions` - All positions
- `get_position` - Specific position
- `get_account_configurations`

**Advanced Features**:
- Options trading (spreads, straddles, etc.)
- Crypto trading (BTC, ETH, etc.)
- Watchlist management
- Market calendar and corporate actions

---

## Troubleshooting

### "uvx command not found"

```bash
# Install uv
pip install uv
exec $SHELL
```

### "Connection refused to MCP server"

```bash
# Check if server is running
ps aux | grep alpaca-mcp-server

# Restart server
./scripts/start_alpaca_mcp.sh
```

### "Invalid API credentials"

```bash
# Verify .env file
cat .env | grep ALPACA

# Test credentials directly
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"
uvx alpaca-mcp-server serve
```

---

## Next Steps

1. **Integrate with Agents**: Update `agent/base_agent/base_agent.py` to use bridge
2. **Enable Real Trading**: Set `ALPACA_PAPER_TRADING="false"` in `.env`
3. **Add to Startup**: Include in `agent_tools/start_mcp_services.py`
4. **Explore Tools**: See `ALPACA_OFFICIAL_MCP_INTEGRATION.md` for complete tool list

---

## Comparison with Custom Wrapper

| Feature | Official MCP | Custom Wrapper |
|---------|-------------|----------------|
| **Tools** | 60+ tools | ~10 tools |
| **Maintenance** | Alpaca team | You |
| **Options** | ✅ Full support | ❌ Not implemented |
| **Crypto** | ✅ Full support | ❌ Not implemented |
| **Updates** | ✅ Automatic | ❌ Manual |
| **Support** | ✅ Official | ❌ Self-support |

**Recommendation**: Use official MCP server for production trading.

---

## Summary

You've successfully integrated Alpaca's official MCP server! 🎉

- ✅ **60+ Trading Tools** available
- ✅ **Real-time Market Data** access
- ✅ **Natural Language** trading interface
- ✅ **Production Ready** code

**Time to first trade**: 5 minutes ⏱️

For more details, see `ALPACA_OFFICIAL_MCP_INTEGRATION.md`
