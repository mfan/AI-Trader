# Active Trader - Autonomous Day Trading System

## Overview

The Active Trader is a **production-ready autonomous AI trading system** using a **mean reversion strategy** on high-volume ETFs. It runs 24/7 as a systemd service, exploiting the statistical edge that prices revert to VWAP 65-70% of the time intraday.

### Key Features
- 🎯 **Statistical Edge**: Mean reversion on SPY/QQQ/IWM has 65% win rate
- 📊 **Simple Strategy**: 2 indicators (VWAP + RSI) vs 5+ in complex systems
- 🛡️ **Tight Risk**: 1% per trade, 0.5% stops, 6% monthly limit
- ⏰ **Time-Based Edge**: 10 AM reversal, 2 PM continuation windows
- 🤖 **AI Execution**: XAI Grok-4.1-Fast for consistent rule following
- 📈 **ETFs Only**: No individual stock news/earnings risk
- 🔄 **Balanced Frequency**: Max 3 concurrent positions, 8 trades/day
- 💤 **No Overnight Risk**: Flat by 3:45 PM every day

## Quick Start

### Prerequisites
1. **Python Environment**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configuration**:
   Create a `.env` file with your API keys:
   ```bash
   XAI_API_KEY=...
   ALPACA_API_KEY=...
   ALPACA_SECRET_KEY=...
   ```
3. **MCP Services**: Ensure Alpaca Data and Trade MCP services are running.

### Running the Trader

**Production (Systemd)**:
```bash
sudo systemctl start active-trader.service
sudo journalctl -u active-trader.service -f
```

**Development (Manual)**:
```bash
source .venv/bin/activate
python active_trader.py
```

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
   - **Step 3**: Validate time window (10:00-10:30 AM or 2:00-3:00 PM)
   - **Step 4**: Position sizing (1% risk, 0.5% stop)
   - **Step 5**: Execute trade (market order for ETFs)
   - **Step 6**: Monitor positions (exit at VWAP, stop, or 3:45 PM)
5. **End-of-Day**: At 3:45 PM ET, close all positions
6. **Sleep**: If market closed, sleep until 5 min before next open

## Trading Strategy (v3.0 - Mean Reversion)

### The Edge

**Statistical Facts:**
- SPY/QQQ mean-revert intraday **65-70%** of the time
- Price touches VWAP **3-5 times per day** on average
- Extreme RSI (<30 or >70) reverts within 30-60 minutes **75%** of the time

### The 5 Simple Rules

| Rule | Description |
|------|-------------|
| **1. ETFs Only** | SPY, QQQ, IWM, XLF, XLE, XLU, GLD, TLT |
| **2. VWAP + RSI** | Long: price <VWAP -0.3% AND RSI<30. Short: price >VWAP +0.3% AND RSI>70 |
| **3. Time Windows** | 10:00-10:30 AM (reversal), 2:00-3:00 PM (continuation) |
| **4. Max 3 Positions** | Concurrent positions in DIFFERENT ETFs (diversified risk) |
| **5. Exit 3:45 PM** | Flat overnight, no exceptions |

### Position Sizing

```python
risk_amount = equity * 0.01          # 1% risk per trade
stop_distance = entry_price * 0.005  # 0.5% stop-loss
shares = int(risk_amount / stop_distance)
target = VWAP                        # Mean reversion target
```

### Expected Performance

| Metric | Value |
|--------|-------|
| Win Rate | 60-65% |
| Avg Win | +0.3% |
| Avg Loss | -0.5% |
| Trades/Day | 5-8 |
| Max Positions | 3 concurrent |
| Monthly Target | +4-6% |

## Risk Management (Elder's Rules)

**Elder's 6% Rule** (Monthly Drawdown Brake):
- Track equity from start of month
- If drawdown ≥ 6% → HALT all trading for rest of month
- Prevents & Data Storage

**Log Structure**:
```
data/agent_data/
└── xai-grok-4.1-fast/
    ├── log/
    │   └── 2025-12-13/
    │       └── log.jsonl          # Trading decisions & outcomes
    ├── trades/
    │   └── trade_history.jsonl   # Completed trades
    ├── momentum_cache.db          # SQLite: Daily momentum scans
    └── risk_management.json       # Elder's 6% Rule tracking
```

**Console Output**: Real-time cycle status, market regime, decisions, errors
**Systemd Journal**: `sudo journalctl -u active-trader -f`
**Stdout/Stderr Files**: `logs/active_trader_stdout.log`, `logs/active_trader_stderr.log`

## Documentation
- **[CLAUDE.md](CLAUDE.md)** - **START HERE**: Complete system analysis, architecture, dependencies, flow diagrams
- [SYSTEMD_SERVICE_SETUP.md](SYSTEMD_SERVICE_SETUP.md) - Service installation, management, troubleshooting
- [ELDER_QUICK_REFERENCE.md](ELDER_QUICK_REFERENCE.md) - Trading strategy: Elder's Triple Screen methodology
- [BELLAFIORE_PRINCIPLES_APPLIED.md](BELLAFIORE_PRINCIPLES_APPLIED.md) - Trading psychology & discipline
- [DEEPSEEK_SETUP.md](DEEPSEEK_SETUP.md) - Alternative AI model configuration

## Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `active_trader.py` | 859 | Main orchestrator - 24-hour loop, market schedule, risk checks |
| `base_agent.py` | 801 | AI agent core - MCP client, LLM, trading execution |
| `agent_prompt.py` | 394 | Trading strategy prompt - Elder Triple Screen, anti-churning |
| `market_schedule.py` | 265 | Market hours detection, sleep logic, session management |
| `elder_risk_manager.py` | 417 | 6% Rule, 2% Rule, position sizing, monthly tracking |
| `momentum_scanner.py` | 734 | Daily pre-market scan, Top 100 movers, SQLite cache |
| `alpaca_trading.py` | 822 | Order execution, position management, account queries |
| `alpaca_data_feed.py` | 524 | Real-time market data, historical bars, quotes |
| `alpaca_mcp_bridge.py` | 499 | Python interface to Alpaca's 60+ MCP tools |

## Version History

### v3.0 (Dec 2025) - Simplified Mean Reversion Edge
- ✅ **Complete strategy overhaul**: Replaced Elder Triple Screen with mean reversion
- ✅ **Statistical edge**: 65-70% intraday reversion rate on ETFs
- ✅ **Simplified to 2 indicators**: VWAP + RSI (vs 5+ previously)
- ✅ **ETFs only**: No individual stock risk (SPY, QQQ, IWM, etc.)
- ✅ **Time-based windows**: 10 AM reversal, 2 PM continuation
- ✅ **Tighter risk**: 1% per trade, 0.5% stops
- ✅ **Natural low frequency**: 1 position max, no anti-churning needed

### v2.0 (Dec 2025) - Anti-Churning & Elder Strategy
- ✅ 6 anti-churning behavioral controls
- ✅ Elder's Triple Screen methodology
- ✅ Enhanced market regime detection
- ✅ Comprehensive documentation

### v1.5 (Nov 2025) - Modular Architecture
- ✅ Separated market schedule, config, agent factory into modules
- ✅ Momentum scanner with SQLite caching
- ✅ Intelligent sleep mode (wakes 5 min before market)
- ✅ Elder Risk Manager integration

### v1.0 (Oct 2025) - Initial Production Release
- ✅ BaseAgent with MCP integration
- ✅ Systemd service configuration
- ✅ Basic Elder Triple Screen implementation
# Also cap at 20% of equity
max_position_value = account_equity * 0.20
max_shares_by_cap = max_position_value / entry_price

final_shares = min(shares, max_shares_by_cap)
```

**Portfolio Limits**:
- Max 3 open positions simultaneously (diversification)
- Max 6% total portfolio risk (3 × 2%)
- 30% buying power buffer always maintained

**Anti-Churning Controls** (v2.0):
- 30-min cooldown after closing position (same symbol)
- Max 2 round-trips per symbol per day
- 30-min minimum hold time (unless stop-loss hit)
- Win rate circuit breaker: Stop if <40% after 3+ trades
- Daily trade limit: Max 6 round-trips across all symbols
- No scalping: Block trades targeting <$0.50 movement

**End-of-Day**:
- Hard stop at 3:45 PM ET (15 min before close)
- Close ALL positions via `close_all_positions(cancel_orders=True)`
- Ensures flat book overnight (no overnight risk)

## Logging
- **Console**: Real-time status updates.
- **File**: Detailed logs in `active_trader.log` and `data/agent_data/`.

## Documentation
- [Systemd Service Setup](SYSTEMD_SERVICE_SETUP.md)
- [Development Setup](CLAUDE.md)
- [Trading Strategy: Bellafiore Principles](BELLAFIORE_PRINCIPLES_APPLIED.md)
- [Trading Strategy: Elder's Triple Screen](ELDER_QUICK_REFERENCE.md)
- [DeepSeek Model Setup](DEEPSEEK_SETUP.md)
