"""
Quick test to verify Alpaca connection and get data for OKLO and CRWV
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tools.alpaca_data_feed import AlpacaDataFeed

def test_connection():
    print("Testing Alpaca connection...")
    
    data_feed = AlpacaDataFeed()
    
    # Test with simple price request
    symbols = ["OKLO", "CRWV"]
    
    for symbol in symbols:
        print(f"\n📊 Testing {symbol}...")
        
        # Get latest price
        try:
            price = data_feed.get_latest_price(symbol)
            if price:
                print(f"   ✅ Latest price: ${float(price):.2f}")
            else:
                print(f"   ⚠️  No price data available")
        except Exception as e:
            print(f"   ❌ Error getting price: {e}")
        
        # Get recent bar
        try:
            end_date = datetime(2025, 11, 2)  # Saturday Nov 2
            start_date = end_date - timedelta(days=5)
            
            bars = data_feed.get_daily_bars(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            
            if bars:
                print(f"   ✅ Got {len(bars)} bars")
                latest = bars[-1]
                print(f"   📅 Latest bar: {latest.timestamp.strftime('%Y-%m-%d')}")
                print(f"   💰 Close: ${float(latest.close):.2f}, Volume: {latest.volume:,}")
            else:
                print(f"   ⚠️  No bar data available")
        except Exception as e:
            print(f"   ❌ Error getting bars: {e}")

if __name__ == "__main__":
    test_connection()
