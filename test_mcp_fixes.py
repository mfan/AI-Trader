#!/usr/bin/env python3
"""
Test script to verify MCP data tool fixes
Tests all critical functions with proper error handling
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

# Import the fixed functions directly
from agent_tools.tool_alpaca_data import (
    get_latest_quote,
    get_latest_trade,
    get_latest_price,
    get_stock_bars,
    get_daily_bars,
    get_bar_for_date,
    get_opening_price,
)

def test_function(name, func, *args, **kwargs):
    """Test a function and print results"""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print(f"{'='*80}")
    try:
        result = func(*args, **kwargs)
        
        # Check for errors
        if isinstance(result, dict) and 'error' in result:
            print(f"❌ ERROR: {result['error']}")
            print(f"Full response: {result}")
            return False
        else:
            print(f"✅ SUCCESS")
            # Print a sample of the result
            if isinstance(result, dict):
                if 'bars' in result:
                    print(f"   Symbol: {result.get('symbol')}")
                    print(f"   Bar count: {result.get('count', 0)}")
                    if result.get('bars'):
                        print(f"   First bar: {result['bars'][0]}")
                elif 'price' in result:
                    print(f"   Symbol: {result.get('symbol')}")
                    print(f"   Price: ${result.get('price')}")
                else:
                    print(f"   Result: {result}")
            return True
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("🧪 MCP DATA TOOL VALIDATION TEST SUITE")
    print("="*80)
    
    test_symbol = "AAPL"
    test_date = "2025-10-31"
    start_date = "2025-10-01"
    end_date = "2025-11-01"
    
    results = []
    
    # Test latest quote
    results.append(test_function(
        "get_latest_quote",
        get_latest_quote,
        test_symbol
    ))
    
    # Test latest trade
    results.append(test_function(
        "get_latest_trade",
        get_latest_trade,
        test_symbol
    ))
    
    # Test latest price
    results.append(test_function(
        "get_latest_price",
        get_latest_price,
        test_symbol
    ))
    
    # Test stock bars
    results.append(test_function(
        "get_stock_bars",
        get_stock_bars,
        test_symbol,
        start_date,
        end_date
    ))
    
    # Test daily bars
    results.append(test_function(
        "get_daily_bars",
        get_daily_bars,
        test_symbol,
        start_date,
        end_date
    ))
    
    # Test bar for date
    results.append(test_function(
        "get_bar_for_date",
        get_bar_for_date,
        test_symbol,
        test_date
    ))
    
    # Test opening price
    results.append(test_function(
        "get_opening_price",
        get_opening_price,
        test_symbol,
        test_date
    ))
    
    # Summary
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print(f"\n✅ ALL TESTS PASSED - MCP tools are production-ready!")
        return 0
    else:
        print(f"\n❌ SOME TESTS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
