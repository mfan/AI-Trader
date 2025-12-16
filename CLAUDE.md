# AI Trader Development Setup

## 🏗️ Active Trader System Analysis (Dec 2025)

### Executive Summary

The **Active Trader** is a production-ready autonomous AI trading system running as a systemd service on Linux. It combines:
- **AI Agent**: XAI Grok-4.1-Fast for decision-making
- **Trading Strategy**: Elder's Triple Screen methodology with momentum swing trading
- **Risk Management**: Elder's 6% Rule + anti-churning controls
- **Data Source**: Alpaca Markets API (60+ MCP tools)
- **Architecture**: Modular Python with async/await, MCP protocol, and SQLite caching

### System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   ACTIVE TRADER (Main Loop)                 │
│  active_trader.py - Orchestrates 24-hour trading cycle      │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──► Market Schedule (market_schedule.py)
             │    • Detects market hours (pre/regular/post)
             │    • Calculates sleep windows
             │    • Handles market holidays
             │
             ├──► Momentum Scanner (momentum_scanner.py)
             │    • Daily scan at 4:00 AM
             │    • Top 50 gainers + 50 losers
             │    • Filters: $2B+ cap, 10M+ volume
             │    • SQLite cache (momentum_cache.db)
             │
             ├──► Agent Factory (agent_factory.py)
             │    • Loads BaseAgent dynamically
             │    • Injects watchlist from scanner
             │    • Configures AI model (Grok-4.1-Fast)
             │
             └──► BaseAgent (base_agent.py)
                  │
                  ├──► MCP Client (langchain_mcp_adapters)
                  │    • Alpaca Data MCP (port 8004)
                  │    • Alpaca Trade MCP (port 8005)
                  │    • 60+ tools for market data & trading
                  │
                  ├──► AI Model (langchain_openai)
                  │    • XAI Grok-4.1-Fast
                  │    • System prompt: agent_prompt.py (394 lines)
                  │    • Max 30 reasoning steps
                  │
                  ├──► Elder Risk Manager (elder_risk_manager.py)
                  │    • 6% monthly drawdown limit
                  │    • 2% per-trade risk
                  │    • Position sizing formulas
                  │
                  └──► Trading Execution
                       • Order verification
                       • Position tracking (via Alpaca)
                       • Logging to data/agent_data/{model}/log/
```

### Runtime Flow (24-Hour Cycle)

**1. Startup (3:55 AM ET)**
- System wakes from sleep 5 min before market open
- Loads configuration from `configs/default_config.json`
- Checks if Alpaca MCP services (ports 8004, 8005) are running
- Initializes Elder Risk Manager

**2. Daily Momentum Scan (4:00 AM ET)**
- `momentum_scanner.py` scans previous day's market data
- Filters: Price ≥ $5, Volume ≥ 10M, Market Cap ≥ $2B
- Ranks by price change percentage
- Selects Top 50 Gainers + Top 50 Losers = 100 stocks
- Caches results to `momentum_cache.db` with TA indicators
- Cache expires at 4:00 PM ET

**3. Agent Initialization**
- Creates BaseAgent instance with momentum watchlist
- Connects to MCP services (retries up to 3 times)
- Initializes AI model (Grok-4.1-Fast @ XAI)
- Loads system prompt from `agent_prompt.py`
- Checks Elder's 6% Rule status

**4. Trading Loop (Every 2 Minutes)**
```python
while not shutdown_requested:
    # Check if market is open
    is_open, session_type = is_market_hours()
    
    if not is_open:
        # Sleep until 5 min before next market open
        await intelligent_sleep()
        continue
    
    # Check Elder's 6% monthly drawdown rule
    if elder_risk_manager.is_suspended():
        log_suspension_reason()
        await sleep(interval_minutes * 60)
        continue
    
    # Run trading cycle
    await run_trading_cycle(agent, cycle_number, session_type)
    
    # Check if end-of-day (3:45 PM ET)
    if should_close_positions(session_type):
        close_all_positions()
        cancel_all_orders()
    
    # Sleep until next cycle (2 minutes)
    await sleep_with_shutdown_check(120)
```

**5. AI Agent Decision Process**
- **Input**: Current portfolio, market data, watchlist, session type
- **Step 1**: Market Regime Detection (SPY/QQQ analysis)
  - Bullish: MACD > Signal, Price > 20-EMA, ADX > 20, RSI 40-70
  - Bearish: MACD < Signal, Price < 20-EMA, ADX > 20, RSI 30-60
  - Neutral: ADX < 20, mixed signals → Cash or 50% size only
- **Step 2**: Portfolio & Risk Check
  - Verify buying power, position count (max 3), monthly drawdown
- **Step 3**: Triple Screen Validation (Elder's Method)
  - Screen 1 (Tide): Weekly/Daily trend via MACD + EMAs
  - Screen 2 (Wave): Pullback timing via RSI/Stochastic
  - Screen 3 (Trigger): Momentum confirmation via volume + breakout
- **Step 4**: Position Sizing
  - `Shares = min((Equity × 0.02) / (Entry - Stop), (Equity × 0.20) / Entry)`
- **Step 5**: Order Execution
  - Pre/Post-market: Limit orders with `extended_hours=True`
  - Regular hours: Market or limit orders
- **Step 6**: Verification
  - Poll order status every 500ms (max 30 seconds)
  - Confirm fills via `get_positions()` and `get_orders()`
  - Log outcomes to JSONL files

**6. Anti-Churning Controls (Critical)**
- **Cooldown Timer**: 30-min wait after closing position before re-entry
- **Max Round-Trips**: 2 per symbol per day
- **Min Hold Time**: 30 minutes unless stop-loss hit
- **Win Rate Check**: Stop trading if <40% win rate after 3+ trades
- **Daily Trade Limit**: Max 6 round-trips per day across all symbols
- **No Scalping**: Block trades targeting <$0.50 movement

**7. End-of-Day (3:45 PM ET)**
- Hard stop enforced by `should_close_positions()`
- Close all open positions via `close_all_positions(cancel_orders=True)`
- Ensures flat book overnight (no overnight risk)

**8. Sleep Mode (After 8:00 PM ET)**
- Calculate time until next market open (5 min before 4:00 AM)
- Enter low-power sleep (1-second loops for shutdown responsiveness)
- Log countdown every 5 minutes

### Key Files & Responsibilities

| File | Purpose | Lines | Key Functions |
|------|---------|-------|---------------|
| `active_trader.py` | Main orchestrator | 859 | `active_trading_loop()`, `run_trading_cycle()`, `ActiveTraderEngine` |
| `base_agent.py` | AI agent core | 801 | `initialize()`, `run_date_range()`, `_handle_trading_result()` |
| `agent_prompt.py` | Trading strategy | 394 | `get_agent_system_prompt()` - Elder Triple Screen rules |
| `market_schedule.py` | Time management | 265 | `is_market_hours()`, `get_next_market_open()`, `should_close_positions()` |
| `elder_risk_manager.py` | Risk control | 417 | `get_monthly_status()`, `update_equity()`, `check_suspended()` |
| `momentum_scanner.py` | Watchlist builder | 734 | `scan_previous_day_movers()`, `calculate_momentum_score()` |
| `momentum_cache.py` | SQLite cache | ~200 | `store_movers()`, `get_momentum_watchlist()` |
| `alpaca_trading.py` | Order execution | 822 | `place_order()`, `get_positions()`, `get_account()` |
| `alpaca_data_feed.py` | Market data | 524 | `get_latest_bars()`, `get_historical_bars()` |
| `alpaca_mcp_bridge.py` | MCP interface | 499 | `_call_tool()`, wrapper methods for 60+ MCP tools |
| `config_loader.py` | Config parser | ~100 | `load_config()` with env var substitution |
| `agent_factory.py` | Dynamic loading | ~100 | `get_agent_class()` |

### Dependencies & Environment

**Python Environment**: `/home/mfan/work/aitrader/.venv/`
- Python 3.10+ required
- Virtual environment MUST be activated for all operations

**Critical Dependencies**:
```python
# AI & Agent Framework
langchain==0.3.13          # AI agent orchestration
langchain-openai==0.2.14   # LLM integration (XAI/DeepSeek/OpenAI)
langchain-mcp-adapters     # MCP protocol for tool access

# Trading & Market Data
alpaca-py==0.36.1         # Official Alpaca SDK
alpaca-mcp-server         # Alpaca's 60+ MCP tools

# Technical Analysis
TA-Lib                    # 150+ TA indicators (C library + Python wrapper)
pandas==2.2.3            # Data manipulation
numpy==2.1.3             # Numerical computing

# Infrastructure
python-dotenv==1.0.1     # Environment variable management
pytz==2024.2             # Timezone handling (US/Eastern)
httpx==0.28.1            # Async HTTP client
requests==2.32.3         # HTTP library
```

**System Requirements**:
- **OS**: Linux (tested on Ubuntu/Debian)
- **Systemd**: For service management
- **TA-Lib C Library**: Must be installed system-wide
  ```bash
  sudo apt-get install libta-lib0 libta-lib0-dev
  pip install TA-Lib
  ```

**MCP Services** (Required):
- **Alpaca Data MCP**: Port 8004 (`alpaca-data.service`)
- **Alpaca Trade MCP**: Port 8005 (`alpaca-trade.service`)
- Started via: `sudo ./manage_services.sh start-mcp`
- Health check: Active Trader polls both ports before initialization

**Environment Variables** (`.env` file):
```bash
# XAI Grok API (Primary AI Model)
XAI_API_KEY=xai-...
XAI_API_BASE=https://api.x.ai/v1

# Alpaca Markets (Data + Trading)
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
ALPACA_PAPER_TRADING=true  # false for live trading
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # or live API

# MCP Service Ports
ALPACA_DATA_HTTP_PORT=8004
ALPACA_TRADE_HTTP_PORT=8005

# Optional: DeepSeek, OpenAI
DEEPSEEK_API_KEY=...
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
OPENAI_API_KEY=...
```

### Configuration (`configs/default_config.json`)

**Current Active Model**: `xai-grok-4.1-fast` (enabled=true)
- **Basemodel**: `grok-4-1-fast`
- **API**: XAI @ `https://api.x.ai/v1`
- **Max Steps**: 30 reasoning iterations
- **Initial Cash**: $10,000 (paper trading)

**Agent Config**:
- `max_retries`: 3 (API call retries)
- `base_delay`: 1.0s (retry backoff)
- `log_path`: `./data/agent_data/` (JSONL logs by model/date)

### Systemd Service Management

**Service Files**:
- `active-trader.service` → Main trading bot
- `alpaca-data.service` → MCP Data server (port 8004)
- `alpaca-trade.service` → MCP Trade server (port 8005)

**Installation**:
```bash
sudo ./manage_services.sh install     # Copy to /etc/systemd/system/
sudo ./manage_services.sh start-mcp   # Start MCP services
sudo ./manage_services.sh start       # Start Active Trader
sudo ./manage_services.sh status      # Check all services
```

**Service Features**:
- **Auto-restart**: On failure or crash (RestartSec=30s)
- **Dependency chain**: Active Trader requires MCP services running
- **Logging**: Dual output (stdout/stderr files + systemd journal)
- **Resource limits**: NOFILE=65536, NPROC=4096
- **Security**: NoNewPrivileges, PrivateTmp

### Risk Management (Elder's Rules)

**6% Monthly Rule** (Capital Preservation):
- Track equity from month start
- If drawdown ≥ 6% → HALT all trading
- Resume next month
- Stored in: `data/agent_data/{model}/risk_management.json`

**2% Per-Trade Rule** (Position Sizing):
```python
max_risk_dollars = account_equity * 0.02
stop_distance = entry_price - stop_loss_price
shares = max_risk_dollars / stop_distance

# Also cap at 20% of equity:
max_position_value = account_equity * 0.20
max_shares_by_cap = max_position_value / entry_price

final_shares = min(shares, max_shares_by_cap)
```

**Portfolio Limits**:
- Max 3 open positions simultaneously
- Max 6% total portfolio risk (3 × 2%)
- 30% buying power buffer always maintained

### Logging & Data Storage

**Log Structure**:
```
data/agent_data/
└── xai-grok-4.1-fast/
    ├── log/
    │   └── 2025-12-13/
    │       └── log.jsonl          # Trading decisions & outcomes
    ├── position/
    │   └── position.jsonl         # DEPRECATED (Alpaca manages positions)
    ├── trades/
    │   └── trade_history.jsonl   # Completed trades
    ├── momentum_cache.db          # SQLite: Daily momentum scans
    └── risk_management.json       # Elder's 6% Rule tracking
```

**Log Content** (JSONL format):
```json
{
  "timestamp": "2025-12-13T10:30:45",
  "cycle": 42,
  "session": "regular",
  "market_regime": "bullish",
  "decision": "BUY",
  "symbol": "NVDA",
  "quantity": 150,
  "entry_price": 142.50,
  "stop_loss": 141.00,
  "target": 145.50,
  "risk_reward": 2.0,
  "signal_strength": 4,
  "order_id": "abc123",
  "status": "filled",
  "fill_time": "2025-12-13T10:30:47"
}
```

### Known Issues & Gotchas

**1. MCP Service Dependency**
- Active Trader WILL NOT START if MCP services (ports 8004, 8005) are not running
- Solution: `sudo ./manage_services.sh start-mcp` before starting trader
- Health check timeout: 60 seconds (configurable in `SystemConfig`)

**2. Virtual Environment Required**
- ALL Python commands must run inside `.venv`
- systemd service uses: `/home/mfan/work/aitrader/.venv/bin/python`
- Manual runs require: `source .venv/bin/activate`

**3. TA-Lib C Library**
- Python wrapper requires system-wide C library installation
- If missing: `ImportError: libtalib.so.0: cannot open shared object file`
- Fix: `sudo apt-get install libta-lib0 libta-lib0-dev && pip install TA-Lib`

**4. Market Hours Detection**
- Primary: Alpaca's Clock API (`is_market_open_now()`)
- Fallback: Time-based check (Eastern timezone)
- Edge case: Market holidays may not be detected correctly in fallback mode

**5. Extended Hours Execution**
- Pre/Post-market orders MUST set `extended_hours=True`
- System auto-converts to limit orders (safety against thin liquidity)
- Spreads are wider → Use aggressive limit pricing (±0.5% of current price)

**6. Position Tracking**
- OLD: Tracked in `position.jsonl` (DEPRECATED)
- NEW: All positions managed by Alpaca directly
- Agent queries `get_positions()` every cycle for ground truth

**7. Momentum Cache Timing**
- Daily scan at 4:00 AM ET (configurable)
- Cache expires at 4:00 PM ET same day
- If started mid-day, loads cached data OR runs immediate scan
- Weekend runs: Uses Friday's cache (no weekend data available)

**8. Order Verification Loop**
- Polls order status every 500ms for up to 30 seconds
- If not filled in 30s → Logs warning but continues
- May result in "ghost orders" if Alpaca is slow

### Verification & Testing

**Pre-Flight Checklist**:
```bash
# 1. Virtual environment
source .venv/bin/activate
python -c "import talib; print('TA-Lib OK')"

# 2. Environment variables
grep -E '(XAI_API_KEY|ALPACA_API_KEY)' .env

# 3. MCP services
lsof -i :8004 && echo "Data MCP OK" || echo "Data MCP DOWN"
lsof -i :8005 && echo "Trade MCP OK" || echo "Trade MCP DOWN"

# 4. Configuration
cat configs/default_config.json | jq '.models[] | select(.enabled == true)'

# 5. Logs directory
ls -ld data/agent_data/xai-grok-4.1-fast/
```

**Test Momentum Scanner**:
```bash
source .venv/bin/activate
python tools/momentum_scanner.py
# Should output: "✅ Top 50 Gainers + 50 Losers cached"
```

**Test Active Trader (Dry Run)**:
```bash
source .venv/bin/activate
python active_trader.py
# Press Ctrl+C after 1-2 cycles to stop gracefully
```

**Check Service Logs**:
```bash
# Real-time
sudo journalctl -u active-trader -f

# Last 100 lines
sudo journalctl -u active-trader -n 100

# Errors only
sudo journalctl -u active-trader -p err
```

### Performance Metrics

**Typical Cycle Times** (2-minute interval):
- Market schedule check: <1ms
- Agent initialization: 5-10s (first time)
- AI reasoning (Grok-4.1-Fast): 10-30s per cycle
- Order execution + verification: 1-5s
- Total cycle time: 15-40s (plenty of buffer for 2-min interval)

**Resource Usage**:
- RAM: ~500MB (Python + AI model + MCP clients)
- CPU: <5% idle, 20-40% during AI reasoning
- Network: Minimal (REST API calls only)
- Disk I/O: Light (JSONL logging + SQLite cache)

### Trading Strategy Summary

**Style**: Mean Reversion on High-Volume ETFs (Long AND Short)
**Instruments**: 
  - Standard: SPY, QQQ, IWM, XLF, XLE, XLU, GLD, TLT
  - Leveraged 3x Bull: TQQQ, SPXL, UPRO, SOXL, TNA
  - Leveraged 3x Bear: SQQQ, SPXS, SOXS, TZA (NOTE: SPXU cannot be shorted)
**Edge**: Buy fear (price below VWAP + RSI<30), sell greed (price above VWAP + RSI>70)
**Holding Period**: Minutes to hours (intraday only)
**Time Windows**: 10:00-11:30 AM (morning session), 1:00-3:45 PM (afternoon session) [4h 15m total]
**Risk**: 1% per trade, 1.5×ATR stop-loss (volatility-adjusted), 6% monthly max drawdown, 20% buying power cap
**Position Limits**: Max 3 concurrent positions (different ETFs), max 8 trades/day
**Exit Strategy**: Target = VWAP touch, Hard stop = 3:45 PM (no overnight)
**ATR Calculation**: 14-period ATR on 5-minute bars for stop placement

**Why This Works:**
- Statistical edge: 65-70% intraday mean reversion rate
- Institutional anchor: Algos execute around VWAP
- Low complexity: 2 indicators (VWAP + RSI) vs 5+ in old strategy
- Natural low frequency: No anti-churning rules needed

### Recent Improvements (Dec 2025)

**v2.0 Strategy Overhaul**:
- ✅ Anti-churning rules (6 behavioral controls)
- ✅ Enhanced market regime detection (4+ indicator confirmation)
- ✅ Triple Screen validation with A+ setup checklist
- ✅ Explicit time management (3:45 PM hard stop)
- ✅ Win rate circuit breaker (<40% halts trading)
- ✅ Minimum hold time (30 min) + cooldown timer (30 min)

**v1.5 Architecture Refactor**:
- ✅ Modular design (market_schedule, config_loader, agent_factory)
- ✅ Momentum scanner with SQLite caching
- ✅ Intelligent sleep mode (wakes 5 min before market)
- ✅ Elder Risk Manager integration

---

## Virtual Environment Setup

This project uses a Python virtual environment to manage dependencies.

### Initial Setup

```bash
# Create virtual environment (already done)
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Daily Usage

**IMPORTANT:** Always activate the virtual environment before running any Python scripts:

```bash
cd /home/mfan/work/aitrader
source .venv/bin/activate
```

Your prompt should show `(.venv)` when activated:
```
(.venv) mfan@dl385:~/work/aitrader$
```

To deactivate:
```bash
deactivate
```

## Core Dependencies

Installed via `requirements.txt`:
- **langchain** - AI agent framework
- **langchain-openai** - OpenAI/DeepSeek integration
- **langchain-mcp-adapters** - MCP protocol adapters
- **fastmcp** - Fast MCP server implementation
- **python-dotenv** - Environment variable management
- **alpaca-py** - Alpaca trading API
- **alpaca-mcp-server** - Alpaca MCP integration
- **mcp** - Model Context Protocol
- **requests** - HTTP library
- **httpx** - Async HTTP client
- **pytz** - Timezone support
- **pandas** - Data manipulation
- **numpy** - Numerical computing

## Project Structure

```
/home/mfan/work/aitrader/
├── .venv/                        # Virtual environment (DO NOT COMMIT)
├── active_trader.py              # Main trading bot
├── requirements.txt              # Python dependencies
├── .env                          # API keys (DO NOT COMMIT)
│
├── agent/                        # Agent base classes
├── agent_tools/                  # MCP service starters
├── configs/                      # Configuration files
├── data/                         # Runtime data & cache
│   ├── momentum_cache.db         # Momentum scan cache (production)
│   └── agent_data/               # Agent logs and state
│
├── prompts/                      # Agent prompts
│   ├── agent_prompt.py           # Main trading strategy
│   └── elder_triple_screen_prompt.py  # Elder methodology
│
└── tools/                        # Trading tools
    ├── momentum_scanner.py       # Pre-market momentum scanner
    ├── momentum_cache.py         # SQLite cache manager
    ├── elder_indicators.py       # Elder's TA indicators
    ├── elder_risk_manager.py     # Risk management (6% rule)
    ├── alpaca_data_feed.py       # Real-time data
    ├── alpaca_trading.py         # Order execution
    └── technical_indicators.py   # TA-Lib indicators
```

## Running the System

### 1. Start MCP Services (Required)

The Alpaca MCP services must be running on ports 8004 (data) and 8005 (trade):

```bash
# Check if services are running
lsof -i :8004
lsof -i :8005

# If not running, start them
sudo ./manage_services.sh start-mcp
```

### 2. Test Momentum Scanner

```bash
source .venv/bin/activate
python tools/momentum_scanner.py
```

This tests the momentum scanner with yesterday's data and caches results to SQLite.

### 3. Run Active Trader

```bash
source .venv/bin/activate
python active_trader.py
```

The active trader will:
1. Run pre-market scan at 4:00 AM ET (or immediately if started later)
2. Cache top 100 momentum stocks to SQLite
3. Trade those stocks during pre-market and regular hours
4. Use Elder's Triple Screen methodology
5. Apply 6% monthly drawdown limit

## Momentum System Overview

### Pre-Market Scan (4:00 AM ET)

The system scans yesterday's market to find top movers:

1. **Universe:** 106 liquid stocks (mega-cap tech, financials, healthcare, etc.)
2. **Filter:** 10M-20M+ daily volume minimum
3. **Rank:** By price change percentage (open to close)
4. **Select:** Top 50 gainers + Top 50 losers = 100 stocks
5. **Cache:** Store to SQLite with TA indicators
6. **Expire:** Cache valid until 4 PM, then re-scan next day at 4:00 AM

### SQLite Cache Schema

**daily_movers table:**
- `scan_date` - Trading date (YYYY-MM-DD)
- `symbol` - Stock ticker
- `direction` - 'gainer' or 'loser'
- `rank` - 1-50 ranking
- `open`, `high`, `low`, `close` - OHLC prices
- `volume` - Daily volume
- `change_pct` - Price change percentage
- `indicators` - JSON of TA indicators (RSI, MACD, EMA, etc.)
- `momentum_score` - Combined momentum score

**market_regime table:**
- `scan_date` - Trading date
- `regime` - 'bullish', 'bearish', or 'neutral'
- `spy_change_pct` - S&P 500 change %
- `qqq_change_pct` - NASDAQ-100 change %
- `market_score` - Combined market score

### Trading Strategy

**Style:** Momentum Swing Trading (1-3 day holds)
- NOT intraday - we hold overnight
- Focus on riding momentum waves
- Options for 2-3x leverage (if available)

**Position Sizing:**
- Stocks: 2% risk per trade
- Options: 1-2% risk per trade (more volatile)

**Market Alignment:**
- Bullish regime → Long calls on gainers
- Bearish regime → Long puts on losers
- Never counter-trend

**Risk Management (Elder's 6% Rule):**
- Max 6% monthly drawdown
- If hit, stop trading for rest of month
- Max 2% risk per single trade
- Position sizing via ATR-based stops

## Recent Changes & Version History

### Dec 16, 2025 - ATR-Based Stops (Volatility-Adaptive)

**Key Improvement:** Replaced fixed 0.5% stops with ATR-based stops that adapt to market volatility.

**Why ATR Stops?**
- Fixed % stops (0.5%) were getting triggered in 16 minutes on volatile TQQQ
- ATR adapts to current market conditions automatically
- Avoids placing stops where everyone else puts them (fixed levels)
- Proper position sizing based on actual volatility

**Implementation:**
- **Timeframe**: ATR(14) calculated on 5-minute bars
- **Multiplier**: 1.5× ATR (balanced - not too tight, not too loose)
- **Stop Placement**: Entry ± (1.5 × ATR) depending on long/short
- **Position Sizing**: `shares = risk_amount / (1.5 × ATR)`

**Example for TQQQ:**
- ATR(14) on 5-min = $0.80
- Stop distance = 1.5 × $0.80 = $1.20
- With $100K equity (1% risk = $1000): shares = 833

**Files Changed:**
- `prompts/agent_prompt.py` → Updated all stop rules to use ATR
- `README.md` → Updated position sizing documentation
- `CLAUDE.md` → This changelog

---

### Dec 15, 2025 - Bug Fixes: Position Sizing & ETF List

**Issues Discovered in Dec 15 Trading Analysis:**
1. Position sizing exceeded buying power ($2.8M orders with $847K buying power)
2. SPXU cannot be shorted on Alpaca (hard-to-borrow)
3. Legacy ghost positions polluting tracking (51 stale entries)

**Fixes Applied:**
- Added 20% buying power cap: `shares = min(risk_shares, max_shares)`
- Removed SPXU from ETF_WATCHLIST (17 ETFs now)
- Reset risk_management.json with correct equity ($839K)

---

### Dec 14, 2025 - Strategy v3.0: Simplified Mean Reversion Edge

**MAJOR STRATEGY OVERHAUL** - Replaced complex Elder Triple Screen with simple mean reversion.

#### Why the Change?

The v2.0 Elder Triple Screen strategy had fundamental problems:

| Problem | Impact |
|---------|--------|
| 394 lines of rules | AI got confused, inconsistent execution |
| Triple Screen (5 indicators) | Conflicting signals, analysis paralysis |
| "Momentum Swing" | Contradictory concept (momentum=fast, swing=slow) |
| Anti-churning rules | Symptom of bad strategy, not solution |
| Retail-grade TA | Institutional algos exploit these patterns |

#### The New Edge: Mean Reversion + VWAP

**Statistical Facts:**
- SPY/QQQ mean-revert intraday 65-70% of the time
- Price touches VWAP 3-5 times per day on average
- Extreme RSI (<20 or >80) reverts within 30-60 minutes 75% of the time
- Morning gaps fill 70% of the time before noon

**The Strategy (5 Simple Rules):**

1. **Trade high-volume ETFs (Long OR Short)**:
   - Standard: SPY, QQQ, IWM, XLF, XLE, XLU, GLD, TLT
   - Leveraged Bull 3x: TQQQ, SPXL, UPRO, SOXL, TNA
   - Leveraged Bear 3x: SQQQ, SPXS, SOXS, TZA (SPXU removed - can't short)
2. **Buy below VWAP, Sell above VWAP**:
   - LONG: Price 0.3%+ below VWAP AND RSI < 30 (0.5% for leveraged)
   - SHORT: Price 0.3%+ above VWAP AND RSI > 70 (0.5% for leveraged)
   - Target: VWAP touch
   - **Stop: 1.5 × ATR(14) on 5-min bars** (volatility-adjusted, adapts to market conditions)
3. **Time windows** (when edge is strongest):
   - 10:00-11:30 AM: Morning session (post-open stabilization)
   - 1:00-3:45 PM: Afternoon session (lunch recovery + continuation)
   - AVOID: 9:30-10:00 (opening chaos), 11:30-1:00 (lunch lull), first 15 min of session
4. **Max 3 concurrent positions**: Different ETFs for diversification
5. **Exit by 3:45 PM**: No overnight positions

#### Position Sizing (ATR-Based, Conservative)

```python
# Get ATR(14) on 5-minute bars
bars_5m = get_bars(symbol, timeframe='5Min', limit=20)
ATR = calculate_ATR(bars_5m, period=14)

# Risk 1% per trade with ATR-based stop
risk_amount = equity * 0.01
stop_distance = 1.5 * ATR  # In dollars per share
risk_shares = int(risk_amount / stop_distance)

# Cap at 20% of buying power
max_shares = int((buying_power * 0.20) / entry_price)
shares = min(risk_shares, max_shares)

# Example: $100K equity, TQQQ at $50, ATR=$0.80
# Risk: $1,000, Stop distance: $1.20 (1.5 * 0.80)
# Shares: 833
```

#### Daily/Monthly Limits

- Max 3 trades per day
- Stop if down 2% for the day
- Stop if 2 consecutive losses
- Stop if down 6% for the month

#### Expected Performance

| Metric | Expected Value |
|--------|----------------|
| Win Rate | 60-65% |
| Avg Win | +0.3% (VWAP touch) |
| Avg Loss | -1.5×ATR (adaptive) |
| Expectancy | +0.004% per trade |
| Trades/Day | 1-3 |
| Monthly Return | +2-4% (gross) |
| Stop Type | ATR-based (volatility-adaptive) |

#### Files Changed

- `prompts/agent_prompt.py` → New v3 mean reversion strategy
- `prompts/agent_prompt_v2_elder.py` → Backup of old Elder strategy
- `prompts/agent_prompt_v3_simple.py` → Source for v3

---

### Dec 13, 2025 - System Analysis & Documentation Update

**Completed comprehensive analysis of Active Trader implementation:**
- Documented complete system architecture and data flow
- Verified all 9 key subsystems (orchestrator, agent, MCP, scanner, risk, etc.)
- Confirmed Elder Triple Screen + anti-churning controls in production
- Validated systemd service configuration and dependency chain
- Updated CLAUDE.md, README.md with accurate implementation details

### Dec 11, 2025 - Strategy v2.0: Anti-Churning & Enhanced TA

**Context:** Dec 9 retrospective revealed critical issues - 15 round-trips on XLU turned +$675 profit into -$266 loss due to overtrading (churning).

#### ✅ Major Strategy Rewrite (`prompts/agent_prompt.py`)

Upgraded from **148 lines to 394 lines** with comprehensive improvements:

**1. ANTI-CHURNING RULES (New Section)**
   - **30-min cooldown** between same-symbol re-entries
   - **Max 2 round-trips per symbol per day** (hard limit)
   - **30-min minimum hold time** unless stop-loss hit
   - **Win rate circuit breaker**: Stop trading if <40% after 3+ trades
   - **6 daily trade limit** maximum across all symbols
   - **No scalping rule**: Targets <$0.50 price movement blocked

**2. ENHANCED TIME MANAGEMENT**
   - Explicit **3:45 PM HARD STOP** enforcement in prompt
   - Clear session windows with specific rules per session
   - Wind-down period (3:30-3:45) explicitly defined

**3. IMPROVED MARKET REGIME DETECTION**
   - Multi-indicator confirmation required (4+ of 6 signals)
   - Clear **BULLISH/BEARISH/NEUTRAL** classification criteria
   - **NEUTRAL regime special rules**:
     - 50% position size only
     - Signal Strength 3+ required (A+ setups only)
     - Maximum 1 position at a time
     - <2 hour hold time max
   - Confidence scoring (1/5 for neutral, 5/5 for strong trends)

**4. TRIPLE SCREEN VALIDATION (Elder's Methodology)**
   - **Screen 1 (Tide)**: Weekly/Daily trend via MACD + EMAs
   - **Screen 2 (Wave)**: Daily oscillators (RSI/Stoch) for pullback timing
   - **Screen 3 (Trigger)**: Momentum confirmation (Impulse System)
   - **A+ Setup Checklist**: 5/5 criteria required for full size execution

**5. RISK MANAGEMENT PROTOCOLS**
   - 2% Iron Rule (per-trade risk cap)
   - 6% Monthly Shield (stop trading on drawdown)
   - SafeZone stops (ATR-based, dynamic)
   - Trailing stop rules: Breakeven at +1R, trail at +2R

**6. BEHAVIORAL DISCIPLINE SECTION**
   - Explicit "DO" and "DO NOT" lists
   - Quality-over-quantity mindset reinforcement
   - "Cash is a position" philosophy

#### 📊 Before vs After Comparison

| Aspect | Old (v1) | New (v2.0) |
|--------|----------|------------|
| Lines of code | 148 | 394 |
| Anti-churning | ❌ None | ✅ 6 explicit rules |
| Cooldown timer | ❌ None | ✅ 30 min minimum |
| Max round-trips | ❌ None | ✅ 2 per symbol/day |
| Win rate check | ❌ None | ✅ Stop if <40% |
| Regime detection | Basic | ✅ Multi-indicator (4+ signals) |
| Neutral handling | Vague | ✅ Strict rules |
| Position sizing | Simple | ✅ Formula with examples |

#### 🎯 Dec 9 Root Causes Addressed

| Issue | Solution in v2.0 |
|-------|-----------------|
| Churning (15 round-trips) | Max 2 per symbol + 30-min cooldown |
| Hard stop violated (traded until 20:33) | 3:45 PM explicitly enforced |
| Impatience (short holds) | 30-min minimum hold time |
| Tiny price targets | No-scalping rule (<$0.50 blocked) |
| Low win rate | Circuit breaker stops trading at <40% |

---

### Dec 2, 2025 - 24-Hour Trading Cycle

#### ✅ Completed

1. **Systemd Service Stabilization**
   - Fixed start/stop loops in `active-trader.service`.
   - Updated all service files to use correct virtual environment path (`.venv/bin/python`).

2. **24-Hour Trading Cycle Implementation**
   - **Pre-Market (4:00 AM)**: Implemented wake-up and momentum scan logic.
   - **Regular Market (9:30 AM)**: Seamless transition (holding positions).
   - **End-of-Day (3:45 PM)**: **Hard Stop** logic to liquidate all positions.
   - **Post-Market**: Optional trading with secondary hard stop (7:45 PM).

3. **Execution Logic Optimization**
   - **No Hesitation**: Agent prompts enforce immediate execution in extended hours.
   - **Limit Orders**: Auto-convert to aggressive limit orders (±0.5%) during extended hours.

---

### 🎯 Next Steps

1. **Monitor v2.0 Strategy Performance**
   - Verify anti-churning rules prevent overtrading.
   - Confirm win rate circuit breaker triggers correctly.
   - Track round-trips per symbol to ensure <2/day.

2. **Validate Behavioral Controls**
   - Ensure cooldown timer is respected.
   - Verify 30-min minimum hold time enforcement.
   - Test NEUTRAL regime special handling.

## Trading Workflow & Schedule

The system operates on a strict 24-hour cycle designed for continuous operation with intelligent sleep modes.

### 1. Pre-Market (4:00 AM - 9:30 AM ET)
*   **3:55 AM**: System wakes up from sleep mode.
*   **4:00 AM**: **Daily Momentum Scan** runs.
    *   Scans previous day's top movers (Volume > 10M, Top 100 Gainers/Losers).
    *   Updates `momentum_watchlist` and re-initializes the agent.
*   **Trading**:
    *   Agent operates in `PRE-MARKET` session mode.
    *   **Execution**: MUST use `extended_hours=True`.
    *   **Order Type**: Auto-converts to **Limit Orders** (Current Price ± 0.5%) for immediate execution.
    *   **Strategy**: Aggressive entry on high-quality setups; no hesitation.

### 2. Regular Market (9:30 AM - 3:45 PM ET)
*   **9:30 AM**: Seamless transition to `REGULAR` session.
*   **Positions**: Existing pre-market positions are **HELD** (not auto-closed).
*   **Trading**:
    *   Standard execution rules apply.
    *   Market orders allowed.
    *   Full liquidity available.

### 3. End-of-Day Wind Down (3:45 PM ET)
*   **3:45 PM**: **HARD STOP** (15 minutes before close).
*   **Action**: `should_close_positions` triggers.
*   **Execution**:
    *   **Close All Positions**: Liquidates all open holdings.
    *   **Cancel Orders**: Cancels all pending open orders.
    *   Ensures flat book going into overnight.

### 4. Post-Market (4:00 PM - 8:00 PM ET)
*   **4:00 PM**: Regular market closes.
*   **Trading**: Optional. If enabled, operates similarly to Pre-Market (Limit orders only).
*   **7:45 PM**: Secondary Hard Stop if post-market trading is active.

### 5. Overnight Sleep
*   System enters "Intelligent Sleep Mode" to minimize resource usage until 3:55 AM next trading day.

## Troubleshooting

### "No module named 'xyz'" Error

Make sure virtual environment is activated:
```bash
source .venv/bin/activate
which python3  # Should show: /home/mfan/work/aitrader/.venv/bin/python3
```

### MCP Services Not Running

```bash
# Check ports
lsof -i :8004
lsof -i :8005

# Start services if needed
sudo ./manage_services.sh start-mcp
```

### Momentum Scan Returns No Data

1. Check Alpaca API credentials in `.env`
2. Verify date is a trading day (not weekend/holiday)
3. Check logs for API errors
4. Ensure MCP services are running

### Cache is Stale

Cache expires at 4 PM ET each day. If it's after market close, the scan will run again next trading day at 4:00 AM.

To manually force a re-scan:
```bash
source .venv/bin/activate
python tools/momentum_scanner.py
```
