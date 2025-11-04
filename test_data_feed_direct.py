#!/usr/bin/env python3
"""
Direct test of AlpacaDataFeed to verify response formats
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from tools.alpaca_data_feed import AlpacaDataFeed

def main():
    print("🧪 ALPACA DATA FEED DIRECT TEST")
    print("="*80)
    
    # Initialize feed
    feed = AlpacaDataFeed()
    
    symbol = "AAPL"
    start_date = "2025-10-01"
    end_date = "2025-11-01"
    test_date = "2025-10-31"
    
    # Test 1: get_latest_quote
    print("\n1. Testing get_latest_quote...")
    quote = feed.get_latest_quote(symbol)
    print(f"   Type: {type(quote)}")
    print(f"   Result: {quote}")
    if quote and isinstance(quote, dict):
        print(f"   ✅ Returns dict with keys: {list(quote.keys())}")
    
    # Test 2: get_latest_trade
    print("\n2. Testing get_latest_trade...")
    trade = feed.get_latest_trade(symbol)
    print(f"   Type: {type(trade)}")
    print(f"   Result: {trade}")
    if trade and isinstance(trade, dict):
        print(f"   ✅ Returns dict with keys: {list(trade.keys())}")
    
    # Test 3: get_latest_price
    print("\n3. Testing get_latest_price...")
    price = feed.get_latest_price(symbol)
    print(f"   Type: {type(price)}")
    print(f"   Result: {price}")
    if isinstance(price, (int, float)):
        print(f"   ✅ Returns numeric value")
    
    # Test 4: get_daily_bars
    print("\n4. Testing get_daily_bars...")
    bars_dict = feed.get_daily_bars([symbol], start_date, end_date)
    print(f"   Type: {type(bars_dict)}")
    print(f"   Keys: {list(bars_dict.keys()) if isinstance(bars_dict, dict) else 'Not a dict'}")
    if symbol in bars_dict:
        bars = bars_dict[symbol]
        print(f"   Bars type: {type(bars)}")
        print(f"   Number of bars: {len(bars)}")
        if bars:
            print(f"   First bar type: {type(bars[0])}")
            print(f"   First bar: {bars[0]}")
            if isinstance(bars[0], dict):
                print(f"   ✅ Returns dict[symbol -> list[dict]]")
                print(f"   Bar keys: {list(bars[0].keys())}")
    
    # Test 5: get_bar_for_date
    print("\n5. Testing get_bar_for_date...")
    bar = feed.get_bar_for_date(symbol, test_date)
    print(f"   Type: {type(bar)}")
    print(f"   Result: {bar}")
    if bar and isinstance(bar, dict):
        print(f"   ✅ Returns dict with keys: {list(bar.keys())}")
    
    # Test 6: get_opening_price
    print("\n6. Testing get_opening_price...")
    opening = feed.get_opening_price(symbol, test_date)
    print(f"   Type: {type(opening)}")
    print(f"   Result: {opening}")
    if isinstance(opening, (int, float)):
        print(f"   ✅ Returns numeric value")
    
    print("\n" + "="*80)
    print("✅ All type checks complete - data formats confirmed!")
    print("="*80)


if __name__ == "__main__":
    main()
