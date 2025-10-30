#!/bin/bash
# Verification Script for Alpaca-Only Migration
# This script verifies that all legacy code has been removed

set -e

echo "🔍 AI-Trader Cleanup Verification Script"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Check 1: Verify legacy files are deleted
echo "📁 Checking for deleted legacy files..."
LEGACY_FILES=(
    "agent_tools/tool_get_price_local.py"
    "agent_tools/tool_jina_search.py"
    "agent_tools/tool_trade.py"
)

for file in "${LEGACY_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${RED}✗ FAIL: Legacy file still exists: $file${NC}"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}✓ PASS: Legacy file deleted: $file${NC}"
    fi
done

# Check 2: Verify only Alpaca tools exist in agent_tools
echo ""
echo "📦 Checking agent_tools directory..."
EXPECTED_FILES=(
    "agent_tools/start_mcp_services.py"
    "agent_tools/tool_math.py"
    "agent_tools/tool_alpaca_data.py"
    "agent_tools/tool_alpaca_trade.py"
)

for file in "${EXPECTED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ PASS: Expected file exists: $file${NC}"
    else
        echo -e "${RED}✗ FAIL: Expected file missing: $file${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check 3: Verify .env.example has no legacy variables
echo ""
echo "🔑 Checking .env.example for legacy variables..."
LEGACY_VARS=(
    "ALPHAADVANTAGE_API_KEY"
    "JINA_API_KEY"
    "USE_ALPACA_MCP"
    "ALPACA_TRADING_MODE"
    "SEARCH_HTTP_PORT"
    "TRADE_HTTP_PORT"
    "GETPRICE_HTTP_PORT"
)

for var in "${LEGACY_VARS[@]}"; do
    if grep -q "$var" .env.example 2>/dev/null; then
        echo -e "${RED}✗ FAIL: Legacy variable found in .env.example: $var${NC}"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}✓ PASS: Legacy variable removed: $var${NC}"
    fi
done

# Check 4: Verify required variables exist
echo ""
echo "✅ Checking required variables in .env.example..."
REQUIRED_VARS=(
    "OPENAI_API_KEY"
    "ALPACA_API_KEY"
    "ALPACA_SECRET_KEY"
    "ALPACA_PAPER_TRADING"
    "MATH_HTTP_PORT"
    "ALPACA_DATA_HTTP_PORT"
    "ALPACA_TRADE_HTTP_PORT"
)

for var in "${REQUIRED_VARS[@]}"; do
    if grep -q "$var" .env.example; then
        echo -e "${GREEN}✓ PASS: Required variable exists: $var${NC}"
    else
        echo -e "${RED}✗ FAIL: Required variable missing: $var${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check 5: Verify requirements.txt has Alpaca packages
echo ""
echo "📦 Checking requirements.txt..."
REQUIRED_PACKAGES=(
    "alpaca-py"
    "alpaca-mcp-server"
    "mcp"
    "langchain-mcp-adapters"
)

for package in "${REQUIRED_PACKAGES[@]}"; do
    if grep -q "$package" requirements.txt; then
        echo -e "${GREEN}✓ PASS: Required package in requirements.txt: $package${NC}"
    else
        echo -e "${RED}✗ FAIL: Required package missing: $package${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check 6: Verify new integration files exist
echo ""
echo "📚 Checking integration documentation..."
INTEGRATION_DOCS=(
    "ALPACA_OFFICIAL_MCP_INTEGRATION.md"
    "ALPACA_MCP_QUICKSTART.md"
    "ALPACA_MCP_ARCHITECTURE.md"
    "ALPACA_MCP_SUMMARY.md"
    "ALPACA_MCP_README.md"
    "INTEGRATION_COMPLETE.md"
    "MIGRATION_PLAN.md"
    "CLEANUP_SUMMARY.md"
    "FINAL_CLEANUP_COMPLETE.md"
)

for doc in "${INTEGRATION_DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "${GREEN}✓ PASS: Documentation exists: $doc${NC}"
    else
        echo -e "${YELLOW}⚠ WARNING: Documentation missing: $doc${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# Check 7: Verify bridge and scripts exist
echo ""
echo "🛠️  Checking Alpaca MCP integration files..."
INTEGRATION_FILES=(
    "tools/alpaca_mcp_bridge.py"
    "scripts/install_alpaca_mcp.sh"
    "scripts/start_alpaca_mcp.sh"
)

for file in "${INTEGRATION_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ PASS: Integration file exists: $file${NC}"
    else
        echo -e "${YELLOW}⚠ WARNING: Integration file missing: $file${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# Check 8: Count MCP services
echo ""
echo "🔧 Verifying MCP service configuration..."
if [ -f "agent_tools/start_mcp_services.py" ]; then
    SERVICE_COUNT=$(grep -c "'.*':" agent_tools/start_mcp_services.py | head -1 || echo "0")
    if [ "$SERVICE_COUNT" -eq "3" ]; then
        echo -e "${GREEN}✓ PASS: Correct number of services (3): math, alpaca_data, alpaca_trade${NC}"
    else
        echo -e "${YELLOW}⚠ WARNING: Service count might be incorrect: $SERVICE_COUNT${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Summary
echo ""
echo "========================================"
echo "📊 Verification Summary"
echo "========================================"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED!${NC}"
    echo ""
    echo "🎉 Migration to Alpaca-only architecture is COMPLETE!"
    echo ""
    echo "Next steps:"
    echo "  1. Review FINAL_CLEANUP_COMPLETE.md"
    echo "  2. Test the system with: python main.py"
    echo "  3. Update README.md and RUNNING_GUIDE.md"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  PASSED WITH WARNINGS${NC}"
    echo "Errors: $ERRORS"
    echo "Warnings: $WARNINGS"
    echo ""
    echo "The system should work, but some documentation may be missing."
    exit 0
else
    echo -e "${RED}❌ VERIFICATION FAILED${NC}"
    echo "Errors: $ERRORS"
    echo "Warnings: $WARNINGS"
    echo ""
    echo "Please fix the errors above before proceeding."
    exit 1
fi
