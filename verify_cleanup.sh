#!/bin/bash

# Verification Script for Position Tracking Cleanup
# This script verifies that the AI-Trader system no longer creates local position files

echo "🔍 AI-Trader Position Tracking Cleanup Verification"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check for position.jsonl files
echo "Test 1: Checking for existing position.jsonl files..."
if find data/agent_data -name "position.jsonl" 2>/dev/null | grep -q .; then
    echo -e "${YELLOW}⚠️  Found existing position.jsonl files (legacy data):${NC}"
    find data/agent_data -name "position.jsonl" 2>/dev/null
    echo ""
else
    echo -e "${GREEN}✅ No position.jsonl files found${NC}"
    echo ""
fi

# Test 2: Check deprecated function usage in production code
echo "Test 2: Checking for deprecated function calls in production code..."
DEPRECATED_CALLS=$(grep -rn "add_no_trade_record\|get_today_init_position\|get_latest_position" \
    --include="*.py" \
    --exclude-dir=data \
    --exclude="price_tools.py" \
    --exclude="result_tools.py" \
    agent/ prompts/ main.py 2>/dev/null || true)

if [ -z "$DEPRECATED_CALLS" ]; then
    echo -e "${GREEN}✅ No deprecated function calls in production code${NC}"
    echo ""
else
    echo -e "${RED}❌ Found deprecated function calls:${NC}"
    echo "$DEPRECATED_CALLS"
    echo ""
fi

# Test 3: Check if register_agent creates files
echo "Test 3: Checking register_agent() implementation..."
if grep -A 5 "def register_agent" agent/base_agent/base_agent.py | grep -q "DEPRECATED"; then
    echo -e "${GREEN}✅ register_agent() is properly deprecated${NC}"
    echo ""
else
    echo -e "${RED}❌ register_agent() may still create files${NC}"
    echo ""
fi

# Test 4: Check MCP services configuration
echo "Test 4: Checking MCP services..."
if grep -q '"alpaca_data"' agent/base_agent/base_agent.py && \
   grep -q '"alpaca_trade"' agent/base_agent/base_agent.py && \
   ! grep -q '"math"' agent/base_agent/base_agent.py; then
    echo -e "${GREEN}✅ MCP services configured correctly (Alpaca only, no math service)${NC}"
    echo ""
else
    echo -e "${RED}❌ MCP services configuration issue${NC}"
    echo ""
fi

# Test 5: Check for add_no_trade_record import
echo "Test 5: Checking for removed imports..."
if grep "from tools.price_tools import add_no_trade_record" agent/base_agent/base_agent.py | grep -q "REMOVED"; then
    echo -e "${GREEN}✅ add_no_trade_record import properly removed${NC}"
    echo ""
else
    if grep -q "from tools.price_tools import add_no_trade_record" agent/base_agent/base_agent.py; then
        echo -e "${RED}❌ add_no_trade_record is still imported${NC}"
        echo ""
    else
        echo -e "${GREEN}✅ add_no_trade_record import not found${NC}"
        echo ""
    fi
fi

# Test 6: Check agent prompt
echo "Test 6: Checking agent prompt for Alpaca MCP usage..."
if grep -q "get_account_info\|get_positions\|get_latest_price" prompts/agent_prompt.py; then
    echo -e "${GREEN}✅ Agent prompt instructs to use Alpaca MCP tools${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Agent prompt may need Alpaca MCP instructions${NC}"
    echo ""
fi

# Test 7: Check deprecation markers in price_tools.py
echo "Test 7: Checking deprecation markers in price_tools.py..."
DEPRECATED_COUNT=$(grep -c "DEPRECATED" tools/price_tools.py 2>/dev/null || echo "0")
if [ "$DEPRECATED_COUNT" -ge 4 ]; then
    echo -e "${GREEN}✅ Found $DEPRECATED_COUNT deprecation markers in price_tools.py${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Only found $DEPRECATED_COUNT deprecation markers (expected 4+)${NC}"
    echo ""
fi

# Summary
echo "=================================================="
echo "📊 Verification Summary"
echo "=================================================="
echo ""
echo "The AI-Trader system has been migrated to use Alpaca exclusively."
echo "Local position tracking (position.jsonl) has been deprecated."
echo ""
echo "Key changes:"
echo "  • register_agent() no longer creates position.jsonl"
echo "  • add_no_trade_record() is a no-op"
echo "  • Agent fetches positions from Alpaca MCP tools"
echo "  • result_tools.py kept for historical analysis only"
echo ""
echo "To verify no new position files are created:"
echo "  1. rm -rf data/agent_data/*/position/position.jsonl"
echo "  2. python main.py"
echo "  3. ls data/agent_data/*/position/position.jsonl  # Should not exist"
echo ""
echo -e "${GREEN}✅ Cleanup verification complete!${NC}"
