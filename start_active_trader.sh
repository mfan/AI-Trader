#!/bin/bash
# Active Trader Startup Script
# Starts all MCP services and launches the active trading program

echo "🚀 Starting Active Trading System..."
echo "=================================="

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Kill any existing MCP service processes
echo "🧹 Cleaning up existing MCP services..."
pkill -f "tool_jina_search.py" 2>/dev/null
pkill -f "tool_alpaca_data.py" 2>/dev/null
pkill -f "tool_alpaca_trade.py" 2>/dev/null
sleep 2

# Start MCP services in background
echo "🔧 Starting MCP services..."
cd agent_tools

# Start Jina Search MCP (port 8001)
nohup python tool_jina_search.py >> /tmp/jina_mcp.log 2>&1 &
JINA_PID=$!
echo "   ✅ Jina Search MCP started (PID: $JINA_PID, Port: 8001)"

# Start Alpaca Data MCP (port 8004)
nohup python tool_alpaca_data.py >> /tmp/alpaca_data_mcp.log 2>&1 &
DATA_PID=$!
echo "   ✅ Alpaca Data MCP started (PID: $DATA_PID, Port: 8004)"

# Start Alpaca Trade MCP (port 8005)
nohup python tool_alpaca_trade.py >> /tmp/alpaca_trade_mcp.log 2>&1 &
TRADE_PID=$!
echo "   ✅ Alpaca Trade MCP started (PID: $TRADE_PID, Port: 8005)"

cd ..

# Wait for services to initialize
echo "⏳ Waiting for MCP services to initialize..."
sleep 5

# Verify services are running
echo "🔍 Verifying MCP services..."
if lsof -nP -iTCP:8001 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "   ✅ Jina Search MCP listening on port 8001"
else
    echo "   ⚠️  Warning: Jina Search MCP may not be ready on port 8001"
fi

if lsof -nP -iTCP:8004 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "   ✅ Alpaca Data MCP listening on port 8004"
else
    echo "   ⚠️  Warning: Alpaca Data MCP may not be ready on port 8004"
fi

if lsof -nP -iTCP:8005 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "   ✅ Alpaca Trade MCP listening on port 8005"
else
    echo "   ⚠️  Warning: Alpaca Trade MCP may not be ready on port 8005"
fi

# Parse command line arguments
CONFIG_PATH="${1:-configs/default_config.json}"
INTERVAL="${2:-10}"

echo ""
echo "=================================="
echo "🎯 Starting Active Trader..."
echo "   Config: $CONFIG_PATH"
echo "   Interval: $INTERVAL minutes"
echo "=================================="
echo ""
echo "💡 Press Ctrl+C to stop gracefully"
echo ""

# Start the active trader
python active_trader.py "$CONFIG_PATH" "$INTERVAL"

# Cleanup on exit
echo ""
echo "🧹 Cleaning up MCP services..."
pkill -f "tool_jina_search.py"
pkill -f "tool_alpaca_data.py"
pkill -f "tool_alpaca_trade.py"

echo "✅ Active Trading System stopped"
