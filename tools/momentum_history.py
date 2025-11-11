"""
Momentum History Archive - Long-Term Historical Database

Archives daily momentum scan data for:
- Backtesting and strategy analysis
- Performance tracking over time
- Pattern recognition
- Historical momentum analysis

Separate from daily cache for:
- Never gets flushed (permanent archive)
- Optimized for historical queries
- Supports multi-year backtests
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import threading

logger = logging.getLogger(__name__)

# Default location for historical archive
DEFAULT_HISTORY_PATH = "data/momentum_history.db"


class MomentumHistory:
    """
    Historical archive for momentum scan data.
    
    Features:
    - Permanent storage (never auto-deleted)
    - Optimized for time-series queries
    - Supports backtesting
    - Tracks momentum patterns over time
    - Separate from daily cache
    """
    
    def __init__(self, db_path: str = DEFAULT_HISTORY_PATH):
        """
        Initialize historical archive.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        
        # Create database directory if needed
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        logger.info(f"✅ Momentum history initialized: {db_path}")
    
    def _init_database(self):
        """Create historical database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Historical daily movers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historical_movers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,  -- 'gainer' or 'loser'
                    rank INTEGER NOT NULL,
                    
                    -- Price data
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    change_pct REAL,
                    
                    -- Technical indicators (JSON)
                    indicators TEXT,
                    
                    -- Momentum score
                    momentum_score REAL,
                    
                    -- Archive metadata
                    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    
                    -- Unique constraint
                    UNIQUE(scan_date, symbol)
                )
            """)
            
            # Indices for fast time-series queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hist_scan_date 
                ON historical_movers(scan_date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hist_symbol 
                ON historical_movers(symbol)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hist_symbol_date 
                ON historical_movers(symbol, scan_date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hist_direction_rank 
                ON historical_movers(direction, rank)
            """)
            
            # Historical market regime
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historical_regime (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_date TEXT NOT NULL UNIQUE,
                    regime TEXT NOT NULL,
                    spy_change_pct REAL,
                    qqq_change_pct REAL,
                    market_score REAL,
                    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hist_regime_date 
                ON historical_regime(scan_date)
            """)
            
            # Historical scan statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historical_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_date TEXT NOT NULL UNIQUE,
                    total_scanned INTEGER,
                    high_volume_count INTEGER,
                    gainers_count INTEGER,
                    losers_count INTEGER,
                    avg_gainer_change REAL,
                    avg_loser_change REAL,
                    max_gainer_change REAL,
                    max_loser_change REAL,
                    scan_duration_seconds REAL,
                    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("✅ Historical database schema initialized")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def archive_daily_scan(
        self,
        scan_date: str,
        movers: List[Dict],
        market_regime: Optional[Dict] = None,
        scan_metadata: Optional[Dict] = None
    ) -> bool:
        """
        Archive daily scan data to historical database.
        
        Uses UPSERT (INSERT OR REPLACE) to handle duplicates gracefully.
        Updates existing records if scan is re-run for same date.
        
        Args:
            scan_date: Date of scan (YYYY-MM-DD)
            movers: List of all stock records (gainers + losers)
            market_regime: Market regime data
            scan_metadata: Scan statistics
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Archive movers (UPSERT)
                    for stock in movers:
                        cursor.execute("""
                            INSERT OR REPLACE INTO historical_movers
                            (scan_date, symbol, direction, rank, open, high, low, close,
                             volume, change_pct, indicators, momentum_score, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            scan_date,
                            stock['symbol'],
                            stock['direction'],
                            stock['rank'],
                            stock.get('open'),
                            stock.get('high'),
                            stock.get('low'),
                            stock.get('close'),
                            stock.get('volume'),
                            stock.get('change_pct'),
                            stock.get('indicators'),  # Already JSON string
                            stock.get('momentum_score'),
                            current_time
                        ))
                    
                    # Archive market regime
                    if market_regime:
                        cursor.execute("""
                            INSERT OR REPLACE INTO historical_regime
                            (scan_date, regime, spy_change_pct, qqq_change_pct, market_score)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            scan_date,
                            market_regime.get('regime', 'neutral'),
                            market_regime.get('spy_change_pct'),
                            market_regime.get('qqq_change_pct'),
                            market_regime.get('market_score')
                        ))
                    
                    # Archive statistics
                    if scan_metadata:
                        # Calculate additional stats from movers
                        gainers = [m for m in movers if m.get('direction') == 'gainer']
                        losers = [m for m in movers if m.get('direction') == 'loser']
                        
                        avg_gainer = sum(g.get('change_pct', 0) for g in gainers) / len(gainers) if gainers else 0
                        avg_loser = sum(l.get('change_pct', 0) for l in losers) / len(losers) if losers else 0
                        max_gainer = max((g.get('change_pct', 0) for g in gainers), default=0)
                        max_loser = min((l.get('change_pct', 0) for l in losers), default=0)
                        
                        cursor.execute("""
                            INSERT OR REPLACE INTO historical_stats
                            (scan_date, total_scanned, high_volume_count, gainers_count, losers_count,
                             avg_gainer_change, avg_loser_change, max_gainer_change, max_loser_change,
                             scan_duration_seconds)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            scan_date,
                            scan_metadata.get('total_scanned', 0),
                            scan_metadata.get('high_volume_count', 0),
                            len(gainers),
                            len(losers),
                            avg_gainer,
                            avg_loser,
                            max_gainer,
                            max_loser,
                            scan_metadata.get('scan_duration', 0)
                        ))
                    
                    conn.commit()
                    
                logger.info(f"✅ Archived {len(movers)} stocks for {scan_date} to history")
                return True
                
            except Exception as e:
                logger.error(f"❌ Error archiving to history: {e}", exc_info=True)
                return False
    
    def get_historical_movers(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        symbol: Optional[str] = None,
        direction: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve historical movers for backtesting.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to start_date
            symbol: Filter by symbol
            direction: Filter by 'gainer' or 'loser'
            
        Returns:
            List of historical records
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    if end_date is None:
                        end_date = start_date
                    
                    query = "SELECT * FROM historical_movers WHERE scan_date BETWEEN ? AND ?"
                    params = [start_date, end_date]
                    
                    if symbol:
                        query += " AND symbol = ?"
                        params.append(symbol)
                    
                    if direction:
                        query += " AND direction = ?"
                        params.append(direction)
                    
                    query += " ORDER BY scan_date, rank"
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    # Convert to dictionaries
                    movers = []
                    for row in rows:
                        stock = dict(row)
                        
                        # Parse indicators JSON if present
                        if stock.get('indicators'):
                            try:
                                indicators = json.loads(stock['indicators'])
                                stock.update(indicators)
                            except:
                                pass
                        
                        del stock['indicators']
                        movers.append(stock)
                    
                    return movers
                    
            except Exception as e:
                logger.error(f"❌ Error retrieving history: {e}", exc_info=True)
                return []
    
    def get_symbol_history(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get historical momentum data for a specific symbol.
        
        Useful for analyzing:
        - How often symbol appears in momentum scans
        - Direction patterns (gainer vs loser)
        - Change % trends over time
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date (defaults to today)
            limit: Maximum records
            
        Returns:
            List of historical records for symbol
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        return self.get_historical_movers(
            start_date=start_date,
            end_date=end_date,
            symbol=symbol
        )[:limit]
    
    def get_date_range(self) -> Dict:
        """
        Get the date range of archived data.
        
        Returns:
            Dict with earliest and latest scan dates
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT 
                            MIN(scan_date) as earliest,
                            MAX(scan_date) as latest,
                            COUNT(DISTINCT scan_date) as total_days,
                            COUNT(*) as total_records
                        FROM historical_movers
                    """)
                    
                    row = cursor.fetchone()
                    return {
                        'earliest': row[0],
                        'latest': row[1],
                        'total_days': row[2],
                        'total_records': row[3]
                    }
                    
            except Exception as e:
                logger.error(f"❌ Error getting date range: {e}", exc_info=True)
                return {}
    
    def get_statistics_summary(
        self,
        start_date: str,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        Get summary statistics for a date range.
        
        Args:
            start_date: Start date
            end_date: End date (defaults to start_date)
            
        Returns:
            Dict with aggregated statistics
        """
        with self._lock:
            try:
                if end_date is None:
                    end_date = start_date
                
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT 
                            COUNT(DISTINCT scan_date) as days,
                            AVG(avg_gainer_change) as avg_daily_gainer,
                            AVG(avg_loser_change) as avg_daily_loser,
                            MAX(max_gainer_change) as best_gainer,
                            MIN(max_loser_change) as worst_loser,
                            AVG(gainers_count) as avg_gainers_per_day,
                            AVG(losers_count) as avg_losers_per_day
                        FROM historical_stats
                        WHERE scan_date BETWEEN ? AND ?
                    """, (start_date, end_date))
                    
                    row = cursor.fetchone()
                    
                    if row and row[0]:
                        return {
                            'days': row[0],
                            'avg_daily_gainer_pct': round(row[1] or 0, 2),
                            'avg_daily_loser_pct': round(row[2] or 0, 2),
                            'best_gainer_pct': round(row[3] or 0, 2),
                            'worst_loser_pct': round(row[4] or 0, 2),
                            'avg_gainers_per_day': round(row[5] or 0, 1),
                            'avg_losers_per_day': round(row[6] or 0, 1)
                        }
                    else:
                        return {'error': 'No data for date range'}
                        
            except Exception as e:
                logger.error(f"❌ Error getting statistics: {e}", exc_info=True)
                return {'error': str(e)}
    
    def print_history_summary(self):
        """Print summary of historical archive."""
        date_range = self.get_date_range()
        
        if not date_range.get('earliest'):
            print("\n📊 Historical Archive: EMPTY")
            return
        
        print(f"\n{'='*80}")
        print(f"HISTORICAL MOMENTUM ARCHIVE")
        print(f"{'='*80}")
        print(f"Database: {self.db_path}")
        print(f"\n📅 Date Range:")
        print(f"   Earliest: {date_range['earliest']}")
        print(f"   Latest:   {date_range['latest']}")
        print(f"   Days:     {date_range['total_days']}")
        print(f"   Records:  {date_range['total_records']:,}")
        
        # Get recent stats
        latest = date_range['latest']
        if latest:
            stats = self.get_statistics_summary(latest, latest)
            if not stats.get('error'):
                print(f"\n📊 Latest Day ({latest}):")
                print(f"   Avg Gainer: {stats['avg_daily_gainer_pct']:+.2f}%")
                print(f"   Avg Loser:  {stats['avg_daily_loser_pct']:+.2f}%")
                print(f"   Best Move:  {stats['best_gainer_pct']:+.2f}%")
                print(f"   Worst Move: {stats['worst_loser_pct']:+.2f}%")
        
        print(f"{'='*80}\n")


def archive_from_cache(
    cache_db_path: str,
    history_db_path: Optional[str] = None,
    scan_date: Optional[str] = None
) -> bool:
    """
    Archive data from daily cache to historical database.
    
    Convenience function to transfer data between databases.
    
    Args:
        cache_db_path: Path to momentum_cache.db
        history_db_path: Path to momentum_history.db (optional)
        scan_date: Specific date to archive (defaults to latest)
        
    Returns:
        True if successful
    """
    try:
        from tools.momentum_cache import MomentumCache
        
        # Load from cache
        cache = MomentumCache(cache_db_path)
        movers = cache.get_cached_momentum_stocks(scan_date)
        
        if not movers:
            logger.warning(f"No data to archive for date: {scan_date or 'latest'}")
            return False
        
        # Extract scan date from first record
        actual_scan_date = movers[0]['scan_date']
        
        # Get regime and metadata
        regime = cache.get_market_regime(actual_scan_date)
        metadata = cache.get_scan_metadata(actual_scan_date)
        
        # Archive to history
        if history_db_path is None:
            # Use same directory as cache
            history_db_path = cache_db_path.replace('momentum_cache.db', 'momentum_history.db')
        
        history = MomentumHistory(history_db_path)
        success = history.archive_daily_scan(
            scan_date=actual_scan_date,
            movers=movers,
            market_regime=regime,
            scan_metadata=metadata
        )
        
        if success:
            logger.info(f"✅ Archived {len(movers)} stocks from {actual_scan_date}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error archiving from cache: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Test historical archive
    logging.basicConfig(level=logging.INFO)
    
    # Create test history
    history = MomentumHistory("data/test_momentum_history.db")
    
    # Test data
    test_date = "2025-11-10"
    test_movers = [
        {
            'scan_date': test_date,
            'symbol': 'NVDA',
            'direction': 'gainer',
            'rank': 1,
            'open': 500.0,
            'high': 520.0,
            'low': 498.0,
            'close': 515.0,
            'volume': 45000000,
            'change_pct': 3.0,
            'indicators': json.dumps({'rsi': 65, 'macd': 2.5}),
            'momentum_score': 3.0
        },
        {
            'scan_date': test_date,
            'symbol': 'TSLA',
            'direction': 'loser',
            'rank': 1,
            'open': 250.0,
            'high': 252.0,
            'low': 240.0,
            'close': 242.0,
            'volume': 78000000,
            'change_pct': -3.2,
            'indicators': json.dumps({'rsi': 35, 'macd': -1.2}),
            'momentum_score': 3.2
        }
    ]
    
    # Archive test data
    success = history.archive_daily_scan(
        scan_date=test_date,
        movers=test_movers,
        market_regime={'regime': 'neutral', 'spy_change_pct': 0.5},
        scan_metadata={'total_scanned': 200, 'high_volume_count': 100, 'scan_duration': 5.2}
    )
    
    # Print summary
    history.print_history_summary()
    
    # Test queries
    print("\n📊 Test Queries:")
    print(f"Get NVDA history: {len(history.get_symbol_history('NVDA', '2025-11-01'))} records")
    print(f"Get date range: {history.get_date_range()}")
    
    stats = history.get_statistics_summary(test_date, test_date)
    print(f"Statistics: {stats}")
