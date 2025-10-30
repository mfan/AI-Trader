# 🚀 Quick Start: Portfolio Management Mode

**Ready to use?** Follow these steps to run your AI portfolio manager.

---

## 📋 Prerequisites

✅ **Already completed** (from previous setup):
- Python 3.8+ installed
- Alpaca paper trading account created
- API keys configured in `.env`
- Dependencies installed (`pip install -r requirements.txt`)
- MCP services verified

---

## 🎯 Running Your AI Portfolio Manager

### Step 1: Start MCP Services

```bash
python agent_tools/start_mcp_services.py
```

**Expected output:**
```
🚀 Starting AI-Trader MCP Services...
✅ JinaSearch Service started (Port 8001)
✅ AlpacaData Service started (Port 8004)
✅ AlpacaTrade Service started (Port 8005)
📊 Total: 19 MCP tools available
```

### Step 2: Run the Trading Agent

```bash
python main.py
```

The agent will automatically:
1. ✅ **Review portfolio** - Check all existing positions
2. ✅ **Check news** - Get latest company news for each position
3. ✅ **Analyze positions** - Evaluate profit/loss, position size, trends
4. ✅ **Make decisions** - HOLD, ADD, TRIM, or EXIT each position
5. ✅ **Find opportunities** - Look for new stocks with positive catalysts
6. ✅ **Execute trades** - Take profits, cut losses, buy new positions
7. ✅ **Verify results** - Check final portfolio state

---

## 🎬 What to Expect

### First Run (No Existing Positions)

```
🔍 Phase 1: Portfolio Review
✅ get_portfolio_summary() - $10,000 cash, no positions
✅ get_account() - $10,000 buying power available

📈 Phase 2: Find Opportunities
🔎 search_news("best performing stocks today")
📰 get_company_info("NVDA") - Positive earnings beat
💰 get_latest_price("NVDA") - $850.00

💵 Phase 3: Execute Trades
✅ Buy 5 NVDA shares @ $850 (5% of portfolio)
✅ Buy 10 AAPL shares @ $180 (10% of portfolio)

📊 Phase 4: Final Check
✅ Portfolio value: $10,000
✅ Positions: 2 (NVDA, AAPL)
✅ Cash remaining: $5,750
```

### Subsequent Runs (With Existing Positions)

```
🔍 Phase 1: Portfolio Review
✅ get_portfolio_summary()
   - NVDA: +35% gain, 18% of portfolio
   - AAPL: +12% gain, 15% of portfolio
   - TSLA: -8% loss, 10% of portfolio

📰 Phase 1.5: Check News
✅ get_company_info("NVDA") - Positive news
✅ get_company_info("AAPL") - Neutral
✅ get_company_info("TSLA") - Negative regulatory concerns

💡 Phase 2: Position Decisions
🟢 NVDA: UP 35% → TAKE 50% PROFITS (lock in gains)
🟢 AAPL: UP 12% → HOLD (let it run)
🔴 TSLA: DOWN 8% + negative news → EXIT (cut loss)

💵 Phase 3: Execute Trades
✅ close_position("NVDA", percentage=50) - Take half off
✅ close_position("TSLA") - Full exit
✅ place_order("META", 8, "buy", "market") - New position

📊 Phase 4: Final Check
✅ Portfolio value: $12,500
✅ Positions: 3 (NVDA 50%, AAPL, META)
✅ Total return: +25%
```

---

## 🛡️ Safety Features (Built-In)

### Automatic Risk Management

The AI agent **automatically enforces** these rules:

**Position Sizing:**
- ✅ No position exceeds 20% of portfolio
- ✅ New positions limited to 5-10% of portfolio
- ✅ Maintains 5-10 positions for diversification

**Profit Taking:**
- ✅ Takes 50% profits at +20% gain
- ✅ Takes 75% profits at +50% gain
- ✅ Rebalances when positions grow too large

**Loss Prevention:**
- ✅ Reviews positions at -10% loss
- ✅ Strong sell signal at -15% loss
- ✅ **Automatic stop loss at -20%**

**News-Informed Decisions:**
- ✅ Checks company news before every decision
- ✅ Exits on negative catalysts (earnings miss, lawsuits)
- ✅ Adds to positions on positive catalysts

---

## 📊 Monitoring Your Agent

### Check Portfolio Status Anytime

```bash
# Quick position check using Alpaca MCP
python test_alpaca_mcp.py
```

### Review Trading Logs

Agent logs are saved in:
- `data/agent_data/[agent_signature]/[date]_log.json`
- Contains all tool calls, decisions, and reasoning

### View Performance

```bash
# Run backtesting analysis
python tools/result_tools.py
```

---

## 🎯 Configuration Options

### Adjust Agent Behavior (`configs/default_config.json`)

```json
{
  "initial_cash": 10000,          // Starting capital
  "max_steps": 10,                // Max reasoning steps per session
  "stock_symbols": ["NVDA", ...], // Trading universe (NASDAQ 100)
  "init_date": "2025-01-13"       // Backtest start date
}
```

### Change AI Model (`main.py`)

```python
# Current: OpenAI GPT-4
agent = BaseAgent(
    signature="portfolio-manager",
    basemodel="gpt-4o",  # Change to: gpt-4, claude-3.5-sonnet, etc.
    # ...
)
```

---

## 🔧 Troubleshooting

### Issue: "No MCP tools available"

**Solution:**
```bash
# Restart MCP services
pkill -f "tool_jina_search.py"
pkill -f "tool_alpaca_data.py"
pkill -f "tool_alpaca_trade.py"
python agent_tools/start_mcp_services.py
```

### Issue: "Insufficient buying power"

**Cause:** Agent trying to buy more than available cash

**Solution:** Agent will automatically skip the trade. Check:
```bash
# Verify account balance
python -c "from alpaca.trading.client import TradingClient; 
client = TradingClient('YOUR_KEY', 'YOUR_SECRET', paper=True); 
print(client.get_account())"
```

### Issue: "Position not found"

**Cause:** Trying to close a position that doesn't exist

**Solution:** Agent will skip. Positions auto-refresh from Alpaca.

---

## 📚 Learn More

### Documentation
- `PORTFOLIO_MANAGEMENT_UPGRADE.md` - Full upgrade details
- `ALPACA_MCP_VERIFIED.md` - MCP tools reference
- `JINA_NEWS_INTEGRATION_COMPLETE.md` - News search guide
- `POSITION_CHECK_GUIDE.md` - How to check positions

### Agent Prompt
- `prompts/agent_prompt.py` - See the exact instructions the AI follows

### Example Session
- `data/agent_data/` - Review past trading sessions

---

## 🎓 Best Practices

### For Daily Trading

1. **Run once per day** during market hours (9:30 AM - 4:00 PM ET)
2. **Let the agent finish** - Don't interrupt the process
3. **Review decisions** - Check the reasoning in logs
4. **Monitor performance** - Track portfolio value over time

### For Backtesting

1. **Set init_date** in config to past date
2. **Run sequentially** - One day at a time
3. **Analyze results** - Use result_tools.py
4. **Compare to benchmark** - QQQ (NASDAQ 100 ETF)

### For Live Trading

⚠️ **WARNING**: Currently in PAPER TRADING mode only

To enable live trading:
1. Change `ALPACA_BASE_URL` in `.env` to live API
2. Fund your Alpaca account
3. **Start small** - Test with minimal capital first
4. **Monitor closely** - Watch the first few days carefully

---

## 🚀 Advanced Usage

### Run Multiple Agents (Portfolio Comparison)

```bash
# Agent 1: Conservative (5% positions, quick profit-taking)
python main.py --signature conservative --max-position 0.05

# Agent 2: Aggressive (15% positions, hold for bigger gains)
python main.py --signature aggressive --max-position 0.15

# Compare results
python tools/compare_agents.py conservative aggressive
```

### Custom Trading Rules

Edit `prompts/agent_prompt.py` to customize:
- Position size limits (default: 20% max)
- Profit-taking thresholds (default: +20%, +50%)
- Stop-loss levels (default: -20%)
- Diversification rules (default: 5-10 positions)

---

## ✅ Verification Checklist

Before running your first session:

- [ ] MCP services are running (3 services, 19 tools)
- [ ] Alpaca API keys are valid (paper trading)
- [ ] Jina API key is set (for news search)
- [ ] Python dependencies are installed
- [ ] Config file is set correctly

**All set?** Run `python main.py` and watch your AI portfolio manager in action! 🎉

---

## 🆘 Need Help?

- **Issues**: Check `TROUBLESHOOTING.md`
- **Questions**: Review documentation in `/docs`
- **Bugs**: Check logs in `data/agent_data/`

---

**Happy Trading! 📈🤖**
