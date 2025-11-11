# Active Trader - Autonomous Day Trading System

## Overview

The Active Trader is an **autonomous AI-powered day trading system** that runs continuously as a systemd service. It features intelligent sleep mode, regular market hours trading, momentum-based stock selection, and fully automated execution with comprehensive order verification:

### Key Features
- 🤖 **Autonomous Trading**: Fully automated buy/sell decisions using XAI Grok-4-latest AI
- 🎯 **Momentum-Based Selection**: Daily scans of 4,701 US stocks to find top 100 movers (50 gainers + 50 losers)
- ⏰ **Regular Market Hours Only**: Trades 9:30 AM - 4:00 PM ET (extended hours disabled)
- ✅ **Order Execution Verification**: Confirms all orders executed before marking trading round complete
- 💤 **Intelligent Sleep Mode**: Minimal CPU usage when markets are closed
- 🔄 **Continuous Operation**: Runs 24/7 as systemd service with automatic restarts
- 📊 **Real-time Analysis**: Technical indicators, market data, and dynamic watchlist management
- 🎯 **Day Trading Strategy**: All positions closed by 3:55 PM ET daily
- 🛡️ **Risk Management**: Position sizing, stop-losses, profit targets, and Elder's 6% Rule

## Quick Start

### Prerequisites

1. **Environment Setup**:
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Configure environment variables in .env
   XAI_API_KEY=your_xai_grok_api_key_here
   XAI_API_BASE=https://api.x.ai/v1
   ALPACA_API_KEY=your_alpaca_key
   ALPACA_SECRET_KEY=your_alpaca_secret
   ALPACA_DATA_HTTP_PORT=8004
   ALPACA_TRADE_HTTP_PORT=8005
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

**Pre-Market (9:00 - 9:30 AM ET):**
```
1. Run momentum scan of 4,701 US stocks (NASDAQ, NYSE, AMEX, ARCA)
2. Filter by: Price ≥$5, Market Cap ≥$2B, Volume ≥10M
3. Select top 50 gainers + top 50 losers = 100 stocks
4. Cache results to SQLite database (2-3ms query performance)
5. Initialize agent with dynamic momentum watchlist
```

**During Market Hours (9:30 AM - 4:00 PM ET):**
```
1. Check portfolio positions via Alpaca MCP
2. Scan top momentum opportunities (pre-scanned with TA)
3. Analyze technical indicators (RSI, MACD, EMA, VWAP, Bollinger Bands)
4. AI agent (Grok-4-latest) analyzes with real-time X/Twitter intelligence
5. Make autonomous buy/sell/hold decisions (no permission required)
6. Execute trades immediately via Alpaca API
7. Wait 3 seconds for pending orders to execute
8. Verify order execution status (filled/pending/failed)
9. Get updated portfolio summary from Alpaca
10. Mark trading round as COMPLETED
11. Repeat every 2 minutes
12. Close all positions at 3:55 PM ET
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

### 🎯 Momentum-Based Stock Selection
- **Daily Momentum Scan**: Scans 4,701 US stocks every morning (9:00-9:30 AM)
- **Quality Filters**: Price ≥$5, Market Cap ≥$2B, Volume ≥10M for liquidity
- **Top Movers**: Selects 50 best gainers + 50 best losers (100 total)
- **SQLite Cache**: Fast 2-3ms queries, stores TA indicators per stock
- **Market Regime Detection**: Monitors SPY/QQQ to align strategy
- **Daily Refresh**: Automatic watchlist update before market open

### 🤖 Autonomous Trading with Execution Verification
- **Zero human intervention**: AI agent makes and executes all trading decisions
- **No permission seeking**: Agent executes trades immediately when signals warrant
- **Order execution verification**: Checks order status (filled/pending/failed) before completing round
- **Portfolio synchronization**: Updates portfolio summary after each trade execution
- **3-second wait period**: Ensures pending orders complete before verification
- **Round completion tracking**: Explicitly marks trading rounds as COMPLETED
- **Continuous operation**: Runs 24/7 with intelligent sleep during closed hours
- **Auto-restart**: systemd ensures service recovers from crashes

### ⏰ Market Hours Intelligence
- **Regular hours only**: Trades 9:30 AM - 4:00 PM ET (no pre-market/post-market)
- **Smart scheduling**: Wakes up 5 minutes before market open (9:25 AM)
- **Automatic detection**: Knows weekends, holidays, and market status
- **Sleep mode**: Minimal CPU usage when markets closed (~11+ hours daily)

### 📊 Technical Analysis & Market Intelligence
- **Real-time indicators**: RSI, MACD, EMA (20/50), VWAP, Bollinger Bands, ADX, Stochastic
- **Multi-timeframe**: 1-min, 5-min, 15-min bars for analysis
- **Signal strength**: Weighted scoring system (0-5) for trade quality (A+ = 5, B+ = 2)
- **Volume analysis**: Confirms price movements with volume (minimum 10M for entries)
- **Pre-scanned opportunities**: Top 15 momentum setups provided to agent at start
- **XAI Grok Integration**: Real-time X/Twitter sentiment and news analysis
- **Market regime alignment**: Monitors SPY/QQQ trends to avoid counter-trend trades

### 🎯 Day Trading Strategy
- **No overnight holds**: All positions closed by 3:55 PM ET
- **Position sizing**: Risk management based on portfolio size
- **Stop losses**: Automatic 2×ATR stop loss on all positions
- **Profit targets**: Take profits at resistance or momentum exhaustion
- **Trend following**: Focuses on momentum and breakout strategies

### 🛡️ Risk Management (Elder's Trading Rules)
- **6% Monthly Rule**: Trading suspended if monthly drawdown exceeds 6%
- **2% Per-Trade Rule**: Maximum 2% account risk per trade
- **6% Total Portfolio Risk**: Combined risk across all positions ≤6%
- **Position limits**: Maximum position size constraints per symbol
- **Daily loss limits**: Stop trading if daily losses exceed threshold
- **Diversification**: Limits per-symbol exposure (momentum watchlist rotation)
- **Real-time monitoring**: Continuous position and P&L tracking via Alpaca
- **Automatic stop losses**: 2×ATR stops on all positions
- **Emergency stop**: Close all positions if risk limits breached

### ✅ Order Execution Verification (New in v2.1)
- **3-second wait period**: Allows pending orders to execute before verification
- **Order status check**: Queries `get_orders()` MCP tool for recent order status
- **Execution summary**: Counts filled, pending, and failed orders
- **Portfolio refresh**: Gets updated portfolio summary after trades
- **Round completion**: Explicitly marks each trading round as COMPLETED
- **Detailed logging**: Shows execution status for each order:
  - ✅ Executed orders (filled/partially_filled)
  - ⏳ Pending orders (pending_new/accepted/new)
  - ❌ Failed orders (canceled/rejected/expired)
- **Audit trail**: Complete verification from decision → execution → completion

### 📝 Logging & Monitoring
- **Comprehensive logs**: All decisions, trades, execution verification, and errors logged
- **Service logs**: systemd journal with rotation
- **Trade history**: JSONL files for each trading day with P&L tracking
- **Position tracking**: Persistent position state via Alpaca (no local files)
- **Performance metrics**: Daily P&L, win rate, trade statistics
- **Execution reports**: Detailed order execution verification in agent logs

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
      "name": "xai-grok-4-latest",
      "signature": "xai-grok-4-latest",
      "basemodel": "grok-4-latest",
      "openai_base_url": "${XAI_API_BASE}",
      "openai_api_key": "${XAI_API_KEY}",
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
- `max_steps`: Maximum AI reasoning steps per cycle (10 recommended for fast execution)
- `max_retries`: Retry attempts for failed API calls (3)
- `initial_cash`: Starting capital for paper trading ($100,000)
- `basemodel`: AI model to use (grok-4-latest - most powerful Grok 4)
- `signature`: Agent signature for data organization (xai-grok-4-latest)
- `openai_base_url`: XAI API endpoint (${XAI_API_BASE} from environment)
- `openai_api_key`: XAI API key (${XAI_API_KEY} from environment)

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
🔄 TRADING CYCLE #145 - REGULAR SESSION 🟢
⏰ 2025-11-11 10:30:15 ET (Monday)
================================================================================

� COMPREHENSIVE TRADING ANALYSIS for 2025-11-11
================================================================================

PART 1: CURRENT PORTFOLIO STATUS
Step 1 – get_portfolio_summary():
{
  "cash": 98450.23,
  "portfolio_value": 122724.73,
  "buying_power": 196900.46,
  "position_count": 3
}

Step 2 – get_account_info():
{
  "account_number": "PA33238F1LAW",
  "status": "ACTIVE",
  "cash": 98450.23,
  "buying_power": 196900.46
}

Step 3 – get_positions():
{
  "AAPL": {"qty": 50, "avg_entry_price": 175.20, "current_price": 177.00},
  "TSLA": {"qty": 25, "avg_entry_price": 245.80, "current_price": 251.58},
  "NVDA": {"qty": 15, "avg_entry_price": 485.30, "current_price": 495.15}
}

PART 2: MARKET OPPORTUNITIES (Pre-scanned with Technical Analysis)
🎯 TOP 15 TRADING OPPORTUNITIES (Strength ≥2):

#1 🟢 BW - BUY (Strength: 5)
   Current Price: $6.90
   Details: {
     "signal": "BUY",
     "strength": 5,
     "change_pct": +16.95,
     "volume": 15644036,
     "rsi": 68.5,
     "macd_signal": "bullish"
   }

#2 🟢 PLTR - BUY (Strength: 4)
   Current Price: $45.23
   [... 13 more opportunities ...]

================================================================================

🤖 AGENT ANALYSIS:
"Analyzing momentum opportunities... AAPL showing profit (+$90), will take 
partial. NVDA approaching resistance, holding. TSLA strong trend, holding.
BW has A+ setup (strength 5) with high volume confirmation. Entering BW..."

🔧 TOOL EXECUTION:
   ├─ sell("AAPL", 25) → Order #abc123 submitted
   ├─ buy("BW", 500) → Order #def456 submitted
   └─ Tool results: {"success": true, "order_id": "def456"}

✅ Received stop signal, trading session ended
⏳ Waiting 3 seconds for pending orders to execute...

================================================================================
📊 TRADING SESSION SUMMARY - 2025-11-11
================================================================================
🔍 Verifying order execution...
   ✅ SELL 25 AAPL - FILLED
   ✅ BUY 500 BW - FILLED

📊 Order Execution Summary:
   ✅ Executed: 2
   ⏳ Pending: 0
   ❌ Failed: 0

💼 Updated Portfolio:
   💰 Cash: $99,285.50
   📈 Portfolio Value: $125,893.25
   📊 Active Positions: 4

✅ TRADING ROUND COMPLETED
   All orders processed and portfolio updated
================================================================================

================================================================================
📊 CYCLE #145 SUMMARY (REGULAR)
================================================================================
📅 Date: 2025-11-11
⏰ Completion time: 2025-11-11 10:32:18

✅ TRADING ROUND COMPLETED WITH ORDERS EXECUTED
   Orders have been processed by Alpaca
   Check agent logs for detailed execution report
================================================================================

⏳ Next trading cycle at: 2025-11-11 10:34:00
💤 Sleeping for 2 minutes...
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
┌─────────────────────────────────────────────────────────────────┐
│                     Active Trader Service                        │
│                     (active_trader.py)                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Momentum Scanner (9:00-9:30 AM Daily)            │  │
│  │  • Scans 4,701 US stocks (NASDAQ/NYSE/AMEX/ARCA)        │  │
│  │  • Filters: Price≥$5, MCap≥$2B, Vol≥10M                 │  │
│  │  • Selects top 50 gainers + 50 losers                    │  │
│  │  • Caches to SQLite (2-3ms queries)                      │  │
│  └──────────────────┬───────────────────────────────────────┘  │
│                     │                                            │
│  ┌──────────────────▼───────────────────────────────────────┐  │
│  │            BaseAgent (XAI Grok-4-latest)                 │  │
│  │  • Momentum stock analysis (dynamic 100-stock watchlist) │  │
│  │  • Real-time X/Twitter intelligence                      │  │
│  │  • Technical analysis (RSI, MACD, EMA, VWAP, etc)       │  │
│  │  • Trading decisions (autonomous)                        │  │
│  │  • Risk management (Elder's 6% Rule)                    │  │
│  │  • Order execution verification ✅                       │  │
│  └──────────────────┬───────────────────────────────────────┘  │
│                     │                                            │
│  ┌──────────────────▼───────────────────────────────────────┐  │
│  │      Execution Verification System (NEW v2.1)            │  │
│  │  • 3-second wait for order execution                     │  │
│  │  • Query order status (filled/pending/failed)            │  │
│  │  • Get updated portfolio summary                         │  │
│  │  • Mark trading round COMPLETED                          │  │
│  │  • Detailed execution logging                            │  │
│  └──────────────────┬───────────────────────────────────────┘  │
│                     │                                            │
│  ┌──────────────────▼───────────────────────────────────────┐  │
│  │           Market Hours Controller                         │  │
│  │  • Time detection (9:30 AM - 4:00 PM ET)                │  │
│  │  • Intelligent sleep mode                                │  │
│  │  • Wake/sleep scheduling                                 │  │
│  │  • Daily momentum scan trigger (9:00-9:30 AM)           │  │
│  │  • Position close enforcement (3:55 PM)                  │  │
│  └──────────────────┬───────────────────────────────────────┘  │
└────────────────────┼────────────────────────────────────────────┘
                     │
         ┌───────────┴──────────┐
         │                       │
    ┌────▼─────┐          ┌─────▼────┐
    │  Alpaca  │          │  Alpaca  │
    │   Data   │          │  Trade   │
    │ Service  │          │ Service  │
    │ (MCP)    │          │  (MCP)   │
    │ :8004    │          │  :8005   │
    │          │          │          │
    │ • Quotes │          │ • Orders │
    │ • Bars   │          │ • Trades │
    │ • TA     │          │ • Status │
    └────┬─────┘          └─────┬────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │   Alpaca    │
              │  Markets    │
              │  Paper API  │
              │ $100k Account
              └─────────────┘
```

### Data Flow

**Pre-Market (9:00 - 9:30 AM):**
```
1. Wake-up signal (9:25 AM if not already running scan)
2. Run momentum scan (9:00-9:30 AM window)
   ├─ Fetch bars for 4,701 stocks from Alpaca
   ├─ Calculate technical indicators (RSI, MACD, etc)
   ├─ Filter: Price≥$5, MCap≥$2B, Vol≥10M
   ├─ Rank by price change percentage
   ├─ Select top 50 gainers + 50 losers
   ├─ Cache to SQLite with TA data
   └─ Duration: ~5 seconds
3. Initialize agent with 100-stock momentum watchlist
4. Wait for market open (9:30 AM)
```

**Market Open (9:30 AM):**
```
1. Initialize MCP connections
2. Load positions from Alpaca
3. Begin trading cycle loop (every 2 minutes)
   ├─ Prefetch portfolio context:
   │  ├─ get_portfolio_summary()
   │  ├─ get_account_info()
   │  └─ get_positions()
   ├─ Scan momentum opportunities (pre-scanned TA):
   │  ├─ Get trading signals for watchlist stocks
   │  ├─ Filter by signal strength ≥2 (B+ setups)
   │  └─ Present top 15 opportunities to agent
   ├─ AI analyzes (Grok-4-latest):
   │  ├─ Review current positions
   │  ├─ Check X/Twitter news via XAI
   │  ├─ Analyze momentum opportunities
   │  ├─ Apply technical analysis
   │  └─ Make buy/sell/hold decisions
   ├─ Execute trades via Alpaca:
   │  ├─ buy() or sell() MCP tools
   │  ├─ Set IF_TRADE flag when orders placed
   │  └─ Orders submitted immediately
   ├─ Agent sends WORK_COMPLETE signal
   ├─ Wait 3 seconds for order execution
   ├─ Verify execution (NEW):
   │  ├─ Call get_orders() for recent orders
   │  ├─ Count filled/pending/failed
   │  ├─ Log execution status per order
   │  ├─ Call get_portfolio_summary()
   │  └─ Display updated portfolio
   ├─ Mark round COMPLETED
   └─ Log all activities
4. Repeat every 2 minutes until 3:55 PM
```

**Market Close (4:00 PM):**
```
1. Detect close time (3:55 PM)
2. Close ALL open positions
   ├─ close_position() for each symbol
   ├─ Wait 3 seconds for execution
   └─ Verify all orders filled
3. Verify all positions flat via Alpaca
4. Calculate daily P&L from trade history
5. Save trade history to JSONL
6. Mark daily session COMPLETED
7. Enter sleep mode
8. Calculate next wake time (9:25 AM next day)
9. Next day: Check if momentum scan needed (9:00-9:30 AM)
```

### Technology Stack

**Core:**
- Python 3.8+
- systemd (service management)
- pytz (timezone handling)

**AI/ML:**
- XAI Grok-4-latest (trading decisions with X/Twitter intelligence)
- OpenAI-compatible API client
- Real-time news and sentiment analysis

**Market Data:**
- Alpaca Markets API
- Model Context Protocol (MCP) servers
- Real-time quotes and bars

**Technical Analysis:**
- TA-Lib or pandas-ta
- Custom indicator calculations
- Multi-timeframe analysis

**Storage:**
- SQLite (momentum cache, 2-3ms queries)
- JSONL (trade history with execution verification)
- JSON (config, runtime state)
- systemd journal (service logs)
- Alpaca API (positions, orders, account - no local position tracking)

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
│   ├── momentum_scanner.py       # Daily momentum scan (4,701 stocks)
│   ├── momentum_cache.py         # SQLite cache for momentum data
│   ├── alpaca_trading.py         # Trading functions
│   ├── alpaca_data_feed.py       # Market data functions
│   ├── technical_indicators.py   # TA calculations
│   ├── ta_helper.py              # TA utilities
│   ├── elder_risk_manager.py     # Elder's 6% Rule implementation
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
│       └── xai-grok-4-latest/
│           ├── momentum_cache.db # SQLite cache (100 stocks, TA data)
│           ├── log/              # Decision logs by date
│           ├── trades/           # Trade history by date (with execution verification)
│           └── position/         # DEPRECATED (Alpaca manages positions)
│
└── systemd services (in /etc/systemd/system/):
    ├── active-trader.service     # Main service
    ├── alpaca-data.service       # Data MCP service
    └── alpaca-trade.service      # Trade MCP service
```

## Momentum Scanning System

### How It Works

The momentum scanning system is a **daily pre-market process** that identifies the best trading opportunities before the market opens:

**1. Universe (4,701 US Stocks)**
- NASDAQ, NYSE, AMEX, ARCA exchanges
- Excludes: OTC, pink sheets, leveraged/inverse ETFs

**2. Quality Filters**
- **Price ≥ $5**: Avoids penny stock volatility
- **Market Cap ≥ $2B**: Sweet spot for quality movers (cuts micro-caps)
- **Volume ≥ 10M**: Ensures liquidity for entries/exits

**3. Momentum Selection**
- Scans previous trading day's performance
- Ranks all stocks by price change percentage
- Selects **Top 50 Gainers** (highest % gain)
- Selects **Top 50 Losers** (largest % loss)
- Total: **100 stocks** for the day

**4. Technical Analysis**
- Calculates indicators for each stock:
  - RSI (14-period Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - EMA (20 and 50-period)
  - VWAP (Volume Weighted Average Price)
  - Bollinger Bands
  - ADX (Average Directional Index)
  - Stochastic Oscillator

**5. SQLite Cache**
- Stores all 100 stocks with TA data
- Lightning-fast queries (2-3ms)
- Expires automatically after market close
- Next day: Fresh scan with new data

**6. Agent Integration**
- Agent initializes with 100-stock watchlist
- Pre-scans for trading opportunities at start
- Focuses on momentum stocks only
- Daily refresh ensures fresh candidates

### Performance Metrics

**Scan Performance:**
- Total stocks analyzed: 4,701
- High-volume candidates: ~200-250 typically
- Final watchlist: 100 (50 gainers + 50 losers)
- Scan duration: ~5 seconds
- Cache query time: 2-3ms

**Example Scan Results (Nov 10, 2025):**
```
✅ MOMENTUM SCAN COMPLETE
   📈 Gainers: 50
   📉 Losers: 50
   📊 Total Watchlist: 100 stocks
   🎯 Market Regime: NEUTRAL
   ⏱️  Scan Duration: 5.14s
   
   🏆 Best Gainer: BW (+16.95%, $6.90, 15.6M volume)
   💔 Worst Loser: BTDR (-23.19%, $17.65, 12.6M volume)
```

**Watchlist Examples:**
- Gainers: BW, OPEN, NVTS, OGN, XPEV, SNDK, PZZA, ENPH, LYFT, RIVN...
- Losers: BTDR, SOFI, PLTR, SNAP, RKT, MP, PRMB, U, EXK...

### Market Regime Detection

The scanner also monitors **market regime** via SPY (S&P 500) and QQQ (NASDAQ):

**Bullish Regime:**
- SPY/QQQ both trending up
- Strategy: Focus on momentum longs (gainers)
- Risk: Lighter position sizing on shorts

**Bearish Regime:**
- SPY/QQQ both trending down  
- Strategy: Focus on momentum shorts (losers)
- Risk: Lighter position sizing on longs

**Neutral Regime:**
- Mixed or ranging market
- Strategy: Trade both sides with confirmation
- Risk: Require stronger technical signals

### Daily Schedule

**9:00 - 9:30 AM ET (Daily Refresh Window):**
```
IF (current_date != last_scan_date):
    1. Run momentum scan
    2. Cache 100 stocks to SQLite
    3. Force agent reinitialization
    4. Load new watchlist
    5. Update last_scan_date
```

**First Startup (No Cache):**
```
IF (no cache exists):
    1. Run momentum scan immediately
    2. Cache results
    3. Initialize agent with watchlist
    4. Begin trading when market opens
```

### Testing

Use `test_momentum_watchlist.py` to validate the system:

```bash
# Test with existing cache
python test_momentum_watchlist.py

# Force a fresh scan
python test_momentum_watchlist.py --force-scan
```

**Test Output:**
```
================================================================================
TEST 1: CACHE LOADING
================================================================================
✅ Cache file exists (45,056 bytes)
✅ Loaded 100 stocks from cache

================================================================================
TEST 2: MOMENTUM SCAN  
================================================================================
✅ Alpaca Data Feed initialized (feed: iex)
✅ MOMENTUM SCAN COMPLETE
   Total Scanned: 4,701
   High Volume: 219
   Watchlist: 100 stocks
   Duration: 5.14s

================================================================================
VALIDATION RESULTS
================================================================================
✅ Watchlist validation PASSED
   Total symbols: 100
   ✅ No duplicate symbols
   ✅ All symbols have valid format

🎉 TEST PASSED - System ready for trading
```

## FAQ

**Q: How often does the momentum scan run?**
A: Once per day during the 9:00-9:30 AM ET window. Cached results used for the entire trading day.

**Q: Can I customize the filters (price, volume, market cap)?**
A: Yes, edit `tools/momentum_scanner.py` - adjust `min_price`, `min_market_cap`, `min_volume` parameters.

**Q: What if the scan fails?**
A: System logs warning and continues with previous day's cache. Retries next day.

**Q: How many stocks are scanned total?**
A: 4,701 US stocks across NASDAQ, NYSE, AMEX, and ARCA exchanges.

**Q: Can I trade during pre-market or post-market hours?**
A: No, extended hours trading is currently disabled. The system only trades during regular market hours (9:30 AM - 4:00 PM ET).

**Q: What happens if the service crashes?**
A: systemd automatically restarts the service with exponential backoff. Check logs to identify the issue.

**Q: Can I run multiple instances?**
A: Not recommended. Multiple instances would compete for the same portfolio and could cause conflicts.

**Q: How do I change the trading strategy?**
A: Edit `prompts/agent_prompt.py` to modify the AI's trading behavior and rules.

**Q: What's the cost of running this?**
A: **XAI Grok-4-latest:** Input: $10/million tokens, Output: $30/million tokens. Typical trading day: ~100K tokens input + ~50K tokens output = ~$2.50/day. **Alpaca paper trading:** Free. **Total:** ~$2.50/day (~$50/month for 20 trading days).

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

**Last Updated:** November 11, 2025  
**Version:** 2.1 (Momentum Scanner + Order Execution Verification)  
**Status:** Production (Paper Trading with $100k Account)  
**AI Model:** XAI Grok-4-latest (most powerful Grok 4)

### Changelog

**v2.1 (Nov 11, 2025):**
- ✅ Added momentum scanning system (4,701 stocks → 100 best)
- ✅ Implemented order execution verification
- ✅ Added 3-second wait period for order completion
- ✅ Enhanced logging with execution status per order
- ✅ Upgraded to XAI Grok-4-latest AI model
- ✅ Added Elder's Risk Management (6% Rule, 2% Rule)
- ✅ SQLite cache for momentum data (2-3ms queries)
- ✅ Daily automatic watchlist refresh
- ✅ Market regime detection (SPY/QQQ trends)

**v2.0 (Nov 5, 2025):**
- Regular market hours only (9:30 AM - 4:00 PM ET)
- Intelligent sleep mode (CPU efficiency)
- Disabled pre-market and post-market trading
- systemd service integration

**v1.0 (Initial):**
- Basic autonomous trading
- Fixed watchlist (NASDAQ 100)
- DeepSeek AI integration

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
  
- **XAI (Grok)**: AI API access
  - Sign up at: https://x.ai/api
  - Generate API key (requires X Premium+ subscription)
  - Pricing: Input $10/M tokens, Output $30/M tokens
  - Typical cost: ~$2.50 per trading day (~$50/month)

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
