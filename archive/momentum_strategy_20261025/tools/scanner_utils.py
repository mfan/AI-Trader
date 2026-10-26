"""
Scanner Utilities

Orchestrates market scanning operations.
"""
import logging
import time as time_module
from typing import List, Optional

from tools.momentum_scanner import MomentumScanner
from tools.momentum_cache import MomentumCache

logger = logging.getLogger(__name__)

async def run_pre_market_scan(log_path: str, signature: str) -> Optional[List[str]]:
    """
    Run pre-market momentum scan to build daily watchlist.
    
    Scans previous day's top volume movers (10M-20M+ volume):
    - Top 100 gainers
    - Top 100 losers
    - Caches results in SQLite for fast intraday access
    
    Args:
        log_path: Path to store cache database
        signature: Model signature for cache organization
        
    Returns:
        List of symbols for today's trading, or None on error
    """
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 PRE-MARKET MOMENTUM SCAN")
        logger.info(f"{'='*80}")
        logger.info(f"⏰ Scanning previous day's top volume movers...")
        logger.info(f"   Filters: Volume >= 10M, Top 200 stocks (100 gainers + 100 losers)")
        
        scan_start = time_module.time()
        
        # Initialize scanner
        scanner = MomentumScanner()
        
        # Scan previous day
        movers = await scanner.scan_previous_day_movers(
            scan_date=None,  # Auto-detect previous business day
            min_volume=10_000_000,  # 10M minimum
            max_results=200  # Top 200 total (100 gainers + 100 losers)
        )
        
        if not movers or (not movers.get('gainers') and not movers.get('losers')):
            logger.warning("⚠️  No momentum stocks found. Using fallback watchlist.")
            return None
        
        scan_duration = time_module.time() - scan_start
        
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
            logger.warning("⚠️  Failed to cache momentum data")
        else:
            # Archive to historical database (permanent storage)
            logger.info("📦 Archiving to historical database...")
            try:
                from tools.momentum_history import archive_from_cache
                history_path = cache_path.replace('momentum_cache.db', 'momentum_history.db')
                archive_success = archive_from_cache(cache_path, history_path, movers.get('scan_date'))
                if archive_success:
                    logger.info(f"   ✅ Archived to: {history_path}")
                else:
                    logger.warning("   ⚠️  Archiving failed (non-critical)")
            except Exception as e:
                logger.warning(f"   ⚠️  Archiving error: {e} (non-critical)")
            
            # Cleanup old scans from daily cache (keep last 30 days)
            logger.info("🧹 Cleaning up old scan data from cache (keeping 30 days)...")
            cache.cleanup_old_scans(days_to_keep=30)
        
        # Get watchlist
        watchlist = scanner.get_momentum_watchlist()
        
        # Log summary
        gainers = movers.get('gainers', [])
        losers = movers.get('losers', [])
        
        logger.info(f"\n✅ MOMENTUM SCAN COMPLETE")
        logger.info(f"   📈 Gainers: {len(gainers)}")
        logger.info(f"   📉 Losers: {len(losers)}")
        logger.info(f"   📊 Total Watchlist: {len(watchlist)} stocks")
        logger.info(f"   🎯 Market Regime: {market_regime.upper()}")
        logger.info(f"   ⏱️  Scan Duration: {scan_duration:.2f}s")
        logger.info(f"   💾 Cached to: {cache_path}")
        
        if gainers:
            top_gainer = gainers[0]
            logger.info(f"   🏆 Best Gainer: {top_gainer['symbol']} ({top_gainer['change_pct']:+.2f}%)")
        
        if losers:
            top_loser = losers[0]
            logger.info(f"   💔 Worst Loser: {top_loser['symbol']} ({top_loser['change_pct']:+.2f}%)")
        
        logger.info(f"{'='*80}\n")
        
        return watchlist
        
    except Exception as e:
        logger.error(f"❌ Pre-market scan failed: {e}", exc_info=True)
        logging.error(f"Pre-market scan failed: {e}")
        return None
