#!/bin/bash
# filepath: /home/mfan/work/aitrader/scripts/install_alpaca_mcp.sh
# 
# Complete Installation Script for Alpaca Official MCP Server
# This script automates the entire setup process
#
# Usage: ./scripts/install_alpaca_mcp.sh

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Alpaca Official MCP Server - Installation       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check Python version
echo -e "${YELLOW}[1/6] Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "      Found Python $python_version"

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    echo -e "${RED}      ❌ Python 3.10+ required. Current: $python_version${NC}"
    exit 1
fi
echo -e "${GREEN}      ✅ Python version OK${NC}"
echo ""

# Step 2: Check for .env file
echo -e "${YELLOW}[2/6] Checking environment configuration...${NC}"
if [ ! -f .env ]; then
    echo -e "${YELLOW}      ⚠️  .env file not found. Creating from template...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}      ✅ Created .env from .env.example${NC}"
        echo -e "${YELLOW}      📝 Please edit .env and add your API keys:${NC}"
        echo "         - ALPACA_API_KEY"
        echo "         - ALPACA_SECRET_KEY"
        echo ""
        echo -e "${BLUE}      Press Enter when ready to continue...${NC}"
        read
    else
        echo -e "${RED}      ❌ .env.example not found${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}      ✅ .env file found${NC}"
fi

# Check if API keys are set
if ! grep -q "ALPACA_API_KEY=.*[A-Z]" .env || ! grep -q "ALPACA_SECRET_KEY=" .env; then
    echo -e "${YELLOW}      ⚠️  Alpaca API keys not configured in .env${NC}"
    echo ""
    echo -e "${BLUE}      To get your API keys:${NC}"
    echo "      1. Go to https://app.alpaca.markets/paper/dashboard/overview"
    echo "      2. Create a free paper trading account (if you don't have one)"
    echo "      3. Generate API keys from the dashboard"
    echo "      4. Add them to your .env file:"
    echo ""
    echo "         ALPACA_API_KEY=\"your_key_here\""
    echo "         ALPACA_SECRET_KEY=\"your_secret_here\""
    echo ""
    echo -e "${BLUE}      Press Enter when ready to continue...${NC}"
    read
fi
echo ""

# Step 3: Install uv package manager
echo -e "${YELLOW}[3/6] Installing uv package manager...${NC}"
if command -v uvx &> /dev/null; then
    echo -e "${GREEN}      ✅ uv already installed${NC}"
else
    echo "      Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Source the new PATH
    export PATH="$HOME/.cargo/bin:$PATH"
    
    if command -v uvx &> /dev/null; then
        echo -e "${GREEN}      ✅ uv installed successfully${NC}"
        echo -e "${YELLOW}      📝 Note: You may need to restart your terminal for 'uvx' command${NC}"
    else
        echo -e "${YELLOW}      ⚠️  uv installed but not in PATH yet${NC}"
        echo "      Please run: exec \$SHELL"
        echo "      Then re-run this script"
        exit 0
    fi
fi
echo ""

# Step 4: Install Python dependencies
echo -e "${YELLOW}[4/6] Installing Python dependencies...${NC}"
if [ -f requirements.txt ]; then
    echo "      Installing from requirements.txt..."
    pip install -r requirements.txt -q
    echo -e "${GREEN}      ✅ Dependencies installed${NC}"
else
    echo -e "${RED}      ❌ requirements.txt not found${NC}"
    exit 1
fi
echo ""

# Step 5: Install Alpaca MCP Server
echo -e "${YELLOW}[5/6] Installing Alpaca MCP Server...${NC}"
if pip show alpaca-mcp-server &> /dev/null; then
    version=$(pip show alpaca-mcp-server | grep Version | awk '{print $2}')
    echo -e "${GREEN}      ✅ alpaca-mcp-server already installed (v$version)${NC}"
else
    echo "      Installing alpaca-mcp-server..."
    pip install alpaca-mcp-server -q
    echo -e "${GREEN}      ✅ alpaca-mcp-server installed${NC}"
fi

# Verify installation
if command -v alpaca-mcp-server &> /dev/null; then
    version=$(alpaca-mcp-server --version 2>&1 | grep -oP '[\d.]+' | head -1)
    echo -e "${GREEN}      ✅ Verified: alpaca-mcp-server v$version${NC}"
else
    # Try with uvx
    if uvx alpaca-mcp-server --version &> /dev/null; then
        version=$(uvx alpaca-mcp-server --version 2>&1 | grep -oP '[\d.]+' | head -1)
        echo -e "${GREEN}      ✅ Verified: alpaca-mcp-server v$version (via uvx)${NC}"
    else
        echo -e "${RED}      ❌ Installation verification failed${NC}"
        exit 1
    fi
fi
echo ""

# Step 6: Create necessary directories
echo -e "${YELLOW}[6/6] Setting up directories...${NC}"
mkdir -p logs
mkdir -p scripts
echo -e "${GREEN}      ✅ Directories created${NC}"
echo ""

# Make startup script executable
if [ -f scripts/start_alpaca_mcp.sh ]; then
    chmod +x scripts/start_alpaca_mcp.sh
    echo -e "${GREEN}      ✅ Startup script is executable${NC}"
fi
echo ""

# Installation complete
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Installation Complete! ✅                        ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}📋 Next Steps:${NC}"
echo ""
echo -e "${YELLOW}1. Verify your .env configuration:${NC}"
echo "   cat .env | grep ALPACA"
echo ""
echo -e "${YELLOW}2. Start the Alpaca MCP server:${NC}"
echo "   ./scripts/start_alpaca_mcp.sh"
echo ""
echo -e "${YELLOW}3. Test the integration (in another terminal):${NC}"
echo "   python tools/alpaca_mcp_bridge.py"
echo ""
echo -e "${YELLOW}4. Start all MCP services:${NC}"
echo "   sudo ./manage_services.sh start-mcp"
echo ""
echo -e "${YELLOW}5. Run AI-Trader with Alpaca support:${NC}"
echo "   python active_trader.py"
echo ""

echo -e "${BLUE}📚 Documentation:${NC}"
echo "   • Quick Start: ALPACA_MCP_QUICKSTART.md"
echo "   • Complete Guide: ALPACA_OFFICIAL_MCP_INTEGRATION.md"
echo "   • Architecture: ALPACA_MCP_ARCHITECTURE.md"
echo ""

echo -e "${GREEN}Happy Trading! 🚀${NC}"
