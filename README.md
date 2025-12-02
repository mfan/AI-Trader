# Active Trader - Autonomous Day Trading System

## Overview

The Active Trader is an **autonomous AI-powered day trading system** designed for high-frequency portfolio management. It runs continuously as a systemd service, leveraging a modular architecture to handle market analysis, trade execution, and risk management autonomously.

### Key Features
- 🤖 **Autonomous AI Agent**: Uses XAI Grok-4-latest for decision making.
- 🏗️ **Modular Architecture**: Clean separation of concerns (Market Schedule, Config, Agent Factory).
- 🎯 **Momentum Scanning**: Daily pre-market scans of 4,701+ US stocks to identify top movers.
- ⏰ **Smart Scheduling**: Intelligent sleep mode during off-hours; auto-wake for market open.
- 🛡️ **Robust Risk Management**: Implements Elder's 6% Rule, 2% per-trade limit, and auto-stops.
- 📊 **Technical Analysis**: Integrated TA-Lib support for RSI, MACD, Bollinger Bands, etc.
- 🔄 **Resilient Operation**: Auto-retry logic for API failures and connection issues.

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

The system is refactored into a modular design:

```
/home/mfan/work/aitrader/
├── active_trader.py       # Main entry point & orchestration loop
├── tools/
│   ├── market_schedule.py # Market hours, session detection, sleep logic
│   ├── config_loader.py   # Configuration management
│   ├── agent_factory.py   # Dynamic agent instantiation
│   ├── scanner_utils.py   # Pre-market momentum scanning
│   ├── ta_helper.py       # Technical analysis wrappers
│   └── ...
├── agent/                 # AI Agent logic
├── configs/               # JSON configuration files
└── data/                  # Logs and runtime data
```

### Trading Cycle
1. **Wake Up**: System wakes 5 minutes before market open.
2. **Scan**: Runs momentum scan (Top Gainers/Losers) if needed.
3. **Initialize**: Loads the AI agent with the latest watchlist.
4. **Loop (Every 2 mins)**:
   - **Analyze**: Agent reviews portfolio and market data.
   - **Decide**: Generates Buy/Sell/Hold signals based on TA and sentiment.
   - **Execute**: Submits orders via Alpaca MCP.
   - **Verify**: Confirms order status and updates portfolio state.
5. **Sleep**: Enters low-power mode when the market closes.

## Risk Management
- **Elder's 6% Rule**: Suspends trading if monthly drawdown hits 6%.
- **Position Limits**: Max 2% risk per trade; max 5 open positions.
- **End-of-Day**: Auto-closes all positions by 3:55 PM ET (Day Trading mode).

## Logging
- **Console**: Real-time status updates.
- **File**: Detailed logs in `active_trader.log` and `data/agent_data/`.

## Documentation
- [Systemd Service Setup](SYSTEMD_SERVICE_SETUP.md)
- [Development Setup](CLAUDE.md)
- [Trading Strategy: Bellafiore Principles](BELLAFIORE_PRINCIPLES_APPLIED.md)
- [Trading Strategy: Elder's Triple Screen](ELDER_QUICK_REFERENCE.md)
- [DeepSeek Model Setup](DEEPSEEK_SETUP.md)
