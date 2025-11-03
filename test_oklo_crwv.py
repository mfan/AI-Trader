"""
Test if OKLO and CRWV have historical data available
"""

from tools.alpaca_data_feed import AlpacaDataFeed
from dotenv import load_dotenv

load_dotenv()

def check_symbol_data(symbol: str):
    """Check if a symbol has historical data available"""
    feed = AlpacaDataFeed()
    
    print(f"\n{'='*60}")
    print(f"Checking {symbol}")
    print(f"{'='*60}")
    
    # Check current price
    try:
        price = feed.get_latest_price(symbol)
        print(f"✅ Current price available: ${price:.2f}")
    except Exception as e:
        print(f"❌ No current price: {e}")
        return False
    
    # Check historical data (last month)
    try:
        bars = feed.get_daily_bars([symbol], '2025-10-01', '2025-10-31')
        if bars and symbol in bars and bars[symbol]:
            print(f"✅ Historical data: {len(bars[symbol])} bars available")
            print(f"   Latest bar: {bars[symbol][-1]['timestamp']}")
            print(f"   Close: ${bars[symbol][-1]['close']:.2f}")
            return True
        else:
            print(f"❌ No historical data available in IEX feed")
            print(f"   Note: Symbol may require SIP (paid) data feed")
            print(f"   Or it may be a newer IPO with limited history")
            return False
    except Exception as e:
        print(f"❌ Error getting historical data: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("SYMBOL DATA AVAILABILITY CHECK")
    print("="*60)
    print("Checking if OKLO and CRWV have historical data...")
    print("Using Alpaca IEX feed (free tier)")
    
    symbols = ["OKLO", "CRWV"]
    results = {}
    
    for symbol in symbols:
        results[symbol] = check_symbol_data(symbol)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for symbol, has_data in results.items():
        status = "✅ Ready for TA" if has_data else "❌ No historical data"
        print(f"{symbol}: {status}")
    
    print(f"\n{'='*60}")
    print("RECOMMENDATION")
    print(f"{'='*60}")
    if all(results.values()):
        print("✅ All symbols have data - proceed with technical analysis")
    else:
        print("⚠️  Some symbols lack historical data.")
        print("\nOptions:")
        print("  1. Upgrade to Alpaca SIP data feed (paid)")
        print("  2. Use alternative symbols with available data")
        print("  3. Wait for more trading history to accumulate")
        print("\nTested alternatives: AAPL, TSLA, NVDA, MSFT, GOOGL, AMZN")
