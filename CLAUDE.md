# AI Trader Development Setup

## Virtual Environment Setup

This project uses a Python virtual environment to manage dependencies.

### Initial Setup

```bash
# Create virtual environment (already done)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Daily Usage

**IMPORTANT:** Always activate the virtual environment before running any Python scripts:

```bash
cd /home/mfan/work/aitrader
source venv/bin/activate
```

Your prompt should show `(venv)` when activated:
```
(venv) mfan@dl385:~/work/aitrader$
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
├── venv/                          # Virtual environment (DO NOT COMMIT)
├── active_trader.py               # Main trading bot
├── requirements.txt               # Python dependencies
├── .env                          # API keys (DO NOT COMMIT)
│
├── agent/                        # Agent base classes
├── agent_tools/                  # MCP service starters
├── configs/                      # Configuration files
├── data/                         # Runtime data & cache
│   ├── momentum_cache.db        # Momentum scan cache (production)
│   └── test_momentum_cache.db   # Test cache
│
├── prompts/                      # Agent prompts
│   ├── agent_prompt.py          # Main trading strategy
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
source venv/bin/activate
python test_momentum_scan.py
```

This tests the momentum scanner with yesterday's data and caches results to SQLite.

### 3. Run Active Trader

```bash
source venv/bin/activate
python active_trader.py
```

The active trader will:
1. Run pre-market scan at 9:00-9:25 AM ET
2. Cache top 100 momentum stocks to SQLite
3. Trade those stocks during regular hours (9:30 AM - 4:00 PM ET)
4. Use Elder's Triple Screen methodology
5. Apply 6% monthly drawdown limit

## Momentum System Overview

### Pre-Market Scan (9:00-9:25 AM ET)

The system scans yesterday's market to find top movers:

1. **Universe:** 106 liquid stocks (mega-cap tech, financials, healthcare, etc.)
2. **Filter:** 10M-20M+ daily volume minimum
3. **Rank:** By price change percentage (open to close)
4. **Select:** Top 50 gainers + Top 50 losers = 100 stocks
5. **Cache:** Store to SQLite with TA indicators
6. **Expire:** Cache valid until 4 PM, then re-scan next day

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

## Recent Changes (Nov 8, 2025)

### ✅ Completed

1. **Created Momentum Scanner** (`tools/momentum_scanner.py`)
   - Scans previous day's top volume movers
   - Fetches data via AlpacaDataFeed
   - Filters for 10M+ volume
   - Ranks by price change %
   - Returns top 100 stocks (50 gainers + 50 losers)

2. **Created SQLite Cache** (`tools/momentum_cache.py`)
   - Stores daily momentum scan results
   - Fast intraday queries (< 2ms)
   - Auto-expires cache at market close
   - Tracks market regime (SPY/QQQ)

3. **Integrated with Active Trader** (`active_trader.py`)
   - Runs pre-market scan at 9:00 AM
   - Loads cached momentum watchlist
   - Replaces fixed NASDAQ-100 list
   - Dynamic trading based on actual momentum

4. **Updated Agent Prompt** (`prompts/agent_prompt.py`)
   - Changed from day trading to swing trading
   - Added momentum watchlist explanation
   - Added options trading strategy
   - Emphasized market regime alignment

5. **Virtual Environment Setup**
   - Created `/home/mfan/work/aitrader/venv`
   - Installed all dependencies from `requirements.txt`
   - Tested momentum scanner successfully

### 🔍 Test Results (Nov 7, 2025 Data)

```
✅ Scanned 106 stocks successfully
✅ Found 51 stocks with 10M+ volume
✅ Top gainer: MSTR (+8.65%, Vol: 16.9M)
✅ Worst loser: ABNB (-3.68%, Vol: 11.8M)
✅ Market regime: NEUTRAL (SPY +0.46%, QQQ +0.24%)
✅ Cached 100 stocks to SQLite
✅ Cache queries: < 2ms (very fast)
```

### 🎯 Next Steps

1. **Complete Alpaca API Integration** ✅ (DONE - using AlpacaDataFeed)
   - Fixed import error in momentum_scanner.py
   - Now uses `AlpacaDataFeed.get_bars()` directly
   - Successfully fetches historical bars

2. **Test End-to-End Integration**
   - Run active trader with momentum system
   - Verify pre-market scan at 9:00 AM
   - Confirm trades only occur on momentum stocks
   - Monitor performance vs fixed watchlist

3. **Add Options Trading Support**
   - Research if Alpaca paper trading supports options
   - If yes: implement `place_option_order()` function
   - If no: document stock-based approach with mental leverage

4. **Backtest Momentum Strategy**
   - Historical validation on Oct-Nov 2025
   - Compare vs fixed NASDAQ-100 watchlist
   - Metrics: Win rate, avg profit, Sharpe ratio
   - Find optimal hold period (1, 2, or 3 days)

## Troubleshooting

### "No module named 'xyz'" Error

Make sure virtual environment is activated:
```bash
source venv/bin/activate
which python3  # Should show: /home/mfan/work/aitrader/venv/bin/python3
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

Cache expires at 4 PM ET each day. If it's after market close, the scan will run again next trading day at 9:00 AM.

To manually force a re-scan:
```bash
source venv/bin/activate
python test_momentum_scan.py
```

## Important Notes

1. **ALWAYS activate venv** before running any Python scripts
2. **MCP services must be running** on ports 8004 and 8005
3. **Pre-market scan runs 9:00-9:25 AM ET** - don't interrupt it
4. **Cache expires at 4 PM** - automatic daily refresh
5. **6% monthly drawdown limit** - enforced by Elder risk manager

## Git Ignore

Make sure these are in `.gitignore`:
```
venv/
__pycache__/
*.pyc
.env
data/*.db
data/*.db-journal
logs/
```

---

**Last Updated:** November 8, 2025  
**Status:** Momentum system tested and operational ✅
