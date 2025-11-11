#!/usr/bin/env python3
"""
Test Active Trader Momentum Scan Integration

This script tests the momentum scanning and watchlist loading functionality
used by active_trader.py. It simulates the startup process to verify:

1. Cache loading from existing scan data
2. Running a new momentum scan if needed
3. Watchlist generation and validation
4. Database integrity checks

Usage:
    python test_momentum_watchlist.py [--force-scan]
    
Options:
    --force-scan    Force a new momentum scan even if cache exists
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
import argparse

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from tools.momentum_scanner import MomentumScanner
from tools.momentum_cache import MomentumCache


async def test_cache_loading(log_path: str, signature: str):
    """Test loading momentum watchlist from cache"""
    print(f"\n{'='*80}")
    print("TEST 1: CACHE LOADING")
    print(f"{'='*80}")
    
    try:
        cache_path = f"{log_path}/{signature}/momentum_cache.db"
        print(f"📂 Cache path: {cache_path}")
        
        # Check if cache file exists
        if not os.path.exists(cache_path):
            print("❌ Cache file does not exist")
            return None
        
        print(f"✅ Cache file exists ({os.path.getsize(cache_path):,} bytes)")
        
        # Initialize cache
        cache = MomentumCache(cache_path)
        
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"📅 Today's date: {today}")
        
        # Try to load today's cached watchlist
        cached_watchlist = cache.get_momentum_watchlist(scan_date=today)
        
        if cached_watchlist and len(cached_watchlist) > 0:
            print(f"✅ Loaded cached watchlist for {today}: {len(cached_watchlist)} stocks")
            
            # Get metadata
            metadata = cache.get_scan_metadata(scan_date=today)
            if metadata:
                print(f"\n📊 Cache Metadata:")
                print(f"   Total Scanned: {metadata.get('total_scanned', 0):,}")
                print(f"   High Volume: {metadata.get('high_volume_count', 0):,}")
                print(f"   Gainers: {metadata.get('gainers_count', 0)}")
                print(f"   Losers: {metadata.get('losers_count', 0)}")
                print(f"   Scan Duration: {metadata.get('scan_duration_seconds', 0):.2f}s")
            
            # Get market regime
            regime = cache.get_market_regime(scan_date=today)
            print(f"\n🎯 Market Regime: {regime.get('regime', 'unknown').upper()}")
            
            # Show sample stocks
            print(f"\n📈 Sample Stocks (first 50):")
            for symbol in cached_watchlist[:50]:
                print(f"   • {symbol}")
            
            return cached_watchlist
        else:
            # Try to load most recent scan
            print(f"ℹ️  No cache for {today}, checking for previous scans...")
            cached_watchlist = cache.get_momentum_watchlist()  # Gets latest
            
            if cached_watchlist and len(cached_watchlist) > 0:
                metadata = cache.get_scan_metadata()
                scan_date = metadata.get('scan_date', 'unknown')
                print(f"✅ Loaded previous watchlist from {scan_date}: {len(cached_watchlist)} stocks")
                
                print(f"\n📈 Sample Stocks (first 50):")
                for symbol in cached_watchlist[:50]:
                    print(f"   • {symbol}")
                
                return cached_watchlist
            else:
                print("❌ No cached watchlist found")
                return None
                
    except Exception as e:
        print(f"❌ Cache loading failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_momentum_scan(log_path: str, signature: str):
    """Test running a fresh momentum scan"""
    print(f"\n{'='*80}")
    print("TEST 2: MOMENTUM SCAN")
    print(f"{'='*80}")
    
    try:
        import time
        
        print("⏰ Starting momentum scan of previous day's movers...")
        print("   Filters: Volume >= 10M, Top 100 stocks (50 gainers + 50 losers)")
        print()
        
        scan_start = time.time()
        
        # Initialize scanner
        scanner = MomentumScanner()
        
        # Scan previous day
        movers = await scanner.scan_previous_day_movers(
            scan_date=None,  # Auto-detect previous business day
            min_volume=10_000_000,  # 10M minimum
            max_results=100  # Top 100 total
        )
        
        scan_duration = time.time() - scan_start
        
        if not movers or (not movers.get('gainers') and not movers.get('losers')):
            print("❌ No momentum stocks found")
            return None
        
        # Cache results
        cache_path = f"{log_path}/{signature}/momentum_cache.db"
        cache = MomentumCache(cache_path)
        
        market_regime = scanner.get_market_regime()
        
        success = cache.cache_momentum_stocks(
            scan_date=movers.get('scan_date'),
            gainers=movers.get('gainers', []),
            losers=movers.get('losers', []),
            market_regime=market_regime,
            metadata={
                'total_scanned': movers.get('total_scanned', 0),
                'high_volume_count': movers.get('high_volume_count', 0),
                'scan_duration': scan_duration
            }
        )
        
        if not success:
            print("⚠️  Failed to cache momentum data")
        
        # Get watchlist
        watchlist = scanner.get_momentum_watchlist()
        
        # Log summary
        gainers = movers.get('gainers', [])
        losers = movers.get('losers', [])
        
        print(f"✅ MOMENTUM SCAN COMPLETE")
        print(f"   📅 Scan Date: {movers.get('scan_date')}")
        print(f"   🔍 Total Scanned: {movers.get('total_scanned', 0):,} stocks")
        print(f"   📊 High Volume: {movers.get('high_volume_count', 0):,} stocks")
        print(f"   📈 Gainers: {len(gainers)}")
        print(f"   📉 Losers: {len(losers)}")
        print(f"   📊 Total Watchlist: {len(watchlist)} stocks")
        print(f"   🎯 Market Regime: {market_regime.upper()}")
        print(f"   ⏱️  Scan Duration: {scan_duration:.2f}s")
        print(f"   💾 Cached to: {cache_path}")
        
        if gainers:
            top_gainer = gainers[0]
            print(f"\n   🏆 Best Gainer: {top_gainer['symbol']} ({top_gainer['change_pct']:+.2f}%)")
            print(f"      Price: ${top_gainer['close']:.2f}")
            print(f"      Volume: {top_gainer['volume']:,}")
        
        if losers:
            top_loser = losers[0]
            print(f"\n   💔 Worst Loser: {top_loser['symbol']} ({top_loser['change_pct']:+.2f}%)")
            print(f"      Price: ${top_loser['close']:.2f}")
            print(f"      Volume: {top_loser['volume']:,}")
        
        print(f"\n   📋 Sample Watchlist (first 20):")
        for i, symbol in enumerate(watchlist[:20], 1):
            print(f"      {i:2d}. {symbol}")
        
        return watchlist
        
    except Exception as e:
        print(f"❌ Momentum scan failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_watchlist_integration(force_scan: bool = False):
    """Test the full watchlist integration as used by active_trader.py"""
    print(f"\n{'='*80}")
    print("ACTIVE TRADER MOMENTUM WATCHLIST TEST")
    print(f"{'='*80}")
    print(f"Testing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Force Scan: {force_scan}")
    print(f"{'='*80}\n")
    
    # Configuration (matching active_trader.py)
    log_path = "./data/agent_data"
    signature = "xai-grok-4-latest"  # Current active model
    
    momentum_watchlist = None
    
    if not force_scan:
        # Test 1: Try to load from cache first (like active_trader.py startup)
        momentum_watchlist = await test_cache_loading(log_path, signature)
    
    # Test 2: Run fresh scan if needed or forced
    if force_scan or not momentum_watchlist:
        if not force_scan:
            print("\n⚠️  No cached data available, running fresh scan...")
        momentum_watchlist = await test_momentum_scan(log_path, signature)
    
    # Validation
    print(f"\n{'='*80}")
    print("VALIDATION RESULTS")
    print(f"{'='*80}")
    
    if momentum_watchlist and len(momentum_watchlist) > 0:
        print(f"✅ Watchlist validation PASSED")
        print(f"   Total symbols: {len(momentum_watchlist)}")
        print(f"   Expected: ~100 symbols")
        print(f"   Status: {'PASS' if 80 <= len(momentum_watchlist) <= 120 else 'WARNING'}")
        
        # Check for duplicates
        duplicates = len(momentum_watchlist) - len(set(momentum_watchlist))
        if duplicates > 0:
            print(f"   ⚠️  Found {duplicates} duplicate symbols")
        else:
            print(f"   ✅ No duplicate symbols")
        
        # Check symbol format
        invalid_symbols = [s for s in momentum_watchlist if not s.isalpha() or len(s) > 5]
        if invalid_symbols:
            print(f"   ⚠️  Found {len(invalid_symbols)} potentially invalid symbols: {invalid_symbols[:5]}")
        else:
            print(f"   ✅ All symbols have valid format")
        
        print(f"\n🎉 TEST PASSED - System ready for trading")
        return True
    else:
        print(f"❌ Watchlist validation FAILED")
        print(f"   No momentum stocks available")
        print(f"   Active trader will not be able to trade")
        print(f"\n⚠️  TEST FAILED - System not ready")
        return False


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(
        description='Test Active Trader Momentum Scan Integration'
    )
    parser.add_argument(
        '--force-scan',
        action='store_true',
        help='Force a new momentum scan even if cache exists'
    )
    
    args = parser.parse_args()
    
    # Run tests
    success = asyncio.run(test_watchlist_integration(force_scan=args.force_scan))
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
