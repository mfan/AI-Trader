#!/bin/bash
# filepath: /home/mfan/work/aitrader/scripts/start_alpaca_mcp.sh
# Start Alpaca Official MCP Server
#
# This script launches the official Alpaca MCP server with configuration
# from the .env file. The server provides 60+ trading and market data tools
# for AI agents to use via the Model Context Protocol.

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please create .env file with ALPACA_API_KEY and ALPACA_SECRET_KEY"
    exit 1
fi

# Check if API keys are set
if [ -z "$ALPACA_API_KEY" ] || [ -z "$ALPACA_SECRET_KEY" ]; then
    echo -e "${RED}❌ Error: Alpaca API keys not configured${NC}"
    echo "Please add ALPACA_API_KEY and ALPACA_SECRET_KEY to your .env file"
    exit 1
fi

# Check if uvx is installed
if ! command -v uvx &> /dev/null; then
    echo -e "${YELLOW}⚠️  uvx not found. Installing uv package manager...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo -e "${GREEN}✅ uv installed. Please restart your terminal and run this script again.${NC}"
    exit 0
fi

# Check if alpaca-mcp-server is available
if ! uvx alpaca-mcp-server --version &> /dev/null; then
    echo -e "${YELLOW}⚠️  Alpaca MCP Server not found. Installing...${NC}"
    pip install alpaca-mcp-server
    echo -e "${GREEN}✅ Alpaca MCP Server installed${NC}"
fi

# Set default port if not configured
ALPACA_MCP_PORT=${ALPACA_MCP_PORT:-8004}

# Set paper trading mode
ALPACA_PAPER=${ALPACA_PAPER_TRADING:-true}

# Display configuration
echo -e "${GREEN}🚀 Starting Alpaca Official MCP Server${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Configuration:"
echo "  • Port: $ALPACA_MCP_PORT"
echo "  • Paper Trading: $ALPACA_PAPER"
echo "  • API Key: ${ALPACA_API_KEY:0:10}..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create logs directory
mkdir -p logs

# Start the server
echo -e "\n${GREEN}🔄 Starting server...${NC}"
echo "📝 Logs: logs/alpaca_mcp.log"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Run the server with environment variables
ALPACA_API_KEY="$ALPACA_API_KEY" \
ALPACA_SECRET_KEY="$ALPACA_SECRET_KEY" \
uvx alpaca-mcp-server serve 2>&1 | tee logs/alpaca_mcp.log
