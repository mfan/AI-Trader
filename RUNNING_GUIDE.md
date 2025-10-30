# 🚀 AI-Trader Setup and Running Guide

**Last Updated**: October 28, 2025  
**Python Version Required**: 3.8+  
**Current System**: Python 3.12.3

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Configuration](#configuration)
4. [Running AI-Trader](#running-ai-trader)
5. [Manual Step-by-Step Process](#manual-step-by-step-process)
6. [Troubleshooting](#troubleshooting)
7. [Common Issues](#common-issues)

---

## 🔧 Prerequisites

Before running AI-Trader, ensure you have:

### Required Software
- ✅ Python 3.8 or higher (You have: **3.12.3** ✓)
- ✅ pip (Python package manager)
- ✅ bash shell (for running scripts)
- ✅ Internet connection (for API calls)

### Required API Keys
You'll need accounts and API keys from:

1. **OpenAI** - For GPT models
   - Sign up: https://platform.openai.com/
   - Get API key: https://platform.openai.com/api-keys

2. **Alpha Vantage** - For stock price data
   - Sign up: https://www.alphavantage.co/support/#api-key
   - Free tier available

3. **Jina AI** - For market intelligence search
   - Sign up: https://jina.ai/
   - Get API key from dashboard

4. **Optional**: Anthropic (Claude), DeepSeek, Qwen, Google (Gemini)
   - Only needed if you enable those models in config

---

## 🎬 Initial Setup

### Step 1: Install Python Dependencies

**⚠️ IMPORTANT**: The `requirements.txt` is missing `python-dotenv`. You need to add it first.

```bash
cd /home/mfan/work/aitrader

# Option 1: Add python-dotenv to requirements.txt
echo "python-dotenv>=0.19.0" >> requirements.txt

# Option 2: Install directly
pip3 install python-dotenv

# Install all dependencies
pip3 install -r requirements.txt
```

**Expected output:**
```
Successfully installed langchain-1.0.2 langchain-openai-1.0.1 ...
```

**Verify installation:**
```bash
python3 -c "import dotenv, langchain, fastmcp; print('✅ All dependencies installed')"
```

### Step 2: Set Up Environment Variables

**Create your `.env` file** (⚠️ Never commit this file to git!)

```bash
cd /home/mfan/work/aitrader

# Copy the example file
cp .env.example .env

# Edit with your API keys
nano .env
# or
vim .env
# or use any text editor
```

**Fill in your `.env` file with real values:**

```bash
# AI Model API configuration
OPENAI_API_BASE="https://api.openai.com/v1"
OPENAI_API_KEY="sk-YOUR_OPENAI_KEY_HERE"

# Data Source configuration
ALPHAADVANTAGE_API_KEY="YOUR_ALPHA_VANTAGE_KEY_HERE"
JINA_API_KEY="YOUR_JINA_KEY_HERE"

# Service Port Configuration (default values are fine)
MATH_HTTP_PORT=8000
SEARCH_HTTP_PORT=8001
TRADE_HTTP_PORT=8002
GETPRICE_HTTP_PORT=8003

# AI Agent Configuration
AGENT_MAX_STEP=30

# System Configuration
RUNTIME_ENV_PATH="/home/mfan/work/aitrader/runtime_env.json"
```

**⚠️ Security Check:**
```bash
# Verify .env is NOT tracked in git
git ls-files | grep .env
# Should return nothing (empty)
```

### Step 3: Initialize Runtime Environment

```bash
cd /home/mfan/work/aitrader

# Create runtime_env.json if it doesn't exist
cat > runtime_env.json << EOF
{
    "SIGNATURE": "gpt-5",
    "TODAY_DATE": "2025-10-15",
    "IF_TRADE": false
}
EOF
```

### Step 4: Verify Data Files Exist

```bash
cd /home/mfan/work/aitrader/data

# Check if price data exists
ls daily_prices_*.json | wc -l
# Should show 100+ files

# Check if merged.jsonl exists
ls -lh merged.jsonl
```

**If price data is missing**, you'll need to fetch it (see Step 1 of Manual Process below).

---

## ⚙️ Configuration

### Configure Which AI Models to Run

Edit the configuration file to enable/disable models:

```bash
cd /home/mfan/work/aitrader
nano configs/default_config.json
```

**Key settings to review:**

```json
{
  "agent_type": "BaseAgent",
  "date_range": {
    "init_date": "2025-10-01",    // Start date for trading
    "end_date": "2025-10-15"      // End date for trading
  },
  "models": [
    {
      "name": "gpt-5",
      "basemodel": "openai/gpt-5",
      "signature": "gpt-5",
      "enabled": true              // Set to true to run this model
    },
    {
      "name": "claude-3.7-sonnet",
      "enabled": false             // Set to true if you have Claude API key
    }
    // ... other models
  ],
  "agent_config": {
    "max_steps": 30,               // Max reasoning steps per day
    "max_retries": 3,              // Retry attempts on failure
    "base_delay": 1.0,             // Delay between retries (seconds)
    "initial_cash": 10000.0        // Starting capital in USD
  },
  "log_config": {
    "log_path": "./data/agent_data"
  }
}
```

**💡 Tip**: Start with only ONE model enabled (e.g., gpt-5) for your first run.

---

## 🚀 Running AI-Trader

### Method 1: Automated Script (Recommended)

The `main.sh` script handles everything automatically:

```bash
cd /home/mfan/work/aitrader

# Make script executable (first time only)
chmod +x main.sh

# Run the complete workflow
./main.sh
```

**What `main.sh` does:**
1. 📊 Fetches latest stock prices from Alpha Vantage
2. 🔧 Merges price data into `merged.jsonl`
3. 🚀 Starts 4 MCP services (Math, Search, Trade, Price)
4. 🤖 Runs the trading agents
5. 🌐 Starts web server for results visualization

**Expected output:**
```
🚀 Launching AI Trader Environment...
📊 Now getting and merging price data...
🔧 Now starting MCP services...
✅ Math service started (PID: 12345, Port: 8000)
✅ Search service started (PID: 12346, Port: 8001)
✅ Trade service started (PID: 12347, Port: 8002)
✅ LocalPrices service started (PID: 12348, Port: 8003)
🤖 Now starting the main trading agent...
🚀 Starting trading experiment
📅 Date range: 2025-10-01 to 2025-10-15
...
```

**⚠️ Important Notes:**
- The script will run in the foreground
- MCP services run in background
- Use `Ctrl+C` to stop
- Web server starts at http://localhost:8888

### Method 2: Run Main Script Only

If you already have price data and want to run trading only:

```bash
cd /home/mfan/work/aitrader

# Start MCP services first
cd agent_tools
python3 start_mcp_services.py &
cd ..

# Wait for services to start
sleep 3

# Run trading
python3 main.py

# Or specify custom config
python3 main.py configs/my_custom_config.json
```

---

## 🔍 Manual Step-by-Step Process

If you prefer to run each step manually or need to debug:

### Step 1: Fetch Stock Price Data

```bash
cd /home/mfan/work/aitrader/data

# Fetch latest prices for all NASDAQ-100 stocks
# ⚠️ This takes ~10-15 minutes due to API rate limits
python3 get_daily_price.py
```

**What this does:**
- Calls Alpha Vantage API for each of 100+ stocks
- Saves to individual `daily_prices_SYMBOL.json` files
- Creates `Adaily_prices_QQQ.json` for benchmark

**💡 Tip**: You may hit API rate limits (5 calls/minute on free tier). The script handles this automatically.

### Step 2: Merge Price Data

```bash
cd /home/mfan/work/aitrader/data

# Combine all price files into single merged.jsonl
python3 merge_jsonl.py
```

**What this does:**
- Reads all `daily_prices_*.json` files
- Renames fields: `1. open` → `1. buy price`, `4. close` → `4. sell price`
- Writes to `merged.jsonl` (one JSON per line)

**Verify:**
```bash
wc -l merged.jsonl
# Should show 100+ lines (one per stock)
```

### Step 3: Start MCP Services

MCP services provide tools for AI agents (math, search, trading, prices).

**Option A: Using Service Manager (Recommended)**

```bash
cd /home/mfan/work/aitrader/agent_tools

# Start all services
python3 start_mcp_services.py
```

**Option B: Start Services Individually**

```bash
cd /home/mfan/work/aitrader/agent_tools

# Terminal 1: Math service
python3 tool_math.py &

# Terminal 2: Search service
python3 tool_jina_search.py &

# Terminal 3: Trade service
python3 tool_trade.py &

# Terminal 4: Price service
python3 tool_get_price_local.py &
```

**Verify services are running:**
```bash
# Check if ports are open
netstat -tuln | grep -E '8000|8001|8002|8003'

# Or use lsof
lsof -i :8000  # Math service
lsof -i :8001  # Search service
lsof -i :8002  # Trade service
lsof -i :8003  # Price service
```

**Check service logs:**
```bash
cd /home/mfan/work/aitrader/logs
tail -f math.log
tail -f search.log
tail -f trade.log
tail -f price.log
```

### Step 4: Run Trading Agent

```bash
cd /home/mfan/work/aitrader

# Run with default config
python3 main.py

# Or specify custom config
python3 main.py configs/custom_config.json

# Or override dates via environment variables
INIT_DATE="2025-10-01" END_DATE="2025-10-05" python3 main.py
```

**What happens during trading:**

1. **Initialization**
   ```
   ✅ Successfully loaded configuration file
   ✅ Successfully loaded Agent class: BaseAgent
   🚀 Starting trading experiment
   📅 Date range: 2025-10-01 to 2025-10-15
   🤖 Model list: ['gpt-5']
   ```

2. **For Each Model**
   ```
   ====================================================
   🤖 Processing model: gpt-5
   📝 Signature: gpt-5
   🔧 BaseModel: openai/gpt-5
   ✅ BaseAgent instance created successfully
   ```

3. **For Each Trading Day**
   ```
   📈 Starting trading session: 2025-10-01
   🔄 Step 1/30
   [AI analyzes market, calls tools]
   ✅ Received stop signal, trading session ended
   ```

4. **Completion**
   ```
   📊 Final position summary:
      - Latest date: 2025-10-15
      - Total records: 15
      - Cash balance: $10,234.56
   ✅ Model gpt-5 processing completed
   ```

### Step 5: View Results

**Check trading logs:**
```bash
cd /home/mfan/work/aitrader/data/agent_data/gpt-5

# View position history
cat position/position.jsonl

# View trading logs for specific date
cat log/2025-10-15/log.jsonl
```

**Start web dashboard:**
```bash
cd /home/mfan/work/aitrader/docs
python3 -m http.server 8888

# Open in browser
# http://localhost:8888
```

---

## 🐛 Troubleshooting

### Common Issues and Solutions

#### Issue 1: `ImportError: No module named 'dotenv'`

**Solution:**
```bash
pip3 install python-dotenv
```

#### Issue 2: `ImportError: No module named 'langchain'`

**Solution:**
```bash
pip3 install -r requirements.txt
```

#### Issue 3: MCP Services Won't Start

**Check port availability:**
```bash
# See if ports are already in use
netstat -tuln | grep -E '8000|8001|8002|8003'

# Kill existing processes on those ports
lsof -ti:8000 | xargs kill -9
lsof -ti:8001 | xargs kill -9
lsof -ti:8002 | xargs kill -9
lsof -ti:8003 | xargs kill -9
```

**Check service logs:**
```bash
cd /home/mfan/work/aitrader/logs
cat math.log
cat search.log
cat trade.log
cat price.log
```

#### Issue 4: API Rate Limit Errors

**For Alpha Vantage:**
- Free tier: 5 API calls per minute, 500 per day
- Solution: Wait between calls (script handles this)
- Or upgrade to paid tier

**For OpenAI:**
- Check your usage limits
- Add delays between requests
- Monitor costs

#### Issue 5: "Configuration file does not exist"

**Solution:**
```bash
cd /home/mfan/work/aitrader

# Make sure config file exists
ls -la configs/default_config.json

# Or create from example
cp configs/default_config.json configs/my_config.json
```

#### Issue 6: "SIGNATURE environment variable is not set"

**Solution:**
```bash
# Check runtime_env.json exists
cat runtime_env.json

# Verify RUNTIME_ENV_PATH in .env
grep RUNTIME_ENV_PATH .env

# Should be:
# RUNTIME_ENV_PATH="/home/mfan/work/aitrader/runtime_env.json"
```

#### Issue 7: Missing Price Data

**Solution:**
```bash
cd /home/mfan/work/aitrader/data

# Fetch price data
python3 get_daily_price.py

# Merge into single file
python3 merge_jsonl.py

# Verify
ls -lh merged.jsonl
```

#### Issue 8: Trading Agent Doesn't Execute Trades

**Check:**
1. MCP services are running
2. API keys are correct in `.env`
3. Model is enabled in config
4. Date range is valid (weekdays only)

**Debug mode:**
```bash
# Check what tools are available
cd /home/mfan/work/aitrader
python3 -c "
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def check():
    client = MultiServerMCPClient({
        'math': {'transport': 'streamable_http', 'url': 'http://localhost:8000/mcp'}
    })
    tools = await client.get_tools()
    print(f'Available tools: {len(tools)}')
    
asyncio.run(check())
"
```

---

## 📊 Monitoring Running Agents

### Check Process Status

```bash
# Find Python processes
ps aux | grep python

# Check specific services
ps aux | grep tool_math.py
ps aux | grep tool_search.py
ps aux | grep tool_trade.py
ps aux | grep tool_get_price_local.py
```

### Monitor Logs in Real-Time

```bash
# Open multiple terminals and run:
tail -f logs/math.log
tail -f logs/search.log
tail -f logs/trade.log
tail -f logs/price.log

# Or use tmux/screen to monitor all at once
```

### Check Trading Progress

```bash
# Watch position updates
watch -n 5 'tail -n 1 data/agent_data/gpt-5/position/position.jsonl'

# Count trading days processed
wc -l data/agent_data/gpt-5/position/position.jsonl
```

---

## 🛑 Stopping AI-Trader

### Stop All Services

```bash
# If using main.sh: Press Ctrl+C

# Or kill MCP services manually
pkill -f tool_math.py
pkill -f tool_jina_search.py
pkill -f tool_trade.py
pkill -f tool_get_price_local.py

# Or kill by port
lsof -ti:8000 | xargs kill
lsof -ti:8001 | xargs kill
lsof -ti:8002 | xargs kill
lsof -ti:8003 | xargs kill
```

### Clean Shutdown

```bash
# Stop services gracefully
cd /home/mfan/work/aitrader/agent_tools
# (Ctrl+C in service manager terminal)

# Or send SIGTERM
pkill -SIGTERM -f start_mcp_services.py
```

---

## 🎯 Quick Start Checklist

Before running AI-Trader, ensure:

- [ ] Python 3.8+ installed ✓ (You have 3.12.3)
- [ ] Dependencies installed (`pip3 install -r requirements.txt`)
- [ ] `python-dotenv` installed
- [ ] `.env` file created with valid API keys
- [ ] `runtime_env.json` exists
- [ ] Price data fetched (`data/merged.jsonl` exists)
- [ ] At least one model enabled in `configs/default_config.json`
- [ ] Ports 8000-8003 are available
- [ ] Internet connection active

---

## 📈 Expected Results

After successful run, you should see:

### File Structure
```
data/agent_data/
└── gpt-5/                    # Or your model signature
    ├── position/
    │   └── position.jsonl    # Trading positions over time
    └── log/
        ├── 2025-10-01/
        │   └── log.jsonl     # Detailed logs per day
        ├── 2025-10-02/
        │   └── log.jsonl
        └── ...
```

### Position File Format
```json
{"date": "2025-10-01", "id": 0, "positions": {"AAPL": 0, "MSFT": 0, ..., "CASH": 10000.0}}
{"date": "2025-10-01", "id": 1, "this_action": {"action": "buy", "symbol": "AAPL", "amount": 5}, "positions": {"AAPL": 5, ..., "CASH": 9123.45}}
```

### Log File Format
```json
{"timestamp": "2025-10-01T10:23:45", "signature": "gpt-5", "new_messages": [{"role": "user", "content": "..."}]}
```

---

## 🚀 Next Steps

After your first successful run:

1. **Analyze Results**
   - Check position files
   - Review trading decisions in logs
   - Calculate returns

2. **Enable More Models**
   - Add API keys for Claude, DeepSeek, etc.
   - Enable in config
   - Compare performance

3. **Customize Configuration**
   - Adjust date ranges
   - Modify initial capital
   - Change max_steps

4. **Contribute**
   - Add new trading strategies
   - Improve MCP tools
   - Submit pull requests

---

## 📞 Getting Help

If you encounter issues:

1. **Check Logs**
   - Service logs in `logs/`
   - Trading logs in `data/agent_data/[model]/log/`

2. **Review Documentation**
   - `README.md` - Project overview
   - `Claude.md` - Deep analysis
   - `configs/README.md` - Configuration guide

3. **Debug Mode**
   ```bash
   # Run with verbose output
   python3 -v main.py
   
   # Or add print statements in code
   ```

4. **Community**
   - Check `Communication.md` for community channels
   - Open GitHub issues

---

**Happy Trading! 📈🤖**

*Last Updated: October 28, 2025*
