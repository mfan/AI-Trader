# 🏦 Alpaca Trading Integration Guide

**Integration Date**: October 28, 2025  
**Status**: Ready for Testing  
**Mode**: Paper Trading (Recommended for testing)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Getting Alpaca API Keys](#getting-alpaca-api-keys)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Migration from File-Based to Alpaca](#migration)
6. [Usage Guide](#usage-guide)
7. [Testing](#testing)
8. [Paper vs Live Trading](#paper-vs-live-trading)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

### What's New

The AI-Trader now integrates with **Alpaca's Trading API** using the official `alpaca-py` SDK. This provides:

- ✅ **Real-time order execution** (market & limit orders)
- ✅ **Actual position management** (no more file simulation)
- ✅ **Live market data** (real-time quotes)
- ✅ **Professional order management** (order status, fills, cancellations)
- ✅ **Paper trading mode** (test with fake money first)
- ✅ **Account management** (cash, buying power, equity tracking)

### Architecture Changes

**Before** (File-based):
```
AI Agent → tool_trade.py → position.jsonl (local file)
```

**After** (Alpaca):
```
AI Agent → tool_alpaca_trade.py → Alpaca API → Real broker
```

---

## 🔑 Getting Alpaca API Keys

### Step 1: Create Alpaca Account

1. **Sign up for Alpaca**:
   - Visit: https://alpaca.markets/
   - Click "Sign Up" (free account)
   - Complete registration

2. **Verify your email** and log in

### Step 2: Get API Keys

1. **Navigate to API Keys**:
   - Dashboard → Settings → API Keys
   - Or direct link: https://app.alpaca.markets/paper/dashboard/overview

2. **Generate Paper Trading Keys** (Recommended for testing):
   - Click "Generate New Key"
   - Name it (e.g., "AI-Trader-Paper")
   - **IMPORTANT**: Copy both keys immediately:
     - **API Key** (starts with `PK...`)
     - **Secret Key** (starts with `...` - shown only once)

3. **Optional: Generate Live Trading Keys** (Only after testing):
   - Switch to Live Trading tab
   - Requires account verification and funding
   - Same process as paper trading keys

### Step 3: Account Types

| Account Type | Purpose | Risk | Cost |
|--------------|---------|------|------|
| **Paper Trading** | Testing with fake money | None | Free |
| **Live Trading** | Real money trading | Real losses possible | Free (commission-free) |

⚠️ **ALWAYS start with Paper Trading!**

---

## 🔧 Installation

### Step 1: Install Dependencies

```bash
cd /home/mfan/work/aitrader

# Install alpaca-py SDK
pip3 install alpaca-py

# Or install all dependencies
pip3 install -r requirements.txt
```

**Verify installation:**
```bash
python3 -c "from alpaca.trading.client import TradingClient; print('✅ Alpaca-py installed')"
```

### Step 2: Verify Installation

```bash
pip3 list | grep alpaca
# Should show: alpaca-py  0.25.0 (or higher)
```

---

## ⚙️ Configuration

### Step 1: Update `.env` File

Add your Alpaca credentials to `.env`:

```bash
cd /home/mfan/work/aitrader
nano .env  # or use your preferred editor
```

**Add these lines:**
```bash
# Alpaca Trading API Configuration
ALPACA_API_KEY="PK..."  # Your paper trading API key
ALPACA_SECRET_KEY="..."  # Your paper trading secret key
ALPACA_PAPER_TRADING="true"  # Use paper trading
ALPACA_BASE_URL=""  # Leave empty for default
```

**Example `.env` with Alpaca:**
```bash
# AI Model APIs
OPENAI_API_BASE="https://api.openai.com/v1"
OPENAI_API_KEY="sk-..."

# Data Sources
ALPHAADVANTAGE_API_KEY="..."
JINA_API_KEY="jina_..."

# Alpaca Trading (NEW!)
ALPACA_API_KEY="PKXXXXXXXXXXXXXXXX"
ALPACA_SECRET_KEY="XXXXXXXXXXXXXXXXXXXXXXXX"
ALPACA_PAPER_TRADING="true"
ALPACA_BASE_URL=""

# Service Ports
MATH_HTTP_PORT=8000
SEARCH_HTTP_PORT=8001
TRADE_HTTP_PORT=8002
GETPRICE_HTTP_PORT=8003

# System
AGENT_MAX_STEP=30
RUNTIME_ENV_PATH="/home/mfan/work/aitrader/runtime_env.json"
```

### Step 2: Test Alpaca Connection

```bash
cd /home/mfan/work/aitrader

# Test the Alpaca trading client
python3 tools/alpaca_trading.py
```

**Expected output:**
```
🧪 Testing Alpaca Trading Client...
✅ Alpaca client initialized (PAPER trading)

📊 Account Info:
  cash: 100000.0
  buying_power: 200000.0
  equity: 100000.0
  portfolio_value: 100000.0
  pattern_day_trader: False
  trading_blocked: False
  account_blocked: False

📈 Current Positions:
  No open positions

💰 Latest Prices:
  AAPL: $178.25
  MSFT: $374.50
  GOOGL: $139.75

✅ Alpaca client test completed successfully!
```

If you see errors, check:
- API keys are correct
- `.env` file is loaded
- Internet connection is active

---

## 🔄 Migration from File-Based to Alpaca

### Option 1: Use Alpaca for New Runs (Recommended)

Keep both systems and choose which to use:

**Using Alpaca Trading:**
```bash
# Start Alpaca trading service
cd /home/mfan/work/aitrader/agent_tools
python3 tool_alpaca_trade.py &

# Run main script (will use Alpaca if service is running)
cd ..
python3 main.py
```

**Using File-Based Trading:**
```bash
# Start original trading service
cd /home/mfan/work/aitrader/agent_tools
python3 tool_trade.py &

# Run main script
cd ..
python3 main.py
```

### Option 2: Update MCP Configuration

Modify your BaseAgent to use Alpaca service:

Edit `agent/base_agent/base_agent.py`:

```python
def _get_default_mcp_config(self) -> Dict[str, Dict[str, Any]]:
    """Get default MCP configuration"""
    return {
        "math": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('MATH_HTTP_PORT', '8000')}/mcp",
        },
        "stock_local": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('GETPRICE_HTTP_PORT', '8003')}/mcp",
        },
        "search": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('SEARCH_HTTP_PORT', '8001')}/mcp",
        },
        # NEW: Use Alpaca trading instead of file-based
        "trade": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('TRADE_HTTP_PORT', '8002')}/mcp",
        },
    }
```

### Option 3: Hybrid Approach

Use Alpaca for real trading, file-based for backtesting:

```python
# In your config
{
  "use_alpaca_trading": true,  # Toggle between systems
  "backtest_mode": false
}
```

---

## 📖 Usage Guide

### Basic Trading Operations

#### 1. Check Account Status

```python
from tools.alpaca_trading import get_alpaca_client

client = get_alpaca_client()
account = client.get_account()

print(f"Cash: ${account['cash']:.2f}")
print(f"Buying Power: ${account['buying_power']:.2f}")
print(f"Equity: ${account['equity']:.2f}")
```

#### 2. Get Current Positions

```python
positions = client.get_positions()

for symbol, pos in positions.items():
    print(f"{symbol}: {pos['qty']} shares @ ${pos['avg_entry_price']:.2f}")
    print(f"  P&L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_plpc']*100:.2f}%)")
```

#### 3. Buy Stocks

```python
# Market order
result = client.buy_market("AAPL", 10)
if result['success']:
    print(f"Order placed: {result['order_id']}")
else:
    print(f"Error: {result['error']}")
```

#### 4. Sell Stocks

```python
# Market order
result = client.sell_market("AAPL", 5)
if result['success']:
    print(f"Sell order placed: {result['order_id']}")
```

#### 5. Get Stock Prices

```python
# Single stock
price = client.get_latest_price("AAPL")
print(f"AAPL: ${price:.2f}")

# Multiple stocks
prices = client.get_latest_prices(["AAPL", "MSFT", "GOOGL"])
for symbol, price in prices.items():
    print(f"{symbol}: ${price:.2f}")
```

#### 6. Portfolio Summary

```python
summary = client.get_portfolio_summary()

print("Portfolio Summary:")
print(f"  Total Equity: ${summary['summary']['equity']:.2f}")
print(f"  Cash: ${summary['summary']['cash']:.2f}")
print(f"  Positions: {summary['summary']['total_positions']}")
print(f"  Unrealized P&L: ${summary['summary']['total_unrealized_pl']:.2f}")
```

### MCP Tool Integration

When using the MCP service (`tool_alpaca_trade.py`), AI agents can call:

```python
# Available tools for AI agents:
- get_account_info()
- get_positions()
- get_position(symbol)
- get_stock_price(symbol)
- get_stock_prices(symbols)
- buy(symbol, quantity)
- sell(symbol, quantity)
- close_position(symbol)
- get_portfolio_summary()
```

---

## 🧪 Testing

### Step 1: Test Alpaca Client

```bash
cd /home/mfan/work/aitrader

# Run the test script
python3 tools/alpaca_trading.py
```

### Step 2: Test MCP Service

```bash
# Terminal 1: Start the service
cd /home/mfan/work/aitrader/agent_tools
python3 tool_alpaca_trade.py

# Terminal 2: Test with Python
python3 << EOF
import requests
import json

# Test health check
response = requests.get("http://localhost:8002/health")
print(f"Service status: {response.status_code}")

# Test getting account info
# (Requires proper MCP client setup)
EOF
```

### Step 3: Test with AI Agent

Create a test configuration:

```json
{
  "agent_type": "BaseAgent",
  "date_range": {
    "init_date": "2025-10-28",
    "end_date": "2025-10-28"
  },
  "models": [
    {
      "name": "gpt-5-alpaca-test",
      "basemodel": "openai/gpt-5",
      "signature": "gpt-5-alpaca-test",
      "enabled": true
    }
  ],
  "agent_config": {
    "max_steps": 10,
    "initial_cash": 100000.0
  }
}
```

Run test:
```bash
python3 main.py configs/alpaca_test_config.json
```

---

## 📊 Paper vs Live Trading

### Paper Trading (Recommended)

**What is it?**
- Simulated trading with fake money
- Real market data and prices
- No financial risk
- Perfect for testing strategies

**When to use:**
- ✅ Testing new strategies
- ✅ Developing AI trading agents
- ✅ Learning the platform
- ✅ Debugging your code

**How to enable:**
```bash
ALPACA_PAPER_TRADING="true"  # In .env
```

**Account details:**
- Starting balance: $100,000 (fake)
- Resets periodically
- No real money involved

### Live Trading (Use with Caution!)

**What is it?**
- Real trading with real money
- Actual stock purchases/sales
- Real financial risk

**When to use:**
- ⚠️ Only after extensive paper trading
- ⚠️ When strategy is proven profitable
- ⚠️ With money you can afford to lose
- ⚠️ With proper risk management

**How to enable:**
```bash
ALPACA_PAPER_TRADING="false"  # In .env
```

**Requirements:**
- Account verification
- Bank account linked
- Funds deposited
- Understanding of risks

**⚠️ WARNING:**
- You can lose money
- Markets are unpredictable
- AI strategies may fail
- Start small and test thoroughly

---

## 🐛 Troubleshooting

### Issue 1: "Alpaca client not initialized"

**Error:**
```
⚠️ Warning: Alpaca client not initialized: Alpaca API credentials not found
```

**Solution:**
```bash
# Check .env file
cat .env | grep ALPACA

# Verify keys are set
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('API Key:', os.getenv('ALPACA_API_KEY'))
print('Secret Key:', os.getenv('ALPACA_SECRET_KEY')[:10] + '...')
"
```

### Issue 2: "Authentication failed"

**Error:**
```
❌ Error: 401 Unauthorized
```

**Solution:**
- Verify API keys are correct
- Check if keys are for paper/live (must match ALPACA_PAPER_TRADING setting)
- Regenerate keys if necessary

### Issue 3: "Insufficient buying power"

**Error:**
```
Insufficient buying power
```

**Solution:**
```python
# Check account
client = get_alpaca_client()
account = client.get_account()
print(f"Buying power: ${account['buying_power']}")

# Paper trading: Account may have been reset
# Live trading: Deposit more funds
```

### Issue 4: "Symbol not found"

**Error:**
```
Could not get price for SYMBOL
```

**Solution:**
- Check symbol is correct (e.g., "AAPL" not "Apple")
- Verify stock is traded on supported exchanges
- Check market hours (some data unavailable when market is closed)

### Issue 5: "Order rejected"

**Common reasons:**
- Insufficient funds
- Symbol not tradable
- Market closed
- Position limits exceeded

**Check order status:**
```python
order = client.get_order(order_id)
print(order['status'])
```

---

## 📈 Best Practices

### 1. Always Start with Paper Trading

```python
# In .env
ALPACA_PAPER_TRADING="true"
```

### 2. Implement Position Limits

```python
# In your agent logic
MAX_POSITION_SIZE = 1000  # Maximum shares per position
MAX_POSITIONS = 10  # Maximum number of positions
```

### 3. Use Stop Losses

```python
# Example: Close position if down 5%
if position['unrealized_plpc'] < -0.05:
    client.close_position(symbol)
```

### 4. Log All Trades

The system automatically logs to:
```
data/agent_data/{model}/trades/{date}_trades.jsonl
```

### 5. Monitor Account Status

```python
# Regular account checks
account = client.get_account()
if account['trading_blocked']:
    print("⚠️ Trading blocked!")
```

### 6. Handle Errors Gracefully

```python
try:
    result = client.buy_market(symbol, qty)
    if not result['success']:
        print(f"Order failed: {result['error']}")
except Exception as e:
    print(f"Error: {e}")
```

---

## 🚀 Next Steps

1. **Get Alpaca API keys** (paper trading)
2. **Install alpaca-py**: `pip3 install alpaca-py`
3. **Configure `.env`** with API keys
4. **Test connection**: `python3 tools/alpaca_trading.py`
5. **Run test trade** with one model
6. **Monitor results** in Alpaca dashboard
7. **Expand to multiple models** when comfortable
8. **Consider live trading** only after extensive testing

---

## 📞 Support & Resources

### Alpaca Resources
- **Documentation**: https://alpaca.markets/docs/
- **API Reference**: https://alpaca.markets/docs/api-references/trading-api/
- **Python SDK**: https://github.com/alpacahq/alpaca-py
- **Community**: https://forum.alpaca.markets/

### AI-Trader Resources
- **Main README**: `README.md`
- **Running Guide**: `RUNNING_GUIDE.md`
- **Deep Analysis**: `Claude.md`

### Getting Help
- Check Alpaca dashboard for order status
- Review trade logs in `data/agent_data/*/trades/`
- Monitor MCP service logs in `logs/`

---

**Integration Complete! Ready for Paper Trading! 📈🤖**

*Remember: Always test thoroughly in paper trading before considering live trading with real money.*

---

**Last Updated**: October 28, 2025  
**Status**: ✅ Ready for Testing  
**Next Milestone**: First successful paper trade!
