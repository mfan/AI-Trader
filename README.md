# Active Trader - Autonomous Day Trading System

## Overview

The Active Trader is a **production-ready autonomous AI trading system** using a **mean reversion strategy** on high-volume ETFs. It runs 24/7 as a systemd service, exploiting the statistical edge that prices revert to VWAP 65-70% of the time intraday.

### Key Features
- 🎯 **Statistical Edge**: Mean reversion on SPY/QQQ/IWM has 65% win rate
- 📊 **Simple Strategy**: 2 indicators (VWAP + RSI) vs 5+ in complex systems
- 🛡️ **ATR-Based Risk**: 1% per trade, 1.5×ATR stops (volatility-adjusted), 6% monthly limit
- ⏰ **Time-Based Edge**: 10 AM reversal, 2 PM continuation windows
- 🤖 **AI Execution**: XAI Grok-4.1-Fast for consistent rule following
- 📈 **ETFs + Leveraged ETFs**: Standard (SPY, QQQ) + 3x leveraged (TQQQ, SQQQ, etc.)
- ↕️ **Long AND Short**: Both directions on all ETFs
- 🔄 **Balanced Frequency**: Max 3 concurrent positions, 8 trades/day
- 💤 **No Overnight Risk**: Flat by 3:45 PM every day

## Quick Start

### Prerequisites
1. **Python Environment**:
   ```bash
   cd /home/mfan/work/aitrader
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Configuration**: Create a `.env` file with your API keys:
   ```bash
   XAI_API_KEY=...
   ALPACA_API_KEY=...
   ALPACA_SECRET_KEY=...
   ```
3. **MCP Services**: Ensure Alpaca Data and Trade MCP services are running.

### Running the Trader

**Production (Systemd)**:
```bash
sudo ./manage_services.sh start-mcp   # Start MCP services first
sudo ./manage_services.sh start       # Start Active Trader
sudo journalctl -u active-trader -f   # Watch logs
```

**Development (Manual)**:
```bash
source .venv/bin/activate
python active_trader.py
```

---

## Trading Strategy (v3.0 - Mean Reversion)

### The Edge

**Statistical Facts:**
- SPY/QQQ mean-revert intraday **65-70%** of the time
- Price touches VWAP **3-5 times per day** on average
- Extreme RSI (<30 or >70) reverts within 30-60 minutes **75%** of the time

### The 5 Simple Rules

| Rule | Description |
|------|-------------|
| **1. ETFs (Standard + Leveraged)** | Standard: SPY, QQQ, IWM, XLF, XLE, XLU, GLD, TLT. Leveraged 3x: TQQQ, SQQQ, SPXL, SPXS, SOXL, SOXS, TNA, TZA |
| **2. VWAP + RSI (Long OR Short)** | Long: price <VWAP -0.3% AND RSI<30. Short: price >VWAP +0.3% AND RSI>70. Leveraged: wider 0.5% threshold |
| **3. Time Windows** | 10:00-11:30 AM (morning session), 1:00-3:45 PM (afternoon session) |
| **4. Max 3 Positions** | Concurrent positions in DIFFERENT ETFs (diversified risk) |
| **5. Exit 3:45 PM** | Flat overnight, no exceptions |

### Position Sizing (ATR-Based)

```python
# Get ATR(14) on 5-minute bars for volatility-adjusted stops
bars_5m = get_bars(symbol, timeframe='5Min', limit=20)
ATR = calculate_ATR(bars_5m, period=14)

risk_amount = equity * 0.01          # 1% risk per trade
stop_distance = 1.5 * ATR            # 1.5×ATR stop (in dollars)

# Calculate shares with BUYING POWER CAP
risk_shares = int(risk_amount / stop_distance)
max_shares = int((buying_power * 0.20) / entry_price)  # 20% cap
shares = min(risk_shares, max_shares)
target = VWAP                        # Mean reversion target

# Example: TQQQ with ATR=$0.80
# stop_distance = 1.5 * 0.80 = $1.20
# With $100K equity, risk = $1000, shares = 833
```

### Expected Performance

| Metric | Value |
|--------|-------|
| Win Rate | 60-65% |
| Avg Win | +0.3% |
| Avg Loss | -1.5×ATR (varies) |
| Trades/Day | 5-8 |
| Max Positions | 3 concurrent |
| Monthly Target | +4-6% |
| Stop Type | ATR-based (volatility adaptive) |

---

## Risk Management

**Per-Trade Risk (1% Rule):**
- Max risk per trade = 1% of equity
- Stop-loss at 0.5% from entry
- Target = VWAP touch (mean reversion)

**Daily Limits:**
- Max 8 round-trip trades per day
- Max 3 concurrent positions (diversified sectors)
- Stop trading if down 2% for the day
- Stop trading after 3 consecutive losses

**Monthly Limit (6% Rule):**
- If drawdown ≥ 6% for the month → HALT all trading
- Resume next month with fresh start

**End-of-Day:**
- Hard stop at 3:45 PM ET (15 min before close)
- Close ALL positions
- Ensures flat book overnight (no gap risk)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│            ACTIVE TRADER (Systemd Service)                  │
│  active_trader.py - 24-hour orchestration loop              │
└───────┬─────────────────────────────────────────────────────┘
        │
        ├──► Market Schedule (market_schedule.py)
        │     • Detects pre/regular/post market hours
        │     • Calculates sleep windows (wakes 5 min before open)
        │     • Handles market holidays via Alpaca API
        │
        ├──► Agent Factory (agent_factory.py)
        │     • Dynamically loads BaseAgent
        │     • Configures AI model (Grok-4.1-Fast)
        │     • Injects ETF watchlist: SPY, QQQ, IWM, XLF, XLE, XLU, GLD, TLT
        │
        └──► BaseAgent (base_agent.py)
              │
              ├──► MCP Client (langchain_mcp_adapters)
              │     • Alpaca Data MCP (port 8004)
              │     • Alpaca Trade MCP (port 8005)
              │     • 60+ tools: get_bars, get_quote, place_order, etc.
              │
              ├──► AI Model (XAI Grok-4.1-Fast)
              │     • System prompt: agent_prompt.py (v3.0 Mean Reversion)
              │     • 2 indicators: VWAP + RSI
              │     • Max 30 reasoning steps per cycle
              │
              ├──► Risk Manager
              │     • 1% per-trade risk, 0.5% stop-loss
              │     • 6% monthly drawdown brake
              │     • Max 3 concurrent positions
              │
              └──► Trading Execution
                    • ETFs only: SPY, QQQ, IWM, XLF, XLE, XLU, GLD, TLT
                    • Order placement + verification
                    • JSONL logging per cycle
```

### Trading Cycle (Every 2 Minutes)
1. **Market Hours Check**: Determine if pre/regular/post-market or closed
2. **Risk Check**: Verify 6% monthly rule not violated
3. **Agent Initialization**: Create/reuse agent with ETF watchlist
4. **AI Decision Loop** (per cycle):
   - **Step 1**: Check account (equity, buying power, positions)
   - **Step 2**: Scan ETFs for setups (VWAP deviation + RSI extreme)
   - **Step 3**: Validate time window (10:00-11:30 AM or 1:00-3:45 PM)
   - **Step 4**: Position sizing (1% risk, 0.5% stop)
   - **Step 5**: Execute trade (market order for ETFs)
   - **Step 6**: Monitor positions (exit at VWAP, stop, or 3:45 PM)
5. **End-of-Day**: At 3:45 PM ET, close all positions
6. **Sleep**: If market closed, sleep until 5 min before next open

---

## Logging & Data Storage

**Log Structure**:
```
data/agent_data/
└── xai-grok-4.1-fast/
    ├── log/
    │   └── 2025-12-14/
    │       └── log.jsonl          # Trading decisions & outcomes
    ├── trades/
    │   └── trade_history.jsonl   # Completed trades
    └── risk_management.json       # 6% Rule tracking
```

**Console Output**: Real-time cycle status, decisions, errors
**Systemd Journal**: `sudo journalctl -u active-trader -f`
**Stdout/Stderr Files**: `logs/active_trader_stdout.log`, `logs/active_trader_stderr.log`

---

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - **START HERE**: Complete system analysis, architecture, dependencies
- [SYSTEMD_SERVICE_SETUP.md](SYSTEMD_SERVICE_SETUP.md) - Service installation and management
- [ELDER_QUICK_REFERENCE.md](ELDER_QUICK_REFERENCE.md) - Elder's methodology (legacy v2.0)
- [BELLAFIORE_PRINCIPLES_APPLIED.md](BELLAFIORE_PRINCIPLES_APPLIED.md) - Trading psychology
- [DEEPSEEK_SETUP.md](DEEPSEEK_SETUP.md) - Alternative AI model configuration

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `active_trader.py` | Main orchestrator - 24-hour loop, market schedule |
| `agent/base_agent/base_agent.py` | AI agent core - MCP client, LLM, execution |
| `prompts/agent_prompt.py` | **v3.0 Mean Reversion** strategy prompt |
| `prompts/agent_prompt_v2_elder.py` | Legacy Elder Triple Screen (backup) |
| `tools/market_schedule.py` | Market hours detection, sleep logic |
| `tools/elder_risk_manager.py` | 6% monthly rule, risk tracking |
| `tools/alpaca_trading.py` | Order execution, position management |
| `tools/alpaca_data_feed.py` | Real-time market data, quotes |

---

## Version History

### v3.0 (Dec 14, 2025) - Simplified Mean Reversion Edge
- ✅ **Complete strategy overhaul**: Replaced Elder Triple Screen with mean reversion
- ✅ **Statistical edge**: 65-70% intraday reversion rate on ETFs
- ✅ **Simplified to 2 indicators**: VWAP + RSI (vs 5+ previously)
- ✅ **ETFs only**: SPY, QQQ, IWM, XLF, XLE, XLU, GLD, TLT
- ✅ **Time-based windows**: 10 AM reversal, 2 PM continuation
- ✅ **Conservative risk**: 1% per trade, 0.5% stops
- ✅ **Balanced frequency**: Max 3 positions, 8 trades/day

### v2.0 (Dec 11, 2025) - Anti-Churning & Elder Strategy
- 6 anti-churning behavioral controls
- Elder's Triple Screen methodology
- Enhanced market regime detection

### v1.5 (Nov 2025) - Modular Architecture
- Separated market schedule, config, agent factory
- Momentum scanner with SQLite caching
- Intelligent sleep mode

### v1.0 (Oct 2025) - Initial Release
- BaseAgent with MCP integration
- Systemd service configuration
