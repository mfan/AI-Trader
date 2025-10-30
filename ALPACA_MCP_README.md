# 🎯 Alpaca Official MCP Server - Complete Integration

**Status**: ✅ **READY FOR USE**  
**Integration Date**: October 28, 2025  
**Maintained By**: Alpaca Markets + AI-Trader Team

---

## 📊 What You Get

### Official Alpaca MCP Server
- **60+ Trading Tools** - Complete API coverage
- **Real-time Data** - Live quotes, trades, bars
- **Production Ready** - Battle-tested by thousands
- **Auto Updates** - Always latest features
- **Official Support** - Alpaca team maintains

### AI-Trader Integration
- **Seamless Bridge** - Works with existing code
- **Natural Language** - AI agents understand plain English
- **Dual Mode** - Simulation OR real trading
- **Backward Compatible** - Existing features still work

---

## 🚀 Quick Start (5 Minutes)

### One-Command Installation

```bash
./scripts/install_alpaca_mcp.sh
```

This script will:
1. ✅ Check Python 3.10+ requirement
2. ✅ Set up environment variables
3. ✅ Install uv package manager
4. ✅ Install all dependencies
5. ✅ Install Alpaca MCP server
6. ✅ Create necessary directories

### Manual Installation

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
exec $SHELL

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Alpaca MCP
pip install alpaca-mcp-server

# 4. Configure API keys in .env
# Add: ALPACA_API_KEY, ALPACA_SECRET_KEY
```

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Alpaca API Credentials (REQUIRED)
ALPACA_API_KEY="PK..."              # Your Alpaca API key
ALPACA_SECRET_KEY="..."             # Your Alpaca secret key
ALPACA_PAPER_TRADING="true"         # true = paper, false = live

# MCP Server Configuration
ALPACA_MCP_PORT=8004                # Port for MCP server
```

### Get API Keys

1. Visit https://app.alpaca.markets/paper/dashboard/overview
2. Create free paper trading account
3. Generate API keys
4. Add to `.env` file

---

## 🎮 Usage

### Start the MCP Server

```bash
# Terminal 1: Start Alpaca MCP server
./scripts/start_alpaca_mcp.sh
```

Expected output:
```
🚀 Starting Alpaca Official MCP Server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Configuration:
  • Port: 8004
  • Paper Trading: true
  • API Key: PKXXXXXXXX...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Server running on port 8004
```

### Test the Integration

```bash
# Terminal 2: Test bridge
python tools/alpaca_mcp_bridge.py
```

Expected output:
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
==================================================
✅ All tests passed!
```

### Use in Python Code

```python
from tools.alpaca_mcp_bridge import AlpacaMCPBridge

# Initialize
bridge = AlpacaMCPBridge()

# Get account info
account = bridge.get_account()
print(f"Cash: ${account['cash']}")
print(f"Buying Power: ${account['buying_power']}")

# Get current price
price = bridge.get_latest_price("AAPL")
print(f"AAPL: ${price}")

# Place order
order = bridge.buy_market("AAPL", 10)
print(f"Order ID: {order['id']}")

# Check positions
positions = bridge.get_positions()
for pos in positions:
    print(f"{pos['symbol']}: {pos['qty']} shares")
```

### Use with AI Agents

AI agents can use natural language:

```python
# Agent receives: "Buy 10 shares of AAPL"
# Agent executes:
bridge.buy_market("AAPL", 10)

# Agent receives: "What's my portfolio value?"
# Agent executes:
summary = bridge.get_portfolio_summary()
# Responds: "Your portfolio is worth $125,432.50"
```

---

## 🛠️ Available Tools (60+)

### Trading Operations
```python
# Orders
bridge.place_order(symbol, qty, side, type, ...)
bridge.buy_market(symbol, qty)
bridge.sell_market(symbol, qty)
bridge.buy_limit(symbol, qty, price)
bridge.sell_limit(symbol, qty, price)

# Order Management
bridge.get_orders(status="all")
bridge.cancel_order(order_id)
bridge.cancel_all_orders()

# Positions
bridge.get_positions()
bridge.get_position(symbol)
bridge.close_position(symbol, qty=None)
bridge.close_all_positions()
```

### Market Data
```python
# Real-time
bridge.get_latest_price(symbol)
bridge.get_latest_trade(symbol)
bridge.get_latest_quote(symbol)
bridge.get_latest_bar(symbol)
bridge.get_snapshot(symbol)

# Historical
bridge.get_bars(symbol, start, end, timeframe="1Day")
```

### Account Management
```python
# Account
bridge.get_account()
bridge.get_account_configurations()

# Portfolio
bridge.get_portfolio_summary()
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **ALPACA_MCP_QUICKSTART.md** | 5-minute quick start guide |
| **ALPACA_OFFICIAL_MCP_INTEGRATION.md** | Complete integration guide |
| **ALPACA_MCP_ARCHITECTURE.md** | Technical architecture details |
| **ALPACA_MCP_SUMMARY.md** | Integration summary |
| **This file** | Quick reference |

---

## 🔍 Troubleshooting

### "uvx command not found"

```bash
# Install uv and restart terminal
pip install uv
exec $SHELL
```

### "Connection refused"

```bash
# Check if server is running
ps aux | grep alpaca-mcp-server

# Start server
./scripts/start_alpaca_mcp.sh
```

### "Invalid API credentials"

```bash
# Verify .env file
cat .env | grep ALPACA

# Test manually
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"
uvx alpaca-mcp-server serve
```

### "Import Error: No module named 'alpaca_mcp_server'"

```bash
# Reinstall
pip install alpaca-mcp-server --upgrade
```

---

## 🎯 Integration Modes

### Mode 1: Simulation (Default)
- Uses file-based trading simulation
- No real API calls
- Perfect for testing strategies
- Free, no API keys needed

### Mode 2: Paper Trading (Recommended)
- Real Alpaca API with fake money
- Free $100,000 virtual capital
- Real market data
- Perfect for strategy validation
- Requires Alpaca API keys

### Mode 3: Live Trading (Production)
- Real money, real trading
- Set `ALPACA_PAPER_TRADING="false"`
- **USE WITH CAUTION**
- Requires funded Alpaca account

---

## 📊 Comparison

| Feature | Simulation | Paper Trading | Live Trading |
|---------|-----------|---------------|--------------|
| **Cost** | Free | Free | Real money |
| **API Keys** | Not needed | Required | Required |
| **Market Data** | Local files | Real-time | Real-time |
| **Order Execution** | Simulated | Simulated | Real |
| **Risk** | None | None | High |
| **Best For** | Development | Testing | Production |

---

## 🚦 System Architecture

```
AI Agent (GPT/DeepSeek)
    ↓
LangChain Core
    ↓
AlpacaMCPBridge (HTTP)
    ↓
Alpaca MCP Server (:8004)
    ↓
Alpaca Trading API
    ↓
Real Markets
```

---

## ✅ Checklist

### Installation
- [ ] Python 3.10+ installed
- [ ] uv package manager installed
- [ ] requirements.txt dependencies installed
- [ ] alpaca-mcp-server installed
- [ ] API keys added to .env

### Testing
- [ ] MCP server starts successfully
- [ ] Bridge test passes
- [ ] Can get account info
- [ ] Can get latest price
- [ ] Can place test order

### Integration
- [ ] All MCP services running
- [ ] AI agents can access tools
- [ ] Natural language trading works
- [ ] Position tracking works

---

## 🎓 Learning Resources

### Official Docs
- Alpaca MCP Server: https://github.com/alpacahq/alpaca-mcp-server
- Alpaca API Docs: https://docs.alpaca.markets/
- Model Context Protocol: https://modelcontextprotocol.io/

### AI-Trader Docs
- Main README: `README.md`
- Running Guide: `RUNNING_GUIDE.md`
- Technical Analysis: `Claude.md`

---

## 🆘 Support

### Community Support
- **Alpaca Slack**: https://alpaca.markets/slack
- **Alpaca Forum**: https://forum.alpaca.markets/
- **GitHub Issues**: https://github.com/alpacahq/alpaca-mcp-server/issues

### AI-Trader Support
- Check documentation files
- Review error logs in `logs/`
- Test with `python tools/alpaca_mcp_bridge.py`

---

## 🎉 Success Criteria

You've successfully integrated when:

✅ MCP server starts without errors  
✅ Bridge test passes all checks  
✅ Can get account balance  
✅ Can get real-time prices  
✅ Can place and cancel orders  
✅ AI agents can execute trades  

---

## 📝 Notes

- **Paper Trading**: Default mode, safe for testing
- **Live Trading**: Requires explicit configuration
- **Rate Limits**: Respect Alpaca API rate limits
- **Market Hours**: Some operations only work during market hours
- **Data Plans**: Real-time data requires Alpaca subscription

---

**Created**: October 28, 2025  
**Status**: Production Ready ✅  
**Maintained**: Alpaca Markets + AI-Trader Team  

**Happy Trading! 🚀📈**
