"""
Momentum Cache - SQLite Database for High-Performance Stock Data

Caches momentum scanner results to accelerate intraday trading decisions.
Stores: Daily movers, technical indicators, volume data, momentum scores.

Benefits:
- Fast queries during trading hours (no repeated API calls)
- Historical momentum tracking
- Pre-calculated TA indicators
- Automatic cache expiration
"""

import sqlite3
import json
import logging
from datetime import datetime, time as dt_time, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import threading

logger = logging.getLogger(__name__)

# Database location
DEFAULT_DB_PATH = "data/momentum_cache.db"

# Cache expiration (market close)
MARKET_CLOSE_TIME = dt_time(16, 0)  # 4:00 PM


class MomentumCache:
    """
    SQLite cache for momentum scanner results.
    
    Features:
    - Fast indexed queries
    - Automatic cache expiration
    - Thread-safe operations
    - Historical tracking
    - JSON storage for complex data (TA indicators)
    """
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """
        Initialize momentum cache.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        
        # Create database directory if needed
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        logger.info(f"✅ Momentum cache initialized: {db_path}")
    
    def _init_database(self):
        """Create database schema if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Daily movers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_movers (
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
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Unique constraint
                    UNIQUE(scan_date, symbol)
                )
            """)
            
            # Indices for fast queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scan_date 
                ON daily_movers(scan_date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol 
                ON daily_movers(symbol)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_direction_rank 
                ON daily_movers(direction, rank)
            """)
            
            # Market regime tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_regime (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_date TEXT NOT NULL UNIQUE,
                    regime TEXT NOT NULL,  -- 'bullish', 'bearish', 'neutral'
                    spy_change_pct REAL,
                    qqq_change_pct REAL,
                    market_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Scan metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_date TEXT NOT NULL UNIQUE,
                    total_scanned INTEGER,
                    high_volume_count INTEGER,
                    gainers_count INTEGER,
                    losers_count INTEGER,
                    scan_duration_seconds REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("✅ Database schema initialized")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def cache_momentum_stocks(
        self,
        scan_date: str,
        gainers: List[Dict],
        losers: List[Dict],
        market_regime: str = 'neutral',
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Cache momentum scanner results.
        
        Args:
            scan_date: Date of scan (YYYY-MM-DD)
            gainers: List of gainer stocks with data
            losers: List of loser stocks with data
            market_regime: Overall market direction
            metadata: Additional scan metadata
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Clear existing data for this date
                    cursor.execute("DELETE FROM daily_movers WHERE scan_date = ?", (scan_date,))
                    
                    # Insert gainers
                    for rank, stock in enumerate(gainers, 1):
                        self._insert_stock(cursor, scan_date, stock, 'gainer', rank)
                    
                    # Insert losers
                    for rank, stock in enumerate(losers, 1):
                        self._insert_stock(cursor, scan_date, stock, 'loser', rank)
                    
                    # Cache market regime
                    spy_change = self._find_stock_change(gainers + losers, 'SPY')
                    qqq_change = self._find_stock_change(gainers + losers, 'QQQ')
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO market_regime 
                        (scan_date, regime, spy_change_pct, qqq_change_pct, market_score)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                    scan_date,
                    market_regime,
                    spy_change,
                    qqq_change,
                    ((spy_change or 0) + (qqq_change or 0)) / 2
                ))                    # Cache metadata
                    if metadata:
                        cursor.execute("""
                            INSERT OR REPLACE INTO scan_metadata
                            (scan_date, total_scanned, high_volume_count, 
                             gainers_count, losers_count, scan_duration_seconds)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            scan_date,
                            metadata.get('total_scanned', 0),
                            metadata.get('high_volume_count', 0),
                            len(gainers),
                            len(losers),
                            metadata.get('scan_duration', 0)
                        ))
                    
                    conn.commit()
                    
                logger.info(f"✅ Cached {len(gainers)} gainers + {len(losers)} losers for {scan_date}")
                return True
                
            except Exception as e:
                logger.error(f"Error caching momentum stocks: {e}", exc_info=True)
                return False
    
    def _insert_stock(
        self,
        cursor: sqlite3.Cursor,
        scan_date: str,
        stock: Dict,
        direction: str,
        rank: int
    ):
        """Insert a single stock into cache."""
        # Extract indicators and serialize to JSON
        indicators = {
            k: v for k, v in stock.items()
            if k not in ['symbol', 'open', 'high', 'low', 'close', 'volume', 'change_pct']
        }
        
        cursor.execute("""
            INSERT OR REPLACE INTO daily_movers
            (scan_date, symbol, direction, rank, open, high, low, close, 
             volume, change_pct, indicators, momentum_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            scan_date,
            stock['symbol'],
            direction,
            rank,
            stock.get('open'),
            stock.get('high'),
            stock.get('low'),
            stock.get('close'),
            stock.get('volume'),
            stock.get('change_pct'),
            json.dumps(indicators),
            abs(stock.get('change_pct', 0))  # Momentum score
        ))
    
    def _find_stock_change(self, stocks: List[Dict], symbol: str) -> Optional[float]:
        """Find price change % for a specific symbol."""
        for stock in stocks:
            if stock.get('symbol') == symbol:
                return stock.get('change_pct')
        return None
    
    def get_cached_momentum_stocks(
        self,
        scan_date: Optional[str] = None,
        direction: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve cached momentum stocks.
        
        Args:
            scan_date: Date to retrieve (defaults to latest)
            direction: Filter by 'gainer' or 'loser' (None = both)
            limit: Maximum stocks to return
            
        Returns:
            List of stock dictionaries with all cached data
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Build query
                    query = "SELECT * FROM daily_movers"
                    params = []
                    
                    if scan_date:
                        query += " WHERE scan_date = ?"
                        params.append(scan_date)
                    else:
                        # Get latest scan date
                        cursor.execute("SELECT MAX(scan_date) FROM daily_movers")
                        latest = cursor.fetchone()[0]
                        if latest:
                            query += " WHERE scan_date = ?"
                            params.append(latest)
                    
                    if direction:
                        query += " AND direction = ?" if "WHERE" in query else " WHERE direction = ?"
                        params.append(direction)
                    
                    query += " ORDER BY rank"
                    
                    if limit:
                        query += " LIMIT ?"
                        params.append(limit)
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    # Convert to dictionaries
                    stocks = []
                    for row in rows:
                        stock = dict(row)
                        
                        # Parse indicators JSON
                        if stock.get('indicators'):
                            indicators = json.loads(stock['indicators'])
                            stock.update(indicators)
                        
                        del stock['indicators']  # Remove JSON field
                        stocks.append(stock)
                    
                    return stocks
                    
            except Exception as e:
                logger.error(f"Error retrieving cached stocks: {e}", exc_info=True)
                return []
    
    def get_momentum_watchlist(
        self,
        scan_date: Optional[str] = None,
        symbols_only: bool = True
    ) -> List:
        """
        Get momentum watchlist (all gainers + losers).
        
        Args:
            scan_date: Date to retrieve (defaults to latest)
            symbols_only: Return only symbols (True) or full data (False)
            
        Returns:
            List of symbols or full stock dictionaries
        """
        stocks = self.get_cached_momentum_stocks(scan_date)
        
        if symbols_only:
            return [stock['symbol'] for stock in stocks]
        else:
            return stocks
    
    def get_market_regime(self, scan_date: Optional[str] = None) -> Dict:
        """
        Get cached market regime.
        
        Args:
            scan_date: Date to retrieve (defaults to latest)
            
        Returns:
            Dictionary with regime info
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    if scan_date:
                        cursor.execute(
                            "SELECT * FROM market_regime WHERE scan_date = ?",
                            (scan_date,)
                        )
                    else:
                        cursor.execute(
                            "SELECT * FROM market_regime ORDER BY scan_date DESC LIMIT 1"
                        )
                    
                    row = cursor.fetchone()
                    
                    if row:
                        return dict(row)
                    else:
                        return {'regime': 'neutral', 'spy_change_pct': 0, 'qqq_change_pct': 0}
                        
            except Exception as e:
                logger.error(f"Error retrieving market regime: {e}", exc_info=True)
                return {'regime': 'neutral'}
    
    def is_cache_valid(self, scan_date: Optional[str] = None) -> bool:
        """
        Check if cache is valid for trading day.
        
        Cache expires after market close (4:00 PM ET).
        
        Args:
            scan_date: Date to check (defaults to today)
            
        Returns:
            True if cache is valid, False if expired
        """
        if scan_date is None:
            scan_date = datetime.now().strftime('%Y-%m-%d')
        
        # Check if data exists
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT COUNT(*) FROM daily_movers WHERE scan_date = ?",
                        (scan_date,)
                    )
                    count = cursor.fetchone()[0]
                    
                    if count == 0:
                        return False
                    
                    # Check if market has closed (cache should be refreshed)
                    now = datetime.now().time()
                    if now > MARKET_CLOSE_TIME:
                        # After market close, cache for "today" is stale
                        today = datetime.now().strftime('%Y-%m-%d')
                        if scan_date == today:
                            return False
                    
                    return True
                    
            except Exception as e:
                logger.error(f"Error checking cache validity: {e}", exc_info=True)
                return False
    
    def get_scan_metadata(self, scan_date: Optional[str] = None) -> Dict:
        """Get metadata about a scan."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    if scan_date:
                        cursor.execute(
                            "SELECT * FROM scan_metadata WHERE scan_date = ?",
                            (scan_date,)
                        )
                    else:
                        cursor.execute(
                            "SELECT * FROM scan_metadata ORDER BY scan_date DESC LIMIT 1"
                        )
                    
                    row = cursor.fetchone()
                    return dict(row) if row else {}
                    
            except Exception as e:
                logger.error(f"Error retrieving scan metadata: {e}", exc_info=True)
                return {}
    
    def cleanup_old_scans(self, days_to_keep: int = 30):
        """
        Remove old scan data to keep database size manageable.
        
        Args:
            days_to_keep: Number of days of history to preserve
        """
        with self._lock:
            try:
                cutoff_date = (
                    datetime.now() - timedelta(days=days_to_keep)
                ).strftime('%Y-%m-%d')
                
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("DELETE FROM daily_movers WHERE scan_date < ?", (cutoff_date,))
                    cursor.execute("DELETE FROM market_regime WHERE scan_date < ?", (cutoff_date,))
                    cursor.execute("DELETE FROM scan_metadata WHERE scan_date < ?", (cutoff_date,))
                    
                    deleted = cursor.rowcount
                    conn.commit()
                    
                    logger.info(f"✅ Cleaned up {deleted} old records (kept {days_to_keep} days)")
                    
            except Exception as e:
                logger.error(f"Error cleaning up old scans: {e}", exc_info=True)
    
    def print_cache_summary(self, scan_date: Optional[str] = None):
        """Print summary of cached data."""
        stocks = self.get_cached_momentum_stocks(scan_date)
        regime = self.get_market_regime(scan_date)
        metadata = self.get_scan_metadata(scan_date)
        
        if not stocks:
            print("No cached data available.")
            return
        
        date = stocks[0]['scan_date']
        gainers = [s for s in stocks if s['direction'] == 'gainer']
        losers = [s for s in stocks if s['direction'] == 'loser']
        
        print(f"\n{'='*80}")
        print(f"CACHED MOMENTUM DATA - {date}")
        print(f"{'='*80}")
        print(f"Market Regime: {regime.get('regime', 'unknown').upper()}")
        spy_change = regime.get('spy_change_pct') or 0
        qqq_change = regime.get('qqq_change_pct') or 0
        print(f"SPY: {spy_change:+.2f}%  QQQ: {qqq_change:+.2f}%")
        print(f"\n📈 Gainers: {len(gainers)} stocks")
        print(f"📉 Losers: {len(losers)} stocks")
        print(f"📊 Total Watchlist: {len(stocks)} stocks")
        
        if metadata:
            print(f"\n🔍 Scan Stats:")
            print(f"   Total Scanned: {metadata.get('total_scanned', 0):,}")
            print(f"   High Volume: {metadata.get('high_volume_count', 0):,}")
            print(f"   Duration: {metadata.get('scan_duration_seconds', 0):.2f}s")
        
        print(f"{'='*80}\n")


# Convenience functions
def get_momentum_watchlist(scan_date: Optional[str] = None) -> List[str]:
    """Get momentum watchlist from cache (convenience function)."""
    cache = MomentumCache()
    return cache.get_momentum_watchlist(scan_date)


def get_market_regime(scan_date: Optional[str] = None) -> str:
    """Get market regime from cache (convenience function)."""
    cache = MomentumCache()
    regime_data = cache.get_market_regime(scan_date)
    return regime_data.get('regime', 'neutral')


if __name__ == "__main__":
    # Test the cache
    logging.basicConfig(level=logging.INFO)
    
    # Create cache instance
    cache = MomentumCache("data/test_momentum_cache.db")
    
    # Test data
    test_gainers = [
        {
            'symbol': 'NVDA',
            'open': 500.0,
            'high': 520.0,
            'low': 498.0,
            'close': 515.0,
            'volume': 45000000,
            'change_pct': 3.0,
            'rsi': 65,
            'macd': 2.5
        },
        {
            'symbol': 'TSLA',
            'open': 250.0,
            'high': 258.0,
            'low': 249.0,
            'close': 255.0,
            'volume': 78000000,
            'change_pct': 2.0,
            'rsi': 62,
            'macd': 1.8
        }
    ]
    
    test_losers = [
        {
            'symbol': 'INTC',
            'open': 30.0,
            'high': 30.5,
            'low': 28.5,
            'close': 29.0,
            'volume': 35000000,
            'change_pct': -3.33,
            'rsi': 35,
            'macd': -1.2
        }
    ]
    
    # Cache test data
    scan_date = datetime.now().strftime('%Y-%m-%d')
    cache.cache_momentum_stocks(
        scan_date,
        test_gainers,
        test_losers,
        'bullish',
        {'total_scanned': 200, 'high_volume_count': 100, 'scan_duration': 5.2}
    )
    
    # Retrieve and print
    cache.print_cache_summary()
    
    print(f"✅ Watchlist: {cache.get_momentum_watchlist()}")
    print(f"✅ Market Regime: {cache.get_market_regime()['regime']}")
