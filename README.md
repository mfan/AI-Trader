# Active Trader - Continuous Trading Program

## Overview

The Active Trader program runs continuously throughout the day, automatically:
1. Loading current portfolio positions from Alpaca every 10 minutes (configurable)
2. Checking latest news for portfolio stocks via Jina Search
3. Making trading decisions using DeepSeek AI agent
4. Executing trades through Alpaca's paper trading API
5. Repeating the cycle indefinitely until stopped

## Quick Start

### Option 1: Using the Startup Script (Recommended)

```bash
# Start with default settings (10-minute intervals)
./start_active_trader.sh

# Start with custom config
./start_active_trader.sh configs/my_config.json

# Start with custom interval (5 minutes)
./start_active_trader.sh configs/default_config.json 5
```

### Option 2: Manual Start

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Start MCP services manually
cd agent_tools
nohup python tool_jina_search.py >> /tmp/jina_mcp.log 2>&1 &
nohup python tool_alpaca_data.py >> /tmp/alpaca_data_mcp.log 2>&1 &
nohup python tool_alpaca_trade.py >> /tmp/alpaca_trade_mcp.log 2>&1 &
cd ..

# 3. Wait for services to start
sleep 5

# 4. Run the active trader
python active_trader.py [config_path] [interval_minutes]
```

## Features

### Continuous Operation
- **Non-stop trading**: Runs indefinitely until manually stopped
- **Configurable intervals**: Default 10 minutes, adjustable via command line
- **Market hours awareness**: Optional check to only trade during market hours (9:30 AM - 4:00 PM ET)
- **Graceful shutdown**: Press Ctrl+C to stop after current cycle completes

### Automatic Portfolio Management
- **Position monitoring**: Checks current positions every cycle
- **News analysis**: Fetches latest news for all portfolio stocks
- **AI-driven decisions**: Uses DeepSeek Chat v3.1 for trading decisions
- **Automated execution**: Places buy/sell orders through Alpaca

### Error Handling
- **Retry logic**: Configurable retries for failed operations
- **Failure tracking**: Stops after 3 consecutive failed cycles
- **Detailed logging**: All activity logged to console and log files

### Real-time Updates
Each cycle displays:
- Current time and cycle number
- Portfolio positions and cash balance
- Trading actions taken
- Next check time

## Configuration

The program uses the same `configs/default_config.json` format:

```json
{
  "agent_type": "BaseAgent",
  "date_range": {
    "init_date": "2025-10-31",
    "end_date": "2025-10-31"
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
    "initial_cash": 10000.0
  }
}
```

## Command Line Arguments

```bash
python active_trader.py [config_path] [interval_minutes]
```

- `config_path`: Path to config file (default: `configs/default_config.json`)
- `interval_minutes`: Minutes between trading cycles (default: `10`)

### Examples

```bash
# Run with 5-minute intervals
python active_trader.py configs/default_config.json 5

# Run with 15-minute intervals
python active_trader.py configs/default_config.json 15

# Run with default 10-minute intervals
python active_trader.py
```

## Market Hours Control

By default, the program checks if it's within market hours (9:30 AM - 4:00 PM ET).

To enable **24/7 trading** for paper trading/testing, edit `active_trader.py`:

```python
def is_market_hours():
    # Uncomment this line for 24/7 trading
    return True
```

## Monitoring

### Check Running Status

```bash
# Check if MCP services are running
lsof -nP -iTCP:8001,8004,8005 -sTCP:LISTEN

# Check active trader process
ps aux | grep active_trader.py
```

### View Logs

```bash
# MCP service logs
tail -f /tmp/jina_mcp.log
tail -f /tmp/alpaca_data_mcp.log
tail -f /tmp/alpaca_trade_mcp.log

# Active trader output (if redirected)
tail -f active_trader.log
```

## Stopping the Program

### Graceful Shutdown
Press `Ctrl+C` once - the program will complete the current cycle and then stop.

### Force Stop
```bash
# Kill active trader
pkill -f active_trader.py

# Stop MCP services
pkill -f "tool_jina_search.py"
pkill -f "tool_alpaca_data.py"
pkill -f "tool_alpaca_trade.py"
```

## Sample Output

```
🚀 ACTIVE TRADING PROGRAM STARTED
================================================================================
🤖 Agent type: BaseAgent
📅 Start date: 2025-10-31
🤖 Model: deepseek (deepseek-chat-v3.1)
⏱️  Check interval: 10 minutes
⚙️  Agent config: max_steps=30, max_retries=3
💰 Initial cash: $10000.00
================================================================================

🔧 Initializing trading agent...
✅ BaseAgent instance created successfully
✅ Agent initialization complete
🎯 Starting continuous trading loop...

================================================================================
🔄 TRADING CYCLE #1
⏰ Time: 2025-10-31 10:00:00
================================================================================

[Trading activity appears here...]

📊 CYCLE #1 SUMMARY:
   ├─ Date: 2025-10-31
   ├─ Total records: 15
   ├─ Cash balance: $9500.00
   └─ Positions:
      ├─ AAPL: 10
      ├─ AMD: 5

✅ Cycle #1 completed successfully

⏳ Next trading cycle at: 2025-10-31 10:10:00
💤 Sleeping for 10 minutes...
```

## Comparison with Other Programs

| Program | Purpose | Execution |
|---------|---------|-----------|
| `trade.py` | Single trading session | One-time run for specific date range |
| `active_trader.py` | Continuous trading | Runs indefinitely with periodic checks |
| `check_positions_mcp.py` | Testing | Verify MCP connectivity only |

## Troubleshooting

### Services won't start
```bash
# Check if ports are already in use
lsof -nP -iTCP:8001,8004,8005 -sTCP:LISTEN

# Kill existing processes
pkill -f "tool_"
```

### Connection errors
- Ensure all 3 MCP services are running
- Wait 5-10 seconds after starting services
- Check service logs in `/tmp/*.log`

### Trading not executing
- Verify Alpaca API credentials in `.env`
- Check if paper trading is enabled in Alpaca account
- Review agent logs for decision-making details

## Best Practices

1. **Start with longer intervals**: Begin with 10-15 minute intervals to avoid excessive API calls
2. **Monitor first few cycles**: Watch the output to ensure everything works correctly
3. **Check logs regularly**: Review MCP service logs for any issues
4. **Use paper trading**: Always test with Alpaca paper trading first
5. **Set cash limits**: Configure appropriate `initial_cash` in config to limit risk

## Safety Features

- ✅ Graceful shutdown on Ctrl+C
- ✅ Automatic stop after 3 consecutive failures
- ✅ Market hours check (optional)
- ✅ Detailed error reporting
- ✅ Position tracking and validation
- ✅ Configurable risk parameters

## Next Steps

After starting the active trader:

1. Monitor the first few cycles
2. Verify trades in Alpaca dashboard
3. Adjust interval timing based on your strategy
4. Review and tune agent configuration
5. Check portfolio performance regularly
