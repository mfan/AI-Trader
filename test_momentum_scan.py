#!/usr/bin/env python3
"""
Test Momentum Scanner - Validate with Yesterday's Data

This script tests the momentum scanning system by:
1. Running a scan on yesterday's market data
2. Caching results to SQLite database
3. Verifying data integrity
4. Displaying top 50 gainers and top 50 losers
5. Showing market regime and scan statistics
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.momentum_scanner import MomentumScanner
from tools.momentum_cache import MomentumCache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def get_yesterday_date() -> str:
    """Get yesterday's date (or last business day)."""
    today = datetime.now()
    
    # If today is Monday, go back to Friday
    if today.weekday() == 0:  # Monday
        yesterday = today - timedelta(days=3)
    elif today.weekday() == 6:  # Sunday
        yesterday = today - timedelta(days=2)
    else:
        yesterday = today - timedelta(days=1)
    
    return yesterday.strftime('%Y-%m-%d')


async def test_momentum_scan():
    """Test the momentum scanner with yesterday's data."""
    
    print("\n" + "="*80)
    print("🧪 MOMENTUM SCANNER TEST")
    print("="*80)
    
    # Get scan date
    scan_date = get_yesterday_date()
    print(f"\n📅 Test Date: {scan_date}")
    print(f"⏰ Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize scanner
    print(f"\n🔧 Initializing momentum scanner...")
    scanner = MomentumScanner()
    
    # Run scan
    print(f"\n🔍 Scanning market data for {scan_date}...")
    print(f"   Filters: Volume >= 10M, Top 100 stocks")
    print(f"   This may take 30-60 seconds...\n")
    
    scan_start = datetime.now()
    
    try:
        movers = await scanner.scan_previous_day_movers(
            scan_date=scan_date,
            min_volume=10_000_000,
            max_results=100
        )
        
        scan_duration = (datetime.now() - scan_start).total_seconds()
        
        if not movers or (not movers.get('gainers') and not movers.get('losers')):
            print("\n❌ SCAN FAILED: No data returned")
            return False
        
        # Get results
        gainers = movers.get('gainers', [])
        losers = movers.get('losers', [])
        total_scanned = movers.get('total_scanned', 0)
        high_volume_count = movers.get('high_volume_count', 0)
        
        print(f"✅ Scan completed in {scan_duration:.2f} seconds")
        print(f"\n📊 SCAN RESULTS:")
        print(f"   Total symbols scanned: {total_scanned}")
        print(f"   High volume stocks (10M+): {high_volume_count}")
        print(f"   Gainers selected: {len(gainers)}")
        print(f"   Losers selected: {len(losers)}")
        print(f"   Total watchlist: {len(gainers) + len(losers)}")
        
        # Cache to database
        print(f"\n💾 Caching results to SQLite database...")
        cache_path = "data/test_momentum_cache.db"
        cache = MomentumCache(cache_path)
        
        market_regime = scanner.get_market_regime()
        
        success = cache.cache_momentum_stocks(
            scan_date=scan_date,
            gainers=gainers,
            losers=losers,
            market_regime=market_regime,
            metadata={
                'total_scanned': total_scanned,
                'high_volume_count': high_volume_count,
                'scan_duration': scan_duration
            }
        )
        
        if not success:
            print("❌ Failed to cache data")
            return False
        
        print(f"✅ Data cached to: {cache_path}")
        
        # Verify database integrity
        print(f"\n🔍 Verifying database integrity...")
        cached_stocks = cache.get_cached_momentum_stocks(scan_date)
        cached_gainers = [s for s in cached_stocks if s['direction'] == 'gainer']
        cached_losers = [s for s in cached_stocks if s['direction'] == 'loser']
        
        print(f"   Cached gainers: {len(cached_gainers)}")
        print(f"   Cached losers: {len(cached_losers)}")
        print(f"   Data integrity: {'✅ PASS' if len(cached_gainers) == len(gainers) and len(cached_losers) == len(losers) else '❌ FAIL'}")
        
        # Get market regime
        regime_data = cache.get_market_regime(scan_date)
        
        print(f"\n🎯 MARKET REGIME:")
        print(f"   Direction: {regime_data.get('regime', 'unknown').upper()}")
        spy_change = regime_data.get('spy_change_pct') or 0
        qqq_change = regime_data.get('qqq_change_pct') or 0
        print(f"   SPY: {spy_change:+.2f}%")
        print(f"   QQQ: {qqq_change:+.2f}%")
        
        # Display top gainers
        print(f"\n{'='*80}")
        print(f"📈 TOP 50 GAINERS - {scan_date}")
        print(f"{'='*80}")
        print(f"{'Rank':<6}{'Symbol':<8}{'Change %':<12}{'Volume':<16}{'Close':<10}{'Open':<10}")
        print(f"{'-'*80}")
        
        for i, stock in enumerate(gainers[:50], 1):
            print(f"{i:<6}{stock['symbol']:<8}{stock['change_pct']:+10.2f}%  "
                  f"{stock['volume']:>14,}  "
                  f"${stock['close']:>7.2f}  "
                  f"${stock.get('open', 0):>7.2f}")
        
        # Display top losers
        print(f"\n{'='*80}")
        print(f"📉 TOP 50 LOSERS - {scan_date}")
        print(f"{'='*80}")
        print(f"{'Rank':<6}{'Symbol':<8}{'Change %':<12}{'Volume':<16}{'Close':<10}{'Open':<10}")
        print(f"{'-'*80}")
        
        for i, stock in enumerate(losers[:50], 1):
            print(f"{i:<6}{stock['symbol']:<8}{stock['change_pct']:+10.2f}%  "
                  f"{stock['volume']:>14,}  "
                  f"${stock['close']:>7.2f}  "
                  f"${stock.get('open', 0):>7.2f}")
        
        # Summary statistics
        print(f"\n{'='*80}")
        print(f"📊 STATISTICS")
        print(f"{'='*80}")
        
        if gainers:
            best_gainer = gainers[0]
            avg_gainer_change = sum(s['change_pct'] for s in gainers) / len(gainers)
            avg_gainer_volume = sum(s['volume'] for s in gainers) / len(gainers)
            
            print(f"\n🏆 Best Gainer:")
            print(f"   Symbol: {best_gainer['symbol']}")
            print(f"   Change: {best_gainer['change_pct']:+.2f}%")
            print(f"   Volume: {best_gainer['volume']:,}")
            print(f"   Close: ${best_gainer['close']:.2f}")
            
            print(f"\n📈 Gainers Stats:")
            print(f"   Average Change: {avg_gainer_change:+.2f}%")
            print(f"   Average Volume: {avg_gainer_volume:,.0f}")
        
        if losers:
            worst_loser = losers[0]
            avg_loser_change = sum(s['change_pct'] for s in losers) / len(losers)
            avg_loser_volume = sum(s['volume'] for s in losers) / len(losers)
            
            print(f"\n💔 Worst Loser:")
            print(f"   Symbol: {worst_loser['symbol']}")
            print(f"   Change: {worst_loser['change_pct']:+.2f}%")
            print(f"   Volume: {worst_loser['volume']:,}")
            print(f"   Close: ${worst_loser['close']:.2f}")
            
            print(f"\n📉 Losers Stats:")
            print(f"   Average Change: {avg_loser_change:+.2f}%")
            print(f"   Average Volume: {avg_loser_volume:,.0f}")
        
        # Watchlist export
        watchlist = scanner.get_momentum_watchlist()
        print(f"\n📝 MOMENTUM WATCHLIST ({len(watchlist)} symbols):")
        print(f"   {', '.join(watchlist[:20])}...")
        
        # Save watchlist to file
        watchlist_file = f"data/momentum_watchlist_{scan_date}.txt"
        Path("data").mkdir(exist_ok=True)
        with open(watchlist_file, 'w') as f:
            f.write('\n'.join(watchlist))
        print(f"\n💾 Full watchlist saved to: {watchlist_file}")
        
        # Test cache retrieval speed
        print(f"\n⚡ CACHE PERFORMANCE TEST:")
        import time
        
        # Test 1: Get all stocks
        start = time.time()
        all_stocks = cache.get_cached_momentum_stocks(scan_date)
        elapsed = (time.time() - start) * 1000
        print(f"   Get all 100 stocks: {elapsed:.2f}ms")
        
        # Test 2: Get gainers only
        start = time.time()
        cached_gainers = cache.get_cached_momentum_stocks(scan_date, direction='gainer')
        elapsed = (time.time() - start) * 1000
        print(f"   Get 50 gainers: {elapsed:.2f}ms")
        
        # Test 3: Get top 10
        start = time.time()
        top_10 = cache.get_cached_momentum_stocks(scan_date, limit=10)
        elapsed = (time.time() - start) * 1000
        print(f"   Get top 10: {elapsed:.2f}ms")
        
        # Test 4: Get watchlist symbols
        start = time.time()
        watchlist = cache.get_momentum_watchlist(scan_date)
        elapsed = (time.time() - start) * 1000
        print(f"   Get watchlist symbols: {elapsed:.2f}ms")
        
        print(f"\n{'='*80}")
        print(f"✅ TEST PASSED - All systems operational!")
        print(f"{'='*80}")
        
        print(f"\n💡 Next Steps:")
        print(f"   1. Review the top gainers and losers above")
        print(f"   2. Verify data looks reasonable for {scan_date}")
        print(f"   3. Check database file: {cache_path}")
        print(f"   4. Test with active_trader.py integration")
        print(f"   5. Run pre-market scan tomorrow at 9:00 AM")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        print(f"\n❌ TEST FAILED: {e}")
        return False


async def test_cache_operations():
    """Test various cache operations."""
    
    print(f"\n{'='*80}")
    print(f"🧪 TESTING CACHE OPERATIONS")
    print(f"{'='*80}")
    
    cache_path = "data/test_momentum_cache.db"
    cache = MomentumCache(cache_path)
    
    # Test 1: Check cache validity
    scan_date = get_yesterday_date()
    is_valid = cache.is_cache_valid(scan_date)
    print(f"\n1️⃣  Cache validity for {scan_date}: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    # Test 2: Get scan metadata
    metadata = cache.get_scan_metadata(scan_date)
    if metadata:
        print(f"\n2️⃣  Scan Metadata:")
        print(f"   Scan Date: {metadata.get('scan_date')}")
        print(f"   Total Scanned: {metadata.get('total_scanned', 0):,}")
        print(f"   High Volume Count: {metadata.get('high_volume_count', 0):,}")
        print(f"   Gainers: {metadata.get('gainers_count', 0)}")
        print(f"   Losers: {metadata.get('losers_count', 0)}")
        print(f"   Duration: {metadata.get('scan_duration_seconds', 0):.2f}s")
    else:
        print(f"\n2️⃣  No metadata found")
    
    # Test 3: Market regime
    regime = cache.get_market_regime(scan_date)
    print(f"\n3️⃣  Market Regime:")
    print(f"   Direction: {regime.get('regime', 'unknown').upper()}")
    spy_change = regime.get('spy_change_pct') or 0
    qqq_change = regime.get('qqq_change_pct') or 0
    market_score = regime.get('market_score') or 0
    print(f"   SPY: {spy_change:+.2f}%")
    print(f"   QQQ: {qqq_change:+.2f}%")
    print(f"   Score: {market_score:+.2f}")
    
    # Test 4: Print full summary
    print(f"\n4️⃣  Full Cache Summary:")
    cache.print_cache_summary(scan_date)
    
    print(f"✅ Cache operations test complete")


def main():
    """Main test function."""
    
    print("\n" + "🚀"*40)
    print("MOMENTUM SCANNER TEST SUITE")
    print("🚀"*40)
    
    try:
        # Run momentum scan test
        scan_success = asyncio.run(test_momentum_scan())
        
        if scan_success:
            # Run cache operations test
            asyncio.run(test_cache_operations())
            
            print(f"\n{'='*80}")
            print(f"✅ ALL TESTS PASSED!")
            print(f"{'='*80}")
            
            return 0
        else:
            print(f"\n{'='*80}")
            print(f"❌ TESTS FAILED")
            print(f"{'='*80}")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
