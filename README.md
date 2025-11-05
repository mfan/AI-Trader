# Active Trader - Autonomous Day Trading System

## Overview

The Active Trader is an **autonomous AI-powered day trading system** that runs continuously as a systemd service. It features intelligent sleep mode, regular market hours trading, and fully automated execution:

### Key Features
- 🤖 **Autonomous Trading**: Fully automated buy/sell decisions using DeepSeek AI (v3.1)
- ⏰ **Regular Market Hours Only**: Trades 9:30 AM - 4:00 PM ET (extended hours disabled)
- 💤 **Intelligent Sleep Mode**: Minimal CPU usage when markets are closed
- 🔄 **Continuous Operation**: Runs 24/7 as systemd service with automatic restarts
- 📊 **Real-time Analysis**: Technical indicators, market data, and position management
- 🎯 **Day Trading Strategy**: All positions closed by 3:55 PM ET daily
- 🛡️ **Risk Management**: Position sizing, stop-losses, and profit targets

## Quick Start

### Prerequisites

1. **Environment Setup**:
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Configure environment variables in .env
   DEEPSEEK_API_KEY=your_api_key_here
   ALPACA_API_KEY=your_alpaca_key
   ALPACA_SECRET_KEY=your_alpaca_secret
   ```

2. **MCP Services**: Alpaca Data and Trade services must be running
   ```bash
   # Check MCP services status
   sudo systemctl status alpaca-data.service
   sudo systemctl status alpaca-trade.service
   ```

### Starting the Active Trader

**Option 1: Using systemd service (Recommended for production)**

```bash
# Start the service
sudo systemctl start active-trader.service

# Enable automatic startup on boot
sudo systemctl enable active-trader.service

# Check status
sudo systemctl status active-trader.service

# View live logs
sudo journalctl -u active-trader.service -f
```

**Option 2: Manual execution (For testing/development)**

```bash
# Activate virtual environment
source .venv/bin/activate

# Run directly
python active_trader.py
```

## System Architecture

### Service Stack

The Active Trader runs as part of a systemd service stack:

```
┌─────────────────────────────────────┐
│   active-trader.service             │
│   (Main Trading Logic)              │
│   - DeepSeek AI agent               │
│   - Market hours detection          │
│   - Position management             │
│   - Intelligent sleep mode          │
└──────────┬──────────────────────────┘
           │
           ├─► alpaca-data.service (MCP)
           │   - Real-time quotes
           │   - Historical bars
           │   - Technical indicators
           │
           └─► alpaca-trade.service (MCP)
               - Order execution
               - Position tracking
               - Portfolio management
```

### Trading Cycle

**During Market Hours (9:30 AM - 4:00 PM ET):**
```
1. Check portfolio positions
2. Analyze technical indicators (RSI, MACD, EMA, VWAP)
3. Get trading signals for current holdings
4. AI agent makes autonomous buy/sell/hold decisions
5. Execute trades immediately (no permission required)
6. Repeat every ~5-10 minutes
7. Close all positions at 3:55 PM ET
```

**Outside Market Hours:**
```
1. Detect market is closed
2. Calculate next market open time
3. Enter intelligent sleep mode (minimal CPU)
4. Wake up 5 minutes before market open (9:25 AM ET)
5. Prepare for next trading session
```

## Features

### 🤖 Autonomous Trading
- **Zero human intervention**: AI agent makes and executes all trading decisions
- **No permission seeking**: Agent executes trades immediately when signals warrant
- **Continuous operation**: Runs 24/7 with intelligent sleep during closed hours
- **Auto-restart**: systemd ensures service recovers from crashes

### ⏰ Market Hours Intelligence
- **Regular hours only**: Trades 9:30 AM - 4:00 PM ET (no pre-market/post-market)
- **Smart scheduling**: Wakes up 5 minutes before market open (9:25 AM)
- **Automatic detection**: Knows weekends, holidays, and market status
- **Sleep mode**: Minimal CPU usage when markets closed (~11+ hours daily)

### 📊 Technical Analysis
- **Real-time indicators**: RSI, MACD, EMA (20/50), VWAP, Bollinger Bands
- **Multi-timeframe**: 1-min, 5-min, 15-min bars for analysis
- **Signal strength**: Weighted scoring system for trade quality
- **Volume analysis**: Confirms price movements with volume

### 🎯 Day Trading Strategy
- **No overnight holds**: All positions closed by 3:55 PM ET
- **Position sizing**: Risk management based on portfolio size
- **Stop losses**: Automatic 2×ATR stop loss on all positions
- **Profit targets**: Take profits at resistance or momentum exhaustion
- **Trend following**: Focuses on momentum and breakout strategies

### 🛡️ Risk Management
- **Position limits**: Maximum position size constraints
- **Daily loss limits**: Stop trading if losses exceed threshold
- **Diversification**: Limits per-symbol exposure
- **Real-time monitoring**: Continuous position and P&L tracking
- **Emergency stop**: Close all positions if needed

### 📝 Logging & Monitoring
- **Comprehensive logs**: All decisions, trades, and errors logged
- **Service logs**: systemd journal with rotation
- **Trade history**: JSONL files for each trading day
- **Position tracking**: Persistent position state across restarts
- **Performance metrics**: Daily P&L, win rate, trade statistics

## Configuration

### Service Configuration

The Active Trader runs as a systemd service. Configuration file located at:
```
/etc/systemd/system/active-trader.service
```

Service features:
- **Auto-restart**: Restarts on failure with backoff strategy
- **Dependency management**: Waits for MCP services to start
- **Resource limits**: Memory and task limits configured
- **User isolation**: Runs as dedicated user for security

### Trading Configuration

Agent configuration in `configs/default_config.json`:

```json
{
  "agent_type": "BaseAgent",
  "date_range": {
    "init_date": "2025-11-05",
    "end_date": "2025-11-05"
  },
  "models": [
    {
      "name": "deepseek",
      "signature": "deepseek-chat-v3.1",
      "basemodel": "openai",
      "enabled": true
    }
  ],
  "agent_config": {
    "max_steps": 30,
    "max_retries": 3,
    "base_delay": 1.0,
    "initial_cash": 100000.0
  }
}
```

**Key Parameters:**
- `max_steps`: Maximum AI reasoning steps per cycle (30 recommended)
- `max_retries`: Retry attempts for failed API calls (3)
- `initial_cash`: Starting capital for paper trading
- `signature`: AI model to use (deepseek-chat-v3.1)

### Market Hours Configuration

Configured in `active_trader.py`:

```python
# Market hours (ET timezone)
REGULAR_START = time(9, 30)   # 9:30 AM
REGULAR_END = time(16, 0)     # 4:00 PM
CLOSE_POSITIONS_TIME = time(15, 55)  # 3:55 PM - close all positions
```

**Schedule:**
- **Trading hours**: 9:30 AM - 4:00 PM ET
- **Close positions**: 3:55 PM ET (5 min before close)
- **Wake-up time**: 9:25 AM ET (5 min before open)
- **Sleep mode**: 4:00 PM - 9:25 AM next day

### Agent Prompt Configuration

Trading strategy and behavior defined in `prompts/agent_prompt.py`:
- Trading style and approach
- Technical indicator usage
- Entry/exit rules
- Risk management rules
- Position sizing strategy
- Autonomous execution behavior

## Service Management

### Starting/Stopping Services

```bash
# Start active trader
sudo systemctl start active-trader.service

# Stop active trader
sudo systemctl stop active-trader.service

# Restart active trader
sudo systemctl restart active-trader.service

# Enable auto-start on boot
sudo systemctl enable active-trader.service

# Disable auto-start
sudo systemctl disable active-trader.service
```

### Managing All Services

Use the provided management script:

```bash
# Start all services (Alpaca Data + Trade + Active Trader)
./manage_services.sh start

# Stop all services
./manage_services.sh stop

# Restart all services
./manage_services.sh restart

# Check status of all services
./manage_services.sh status

# View logs for all services
./manage_services.sh logs
```

### Service Status

```bash
# Check active trader status
sudo systemctl status active-trader.service

# Check MCP services
sudo systemctl status alpaca-data.service
sudo systemctl status alpaca-trade.service

# View recent logs (last 50 lines)
sudo journalctl -u active-trader.service -n 50

# Follow logs in real-time
sudo journalctl -u active-trader.service -f

# View logs for specific date
sudo journalctl -u active-trader.service --since "2025-11-05" --until "2025-11-06"
```

## Monitoring

### Log Files

**Service Logs (systemd journal):**
```bash
# Follow active trader logs
sudo journalctl -u active-trader.service -f

# Last 100 lines
sudo journalctl -u active-trader.service -n 100

# Today's logs only
sudo journalctl -u active-trader.service --since today
```

**Application Logs:**
```bash
# Standard output (main log)
tail -f logs/active_trader_stdout.log

# Error output
tail -f logs/active_trader_stderr.log

# MCP service logs
tail -f logs/alpaca_data_mcp.log
tail -f logs/alpaca_trade_mcp.log
```

**Agent Decision Logs:**
```bash
# View today's agent decisions
ls data/agent_data/deepseek-chat-v3.1/log/$(date +%Y-%m-%d)/

# View recent decisions
tail -f data/agent_data/deepseek-chat-v3.1/log/$(date +%Y-%m-%d)/*.log
```

**Trade History:**
```bash
# View today's trades
cat data/agent_data/deepseek-chat-v3.1/trades/$(date +%Y-%m-%d)_trades.jsonl | jq

# Count trades today
wc -l data/agent_data/deepseek-chat-v3.1/trades/$(date +%Y-%m-%d)_trades.jsonl
```

### Real-time Monitoring

**Check if services are running:**
```bash
# Process status
ps aux | grep -E "(active_trader|alpaca)" | grep -v grep

# Network ports (MCP services)
lsof -nP -iTCP:8004,8005 -sTCP:LISTEN

# Service health
systemctl is-active active-trader.service
```

**Monitor system resources:**
```bash
# CPU and memory usage
systemctl status active-trader.service | grep -E "(Memory|CPU)"

# Detailed resource usage
sudo systemctl show active-trader.service --property=CPUUsageNSec,MemoryCurrent
```

### Performance Metrics

**Position tracking:**
```bash
# View current positions
cat data/agent_data/deepseek-chat-v3.1/position/position.jsonl | tail -1 | jq

# Position history
cat data/agent_data/deepseek-chat-v3.1/position/position.jsonl | jq
```

**Daily P&L:**
```bash
# Parse trade logs for P&L (requires jq)
cat data/agent_data/deepseek-chat-v3.1/trades/$(date +%Y-%m-%d)_trades.jsonl | \
  jq -s 'map(.pnl) | add'
```

## Daily Trading Schedule

### Weekday Schedule (Monday - Friday)

| Time (ET) | Status | Description |
|-----------|--------|-------------|
| 12:00 AM - 9:25 AM | 💤 **Sleep Mode** | Intelligent sleep - minimal CPU usage |
| 9:25 AM | 🔔 **Wake Up** | Service wakes 5 minutes before market |
| 9:25 AM - 9:30 AM | 🔧 **Preparation** | Initialize connections, load positions |
| 9:30 AM | 🟢 **Market Open** | Begin active trading |
| 9:30 AM - 3:55 PM | 📈 **Active Trading** | Continuous monitoring and execution |
| 3:55 PM | ⚠️ **Position Close** | Close ALL positions (mandatory) |
| 4:00 PM | 🔴 **Market Close** | Regular market closes |
| 4:00 PM - 11:59 PM | 💤 **Sleep Mode** | Enter sleep until next morning |

### Weekend/Holiday Schedule

| Day | Status | Description |
|-----|--------|-------------|
| **Saturday** | 💤 Full Sleep | No market activity |
| **Sunday** | 💤 Full Sleep | No market activity |
| **Market Holidays** | 💤 Full Sleep | Auto-detected, no trading |

### Trading Session Details

**Pre-Market Trading:** ❌ DISABLED
- Previous: 4:00 AM - 9:30 AM
- Current: Not active

**Regular Market Trading:** ✅ ACTIVE
- Hours: 9:30 AM - 4:00 PM ET
- Trading frequency: ~5-10 minute intervals
- Position close deadline: 3:55 PM ET

**Post-Market Trading:** ❌ DISABLED
- Previous: 4:00 PM - 8:00 PM
- Current: Not active

### Sleep Mode Efficiency

**Energy Savings:**
- Active trading: ~6.5 hours/day (9:30 AM - 4:00 PM)
- Sleep mode: ~17.5 hours/day
- CPU usage reduction: >95% during sleep
- Wake-up precision: ±30 seconds

**Wake/Sleep Cycle:**
```
Weekday:
  ├─ 9:25 AM: Wake up (preparation)
  ├─ 9:30 AM - 4:00 PM: Active trading
  └─ 4:00 PM: Enter sleep mode

Weekend:
  └─ Full sleep (24 hours)
```

## Sample Output

### Service Startup (Market Closed)

```
✅ DeepSeek API key loaded from environment
🚀 Initializing agent: deepseek-chat-v3.1
✅ Loaded 20 MCP tools
🧠 Using DeepSeek API: https://api.deepseek.com
✅ AI model initialized: deepseek-chat
✅ Agent deepseek-chat-v3.1 initialization completed
✅ Agent initialization complete
🎯 Starting continuous day trading loop...

================================================================================
💤 MARKET CLOSED - INTELLIGENT SLEEP MODE
================================================================================
⏰ Current time: Tuesday, November 04, 2025 at 09:45:34 PM ET

📅 Regular Market Hours ONLY:
   └─ 🟢 Regular: 9:30 AM - 4:00 PM ET
   📝 Pre-market and post-market trading DISABLED

⏭️  Next market opens: Wednesday, November 05 at 09:30 AM ET
⏳ Time until open: 11h 44m

💤 Entering intelligent sleep mode - CPU usage minimized
⏰ Will wake up 5 minutes before market open for preparation
================================================================================

� Sleeping until 09:25:00 AM ET (wake up 5 min before market)...
💤 Sleep mode active - Wake up in: 11h 39m
```

### Active Trading (Market Open)

```
================================================================================
� TRADING CYCLE #145 - REGULAR SESSION 🟢
⏰ 2025-11-05 10:30:15 ET (Tuesday)
================================================================================

📈 Current Portfolio Status:
   💰 Cash: $98,450.23
   📊 Positions: 3 open
   
   ┌─────────┬──────────┬────────────┬──────────────┐
   │ Symbol  │ Quantity │ Avg Price  │ Market Value │
   ├─────────┼──────────┼────────────┼──────────────┤
   │ AAPL    │ 50       │ $175.20    │ $8,850.00    │
   │ TSLA    │ 25       │ $245.80    │ $6,395.00    │
   │ NVDA    │ 15       │ $485.30    │ $7,529.50    │
   └─────────┴──────────┴────────────┴──────────────┘

🤖 Agent Decision: EXECUTING TRADES
   ├─ SELL 50 AAPL @ $177.50 (take profit, +$115.00)
   ├─ BUY 30 AMD @ $142.30 (breakout signal, RSI: 45)
   └─ HOLD TSLA (trend strong, stop at $240.00)

✅ Trades executed successfully
⏳ Next cycle in 8 minutes

================================================================================
```

### End of Day Close

```
================================================================================
🔴 END OF DAY POSITION CLOSE - 3:55 PM ET
================================================================================

⚠️  Closing ALL positions before market close (4:00 PM)

Positions to close:
   ├─ TSLA: 25 shares @ market
   ├─ NVDA: 15 shares @ market
   └─ AMD: 30 shares @ market

✅ All positions closed successfully

📊 Daily Summary:
   ├─ Total trades: 12
   ├─ Winning trades: 8 (66.7%)
   ├─ Daily P&L: +$245.80
   ├─ Final cash: $99,872.15
   └─ Status: FLAT (no positions)

💤 Market closing - entering sleep mode
⏰ Next trading session: Tomorrow at 9:30 AM ET
================================================================================
```

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Active Trader Service                    │
│                     (active_trader.py)                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              BaseAgent (DeepSeek v3.1)               │  │
│  │  • Market analysis                                    │  │
│  │  • Trading decisions                                  │  │
│  │  • Risk management                                    │  │
│  │  • Position management                                │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │           Market Hours Controller                     │  │
│  │  • Time detection (9:30 AM - 4:00 PM ET)             │  │
│  │  • Intelligent sleep mode                             │  │
│  │  • Wake/sleep scheduling                              │  │
│  │  • Position close enforcement (3:55 PM)               │  │
│  └──────────────────┬───────────────────────────────────┘  │
└────────────────────┼────────────────────────────────────────┘
                     │
         ┌───────────┴──────────┐
         │                       │
    ┌────▼─────┐          ┌─────▼────┐
    │  Alpaca  │          │  Alpaca  │
    │   Data   │          │  Trade   │
    │ Service  │          │ Service  │
    │ (MCP)    │          │  (MCP)   │
    │ :8004    │          │  :8005   │
    └────┬─────┘          └─────┬────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │   Alpaca    │
              │  Markets    │
              │  Paper API  │
              └─────────────┘
```

### Data Flow

**Market Open (9:30 AM):**
```
1. Wake-up signal (9:25 AM)
2. Initialize MCP connections
3. Load positions from Alpaca
4. Begin trading cycle loop
   ├─ Get current positions
   ├─ Fetch technical indicators
   ├─ AI analyzes market conditions
   ├─ Make trading decisions
   ├─ Execute trades via Alpaca
   └─ Log all activities
5. Repeat every ~5-10 minutes
```

**Market Close (4:00 PM):**
```
1. Detect close time (3:55 PM)
2. Close ALL open positions
3. Verify all positions flat
4. Calculate daily P&L
5. Save trade history
6. Enter sleep mode
7. Calculate next wake time
```

### Technology Stack

**Core:**
- Python 3.8+
- systemd (service management)
- pytz (timezone handling)

**AI/ML:**
- DeepSeek Chat v3.1 (trading decisions)
- OpenAI-compatible API client

**Market Data:**
- Alpaca Markets API
- Model Context Protocol (MCP) servers
- Real-time quotes and bars

**Technical Analysis:**
- TA-Lib or pandas-ta
- Custom indicator calculations
- Multi-timeframe analysis

**Storage:**
- JSONL (trade history)
- JSON (positions, config)
- systemd journal (service logs)

## Project Structure

```
aitrader/
├── active_trader.py              # Main service entry point
├── requirements.txt              # Python dependencies
├── .env                          # API keys (not in git)
├── manage_services.sh            # Service management script
│
├── configs/
│   └── default_config.json       # Agent configuration
│
├── prompts/
│   ├── agent_prompt.py           # Trading strategy & behavior
│   └── technical_analysis_guide.md
│
├── agent/
│   └── base_agent/
│       └── base_agent.py         # AI agent implementation
│
├── tools/
│   ├── alpaca_trading.py         # Trading functions
│   ├── alpaca_data_feed.py       # Market data functions
│   ├── technical_indicators.py   # TA calculations
│   ├── ta_helper.py              # TA utilities
│   └── general_tools.py          # Utility functions
│
├── agent_tools/
│   ├── tool_alpaca_data.py       # MCP data server
│   └── tool_alpaca_trade.py      # MCP trade server
│
├── logs/
│   ├── active_trader_stdout.log  # Main log
│   ├── active_trader_stderr.log  # Error log
│   └── alpaca_*.log              # MCP logs
│
├── data/
│   ├── runtime_env.json          # Runtime state
│   └── agent_data/
│       └── deepseek-chat-v3.1/
│           ├── log/              # Decision logs by date
│           ├── trades/           # Trade history by date
│           └── position/         # Position state
│
└── systemd services (in /etc/systemd/system/):
    ├── active-trader.service     # Main service
    ├── alpaca-data.service       # Data MCP service
    └── alpaca-trade.service      # Trade MCP service
```

## FAQ

**Q: Can I trade during pre-market or post-market hours?**
A: No, extended hours trading is currently disabled. The system only trades during regular market hours (9:30 AM - 4:00 PM ET).

**Q: What happens if the service crashes?**
A: systemd automatically restarts the service with exponential backoff. Check logs to identify the issue.

**Q: Can I run multiple instances?**
A: Not recommended. Multiple instances would compete for the same portfolio and could cause conflicts.

**Q: How do I change the trading strategy?**
A: Edit `prompts/agent_prompt.py` to modify the AI's trading behavior and rules.

**Q: What's the cost of running this?**
A: Minimal - DeepSeek API is ~$0.14 per million tokens. Alpaca paper trading is free. Most days cost <$0.50 in API fees.

**Q: Can I use this with a live trading account?**
A: Technically yes, but NOT RECOMMENDED until thoroughly tested. This is experimental software. Use paper trading only.

**Q: How do I add new technical indicators?**
A: Add calculations to `tools/technical_indicators.py` and update the agent prompt to use them.

**Q: What symbols can it trade?**
A: Any US stocks available on Alpaca. Configure allowed symbols in the agent prompt or code.

**Q: Does it handle dividends, splits, etc?**
A: Basic support via Alpaca API. Always verify positions after corporate actions.

**Q: Can I backtest strategies?**
A: Not currently. This is a live trading system. Consider building a separate backtesting module.

## Contributing

This is a personal trading project. If you fork it:
1. Never commit API keys or .env files
2. Test thoroughly with paper trading
3. Document any changes
4. Use at your own risk

## Disclaimer

⚠️ **IMPORTANT DISCLAIMER** ⚠️

This software is provided for educational and research purposes only. 

- **No warranty**: This software is provided "as is" without any warranties
- **Trading risk**: Trading involves substantial risk of loss
- **Not financial advice**: This is not investment advice
- **Use at your own risk**: You are solely responsible for any trades
- **Paper trading recommended**: Use paper trading accounts only
- **No liability**: Authors accept no liability for financial losses

Always consult with a qualified financial advisor before making investment decisions.

## License

This project is for personal use. See LICENSE file for details.

---

**Last Updated:** November 5, 2025  
**Version:** 2.0 (Regular Market Hours Only)  
**Status:** Production (Paper Trading)

## Troubleshooting

### Service Issues

**Service won't start:**
```bash
# Check if MCP services are running first
sudo systemctl status alpaca-data.service
sudo systemctl status alpaca-trade.service

# Check for errors in logs
sudo journalctl -u active-trader.service -n 100

# Verify environment variables
sudo systemctl show active-trader.service --property=Environment

# Test manual start to see errors
python /home/mfan/work/aitrader/active_trader.py
```

**Service keeps restarting:**
```bash
# Check crash logs
sudo journalctl -u active-trader.service --since "1 hour ago" | grep -i error

# Check systemd restart count
systemctl show active-trader.service --property=NRestarts

# Review stderr logs
tail -50 logs/active_trader_stderr.log
```

**MCP connection errors:**
```bash
# Verify MCP services are listening
lsof -nP -iTCP:8004,8005 -sTCP:LISTEN

# Restart MCP services
sudo systemctl restart alpaca-data.service
sudo systemctl restart alpaca-trade.service

# Wait for services to initialize
sleep 10

# Restart active trader
sudo systemctl restart active-trader.service
```

### Trading Issues

**No trades being executed:**
```bash
# Check if market is open
date -d "$(TZ='America/New_York' date +'%Y-%m-%d %H:%M:%S')"

# Verify agent is in trading mode (not sleep)
tail -20 logs/active_trader_stdout.log | grep -E "(SLEEP|TRADING|MARKET)"

# Check agent decisions
ls -lth data/agent_data/deepseek-chat-v3.1/log/$(date +%Y-%m-%d)/ | head

# Review last agent decision
tail -100 data/agent_data/deepseek-chat-v3.1/log/$(date +%Y-%m-%d)/*.log | tail -50
```

**Positions not closing at 3:55 PM:**
```bash
# Check current positions
cat data/agent_data/deepseek-chat-v3.1/position/position.jsonl | tail -1 | jq

# Review close-of-day logs
grep "END OF DAY" logs/active_trader_stdout.log | tail -5

# Check for close errors
grep -i "close.*error" logs/active_trader_stderr.log | tail -10
```

**API errors:**
```bash
# Check API keys are set
grep -c "ALPACA_API_KEY\|DEEPSEEK_API_KEY" .env

# Test Alpaca connection
python -c "import os; from dotenv import load_dotenv; load_dotenv(); \
  print('API Key:', os.getenv('ALPACA_API_KEY')[:10] + '...')"

# Check API rate limits in logs
grep -i "rate limit" logs/active_trader_stdout.log
```

### Performance Issues

**High CPU usage during sleep:**
```bash
# Check sleep mode status
grep "Sleep mode active" logs/active_trader_stdout.log | tail -5

# Verify sleep function is working
grep "Sleeping until" logs/active_trader_stdout.log | tail -3

# Check process CPU
ps aux | grep active_trader.py | grep -v grep
```

**Memory leaks:**
```bash
# Monitor memory over time
watch -n 5 'systemctl show active-trader.service --property=MemoryCurrent'

# Check for memory errors
dmesg | grep -i "active_trader\|python" | grep -i "memory\|oom"

# Review systemd memory limits
systemctl show active-trader.service --property=MemoryLimit
```

### Log Analysis

**Find errors in logs:**
```bash
# Last 100 errors
sudo journalctl -u active-trader.service -p err -n 100

# Errors from today
sudo journalctl -u active-trader.service -p err --since today

# Search for specific error
sudo journalctl -u active-trader.service | grep -i "connection refused"
```

**Analyze trading patterns:**
```bash
# Count trades per day
for file in data/agent_data/deepseek-chat-v3.1/trades/*.jsonl; do
  echo "$(basename $file): $(wc -l < $file) trades"
done

# Find most traded symbols
cat data/agent_data/deepseek-chat-v3.1/trades/*.jsonl | \
  jq -r '.symbol' | sort | uniq -c | sort -rn | head -10
```

## System Requirements

### Hardware
- **CPU**: 2+ cores recommended (minimal usage during sleep mode)
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 10GB free space for logs and trade history
- **Network**: Stable internet connection for API calls

### Software
- **OS**: Linux (Ubuntu 20.04+ or similar)
- **Python**: 3.8 or higher
- **systemd**: For service management
- **Dependencies**: See `requirements.txt`

### API Accounts
- **Alpaca Markets**: Paper trading account (free)
  - Sign up at: https://alpaca.markets
  - Enable paper trading in dashboard
  - Generate API keys
  
- **DeepSeek**: AI API access
  - Sign up at: https://platform.deepseek.com
  - Generate API key
  - Note: Minimal cost for API usage (~$0.14 per million tokens)

## Best Practices

### For Production Use

1. **Start with paper trading**
   - Test thoroughly with paper account
   - Monitor for at least 1-2 weeks
   - Review all trades and decisions
   - Only move to live trading after validation

2. **Monitor daily**
   - Check logs every morning
   - Review previous day's trades
   - Verify positions are flat overnight
   - Monitor P&L trends

3. **Set appropriate limits**
   - Configure position size limits
   - Set daily loss limits
   - Limit max positions
   - Use stop losses on all trades

4. **Regular maintenance**
   - Review logs weekly
   - Archive old trade data
   - Check service health
   - Update dependencies monthly

5. **Backup strategy**
   - Backup configuration files
   - Save position and trade history
   - Document any custom changes
   - Keep emergency stop procedure ready

### For Development/Testing

1. **Use paper trading exclusively**
   - Never test with live account
   - Monitor resource usage
   - Test edge cases (holidays, pre-market, etc.)

2. **Log analysis**
   - Enable verbose logging
   - Review AI decisions
   - Analyze trade patterns
   - Monitor for errors

3. **Iterate safely**
   - Make one change at a time
   - Test thoroughly before deploying
   - Keep rollback plan ready
   - Document all changes

## Security Considerations

### API Key Security
```bash
# Store keys in .env file (never commit to git)
echo ".env" >> .gitignore

# Set restrictive permissions
chmod 600 .env

# Use environment variables only
# Never hardcode keys in source code
```

### Service Isolation
```bash
# Run service as non-root user
# Already configured in systemd service file

# Limit service permissions
# Configured in service: NoNewPrivileges=true

# Monitor service access
sudo journalctl -u active-trader.service | grep -i "permission\|denied"
```

### Network Security
- Use HTTPS for all API calls (already configured)
- Consider firewall rules for outbound connections
- Monitor for unusual API activity
- Rotate API keys periodically

## Performance Optimization

### Memory Management
- Logs auto-rotate via systemd (default: 10MB max)
- Trade history stored as JSONL (efficient append-only)
- Position state uses minimal memory
- Garbage collection optimized for long-running process

### CPU Efficiency
- **Sleep mode**: >95% CPU reduction when markets closed
- **Intelligent scheduling**: Wakes only when needed
- **Async operations**: Non-blocking API calls
- **Efficient polling**: Variable intervals based on market activity

### Storage Management
```bash
# Archive old logs (older than 30 days)
find data/agent_data/*/log/ -type f -mtime +30 -exec gzip {} \;

# Clean up old trades (older than 90 days)
find data/agent_data/*/trades/ -type f -mtime +90 -delete

# Monitor disk usage
du -sh data/
```

## Documentation

### Additional Resources
- **`SYSTEMD_SERVICE_SETUP.md`**: Detailed service configuration
- **`INTELLIGENT_SLEEP_MODE.md`**: Sleep mode implementation details
- **`REGULAR_HOURS_UPDATE.md`**: Regular market hours configuration
- **`DAY_TRADING_QUICKSTART.md`**: Trading strategy guide
- **`TECHNICAL_ANALYSIS_QUICKSTART.md`**: Technical indicator usage
- **`BELLAFIORE_PRINCIPLES_APPLIED.md`**: Trading principles

### Logs Location
```
logs/
├── active_trader_stdout.log      # Main application log
├── active_trader_stderr.log      # Error log
├── alpaca_data_mcp.log           # Data service log
└── alpaca_trade_mcp.log          # Trade service log

data/agent_data/deepseek-chat-v3.1/
├── log/YYYY-MM-DD/               # Daily agent decision logs
├── trades/YYYY-MM-DD_trades.jsonl # Daily trade history
└── position/position.jsonl        # Position state history
```
