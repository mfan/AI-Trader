# 🎉 Alpaca Trading Integration - Quick Start

## ✅ What's Been Added

### New Files Created:
1. **`tools/alpaca_trading.py`** - Core Alpaca integration module
2. **`agent_tools/tool_alpaca_trade.py`** - MCP service for Alpaca trading
3. **`ALPACA_INTEGRATION.md`** - Complete integration guide

### Updated Files:
1. **`requirements.txt`** - Added `alpaca-py>=0.25.0` and `python-dotenv>=0.19.0`
2. **`.env.example`** - Added Alpaca API configuration template

---

## 🚀 Quick Setup (5 Minutes)

### 1. Get Alpaca API Keys
```
1. Go to: https://alpaca.markets/
2. Sign up (free)
3. Navigate to: Dashboard → API Keys
4. Generate Paper Trading keys
5. Copy API Key and Secret Key
```

### 2. Install Dependencies
```bash
cd /home/mfan/work/aitrader
pip3 install alpaca-py python-dotenv
```

### 3. Configure .env
```bash
# Add to your .env file:
ALPACA_API_KEY="PK..."  # Your paper trading key
ALPACA_SECRET_KEY="..."  # Your secret key  
ALPACA_PAPER_TRADING="true"
```

### 4. Test Connection
```bash
python3 tools/alpaca_trading.py
```

### 5. Start Trading Service
```bash
# Start Alpaca trading MCP service
cd agent_tools
python3 tool_alpaca_trade.py &
```

### 6. Run AI-Trader
```bash
cd ..
python3 main.py
```

---

## 🎯 Key Features

### Real Trading Capabilities
- ✅ Market orders (buy/sell instantly)
- ✅ Limit orders (buy/sell at specific price)
- ✅ Position management (track all holdings)
- ✅ Real-time quotes (live market data)
- ✅ Account management (cash, buying power, equity)
- ✅ Order status tracking (filled, pending, rejected)

### Safety Features
- ✅ Paper trading mode (test with fake money)
- ✅ Position validation (can't sell what you don't own)
- ✅ Buying power checks (can't spend more than you have)
- ✅ Automatic trade logging
- ✅ Error handling and reporting

---

## 📊 Available MCP Tools for AI Agents

Your AI agents can now call these tools:

### Account & Portfolio
- `get_account_info()` - Get cash, buying power, equity
- `get_positions()` - Get all current positions
- `get_position(symbol)` - Get specific position
- `get_portfolio_summary()` - Complete portfolio overview

### Market Data
- `get_stock_price(symbol)` - Get current price for one stock
- `get_stock_prices(symbols)` - Get prices for multiple stocks

### Trading
- `buy(symbol, quantity)` - Buy stocks (market order)
- `sell(symbol, quantity)` - Sell stocks (market order)
- `close_position(symbol)` - Close entire position

---

## 🔄 Migration Path

### Option 1: Use Alpaca for New Runs
- Keep file-based system for backtesting
- Use Alpaca for forward testing/live trading
- Both can coexist

### Option 2: Full Migration
- Replace `tool_trade.py` with `tool_alpaca_trade.py`
- Update MCP service port in configs
- All trading goes through Alpaca

### Option 3: Hybrid
- Use file-based for historical backtests
- Use Alpaca for paper/live trading
- Toggle via configuration

---

## ⚠️ Important Notes

### Paper Trading (Recommended)
- **FREE** simulated trading
- **$100,000** fake starting balance
- **Real** market data and prices
- **Zero** financial risk
- Perfect for testing strategies

### Live Trading (Use Caution!)
- **REAL** money involved
- Can **LOSE** money
- Only use after extensive paper testing
- Requires account funding
- **Start small**

---

## 📖 Documentation

### Full Guides
- **`ALPACA_INTEGRATION.md`** - Complete setup and usage guide
- **`RUNNING_GUIDE.md`** - How to run AI-Trader
- **`Claude.md`** - Deep technical analysis

### Code Documentation
- **`tools/alpaca_trading.py`** - Alpaca client wrapper
- **`agent_tools/tool_alpaca_trade.py`** - MCP trading tools

---

## 🧪 Testing Checklist

Before running with Alpaca:

- [ ] Alpaca account created
- [ ] Paper trading API keys obtained
- [ ] Keys added to `.env` file
- [ ] `alpaca-py` installed
- [ ] Connection tested successfully
- [ ] MCP service starts without errors
- [ ] Test trade executed in paper account
- [ ] Results visible in Alpaca dashboard

---

## 🎓 Example Usage

### Python Script
```python
from tools.alpaca_trading import get_alpaca_client

# Initialize client
client = get_alpaca_client()

# Check account
account = client.get_account()
print(f"Cash: ${account['cash']:,.2f}")

# Get price
price = client.get_latest_price("AAPL")
print(f"AAPL: ${price:.2f}")

# Buy stock
result = client.buy_market("AAPL", 10)
if result['success']:
    print(f"✅ Bought 10 shares of AAPL")
    print(f"Order ID: {result['order_id']}")

# Check position
positions = client.get_positions()
if "AAPL" in positions:
    pos = positions["AAPL"]
    print(f"AAPL Position: {pos['qty']} shares")
    print(f"P&L: ${pos['unrealized_pl']:.2f}")
```

### AI Agent Usage
The AI agent automatically gets these tools through MCP:

```
AI: "I want to buy 100 shares of AAPL"
Tool: buy("AAPL", 100)
Result: Order placed successfully

AI: "Check my positions"
Tool: get_positions()
Result: {"AAPL": {"qty": 100, "unrealized_pl": 125.50, ...}}

AI: "What's the current MSFT price?"
Tool: get_stock_price("MSFT")
Result: {"price": 374.25, ...}
```

---

## 🔧 Troubleshooting

### Can't connect to Alpaca?
```bash
# Verify credentials
python3 -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('Key:', os.getenv('ALPACA_API_KEY'))
"
```

### Service won't start?
```bash
# Check if port is available
lsof -i :8002

# Kill existing process
lsof -ti:8002 | xargs kill -9

# Restart service
python3 agent_tools/tool_alpaca_trade.py
```

### Order failed?
- Check buying power
- Verify symbol is correct
- Check market hours
- Review error message

---

## 💡 Pro Tips

1. **Start Small**: Test with 1-5 shares first
2. **Monitor Dashboard**: Check Alpaca web dashboard for orders
3. **Review Logs**: Check `data/agent_data/*/trades/` for trade logs
4. **Paper Test**: Run for days/weeks in paper mode before live
5. **Set Limits**: Implement position size and count limits

---

## 🎯 Next Steps

1. ✅ Get Alpaca keys → https://alpaca.markets/
2. ✅ Install dependencies → `pip3 install alpaca-py`
3. ✅ Configure `.env` → Add API keys
4. ✅ Test connection → `python3 tools/alpaca_trading.py`
5. ✅ Run first paper trade → Start small!

---

## 📞 Need Help?

- **Alpaca Docs**: https://alpaca.markets/docs/
- **Python SDK**: https://github.com/alpacahq/alpaca-py
- **Forum**: https://forum.alpaca.markets/
- **Support**: support@alpaca.markets

---

**You're ready to trade! Start with paper trading and test thoroughly! 🚀📈**

*Remember: This is powerful technology. Use responsibly and test extensively before any live trading.*
