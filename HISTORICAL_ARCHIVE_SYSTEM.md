# Historical Momentum Archive System

## Overview

**Two-Database Architecture** for optimal performance and data management:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DAILY MOMENTUM SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────┐      ┌──────────────────────────┐  │
│  │  momentum_cache.db     │      │  momentum_history.db     │  │
│  │  (Daily Trading)       │─────▶│  (Permanent Archive)     │  │
│  │                        │ Auto │                          │  │
│  │  • Latest scan only    │ Copy │  • All historical scans  │  │
│  │  • Fast queries        │      │  • Backtesting data      │  │
│  │  • 30-day cleanup      │      │  • Never deleted         │  │
│  │  • Optimized for speed │      │  • Time-series queries   │  │
│  └────────────────────────┘      └──────────────────────────┘  │
│            ▲                                  │                 │
│            │                                  │                 │
│            │ Read                       Read  │                 │
│            │                                  ▼                 │
│  ┌─────────┴──────────┐            ┌──────────────────────┐   │
│  │  Active Trader     │            │  Backtesting Engine  │   │
│  │  (Live Trading)    │            │  (Analysis/Research) │   │
│  └────────────────────┘            └──────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Comparison

| Feature | momentum_cache.db | momentum_history.db |
|---------|-------------------|---------------------|
| **Purpose** | Live trading data | Historical archive |
| **Data Retention** | 30 days | Permanent |
| **Cleanup** | Auto-delete >30 days | Never deleted |
| **Optimization** | Speed (indexed) | Time-series queries |
| **Size** | Small (~100KB-3MB) | Growing (100KB/day) |
| **Updates** | Daily flush & replace | Daily append (UPSERT) |
| **Use Case** | Intraday trading | Backtesting, analysis |

---

## Daily Workflow

### 9:00 AM - Pre-Market Scan

```
1. Scan Previous Day
   └─▶ momentum_scanner.py
       └─▶ Identifies top 100 movers (50 gainers + 50 losers)

2. Cache for Trading
   └─▶ momentum_cache.db
       └─▶ DELETE old data for scan_date
       └─▶ INSERT 100 fresh records
       └─▶ Used for live trading all day

3. Archive for History ✨ NEW
   └─▶ momentum_history.db
       └─▶ UPSERT (INSERT OR REPLACE) records
       └─▶ Permanent storage, never deleted
       └─▶ Used for backtesting/analysis

4. Cleanup Cache
   └─▶ momentum_cache.db
       └─▶ DELETE scans older than 30 days
       └─▶ Keeps database small and fast
```

**Code Flow** (`active_trader.py`):

```python
# Step 1 & 2: Scan and cache
success = cache.cache_momentum_stocks(
    scan_date=movers.get('scan_date'),
    gainers=movers.get('gainers', []),
    losers=movers.get('losers', []),
    market_regime=market_regime,
    metadata={...}
)

# Step 3: Archive to history ✨
from tools.momentum_history import archive_from_cache
archive_from_cache(cache_path, history_path, scan_date)

# Step 4: Cleanup old cache
cache.cleanup_old_scans(days_to_keep=30)
```

---

## Historical Database Schema

### Table: `historical_movers`

Stores individual stock momentum records.

```sql
CREATE TABLE historical_movers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date TEXT NOT NULL,           -- Market date (YYYY-MM-DD)
    symbol TEXT NOT NULL,              -- Stock ticker
    direction TEXT NOT NULL,           -- 'gainer' or 'loser'
    rank INTEGER NOT NULL,             -- 1-50 ranking
    
    -- Price Data
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    change_pct REAL,                   -- % change vs previous day
    
    -- Technical Indicators (JSON)
    indicators TEXT,                   -- RSI, MACD, etc.
    momentum_score REAL,               -- Absolute change %
    
    -- Archive Metadata
    archived_at TIMESTAMP,             -- When archived
    updated_at TIMESTAMP,              -- Last update
    
    UNIQUE(scan_date, symbol)          -- No duplicates
);
```

**Indexes** (for fast queries):
- `scan_date` - Query by date
- `symbol` - Query by stock
- `symbol, scan_date` - Symbol history over time
- `direction, rank` - Top gainers/losers

### Table: `historical_regime`

Stores daily market regime data.

```sql
CREATE TABLE historical_regime (
    id INTEGER PRIMARY KEY,
    scan_date TEXT UNIQUE,
    regime TEXT,                       -- 'bullish', 'bearish', 'neutral'
    spy_change_pct REAL,               -- SPY % change
    qqq_change_pct REAL,               -- QQQ % change
    market_score REAL,                 -- Overall market score
    archived_at TIMESTAMP
);
```

### Table: `historical_stats`

Stores aggregated daily statistics.

```sql
CREATE TABLE historical_stats (
    id INTEGER PRIMARY KEY,
    scan_date TEXT UNIQUE,
    total_scanned INTEGER,             -- Total stocks scanned
    high_volume_count INTEGER,         -- Stocks meeting volume criteria
    gainers_count INTEGER,             -- Number of gainers
    losers_count INTEGER,              -- Number of losers
    avg_gainer_change REAL,            -- Average gainer %
    avg_loser_change REAL,             -- Average loser %
    max_gainer_change REAL,            -- Best gainer %
    max_loser_change REAL,             -- Worst loser %
    scan_duration_seconds REAL,        -- Scan performance
    archived_at TIMESTAMP
);
```

---

## UPSERT Behavior

**Key Feature**: Uses `INSERT OR REPLACE` for idempotent archiving.

```python
cursor.execute("""
    INSERT OR REPLACE INTO historical_movers
    (scan_date, symbol, direction, rank, open, high, low, close,
     volume, change_pct, indicators, momentum_score, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (...))
```

**Benefits**:
- ✅ **Idempotent**: Can re-run scan for same date without errors
- ✅ **Updates**: Overwrites existing data if re-archived
- ✅ **No Duplicates**: UNIQUE constraint ensures one record per (scan_date, symbol)
- ✅ **Safe**: Won't fail if data already exists

**Example Scenarios**:

```
Day 1 (Nov 10):
  Archive 100 stocks for 2025-11-10
  Result: 100 new records

Day 2 (Nov 11):
  Archive 100 stocks for 2025-11-11
  Result: 200 total records (100 + 100)

Re-run Nov 10 scan:
  Archive 100 stocks for 2025-11-10 again
  Result: Still 200 records (updates existing Nov 10 data)
```

---

## Query Examples

### 1. Command Line Tool

```bash
# Show database summary
/home/mfan/work/bin/python query_history.py --summary

# Query specific date
/home/mfan/work/bin/python query_history.py --date 2025-11-10

# Query date range
/home/mfan/work/bin/python query_history.py --range 2025-11-01 2025-11-30

# Query specific symbol
/home/mfan/work/bin/python query_history.py --symbol NVDA --days 30

# Show statistics
/home/mfan/work/bin/python query_history.py --stats 2025-11-10
/home/mfan/work/bin/python query_history.py --stats 2025-11-01 2025-11-30
```

### 2. Python API

```python
from tools.momentum_history import MomentumHistory

# Initialize
history = MomentumHistory('data/agent_data/xai-grok-4-latest/momentum_history.db')

# Get movers for date range
movers = history.get_historical_movers(
    start_date='2025-11-01',
    end_date='2025-11-30',
    direction='gainer'  # Optional filter
)

# Get symbol history
nvda_history = history.get_symbol_history(
    symbol='NVDA',
    start_date='2025-10-01',
    end_date='2025-11-30'
)

# Get date range info
date_info = history.get_date_range()
# Returns: {'earliest': '2025-11-01', 'latest': '2025-11-30', 'total_days': 30, 'total_records': 3000}

# Get statistics
stats = history.get_statistics_summary(
    start_date='2025-11-01',
    end_date='2025-11-30'
)
# Returns: avg gainer/loser %, best/worst moves, etc.
```

### 3. Direct SQL Queries

```sql
-- Get top gainers for a month
SELECT symbol, scan_date, change_pct, volume
FROM historical_movers
WHERE scan_date BETWEEN '2025-11-01' AND '2025-11-30'
  AND direction = 'gainer'
ORDER BY change_pct DESC
LIMIT 20;

-- Count symbol appearances
SELECT symbol, COUNT(*) as appearances, AVG(change_pct) as avg_change
FROM historical_movers
WHERE scan_date >= '2025-11-01'
GROUP BY symbol
ORDER BY appearances DESC
LIMIT 20;

-- Best performing days
SELECT scan_date, 
       AVG(CASE WHEN direction='gainer' THEN change_pct END) as avg_gainer,
       MAX(CASE WHEN direction='gainer' THEN change_pct END) as max_gainer
FROM historical_movers
GROUP BY scan_date
ORDER BY avg_gainer DESC;

-- Symbol momentum pattern
SELECT scan_date, direction, change_pct, volume
FROM historical_movers
WHERE symbol = 'NVDA'
ORDER BY scan_date DESC;
```

---

## Backtesting Use Cases

### 1. Strategy Validation

```python
# Test: "Buy top 10 gainers, hold 3 days"
for date in backtest_dates:
    gainers = history.get_historical_movers(date, direction='gainer')
    top_10 = gainers[:10]
    
    # Simulate trades, measure 3-day return
    # ...
```

### 2. Pattern Recognition

```python
# Find stocks that appear frequently as gainers
symbol_counts = {}
for date in date_range:
    movers = history.get_historical_movers(date, direction='gainer')
    for stock in movers:
        symbol_counts[stock['symbol']] = symbol_counts.get(stock['symbol'], 0) + 1

# Top momentum stocks
frequent_winners = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:20]
```

### 3. Market Regime Analysis

```python
# Analyze market regime correlation with strategy performance
for date in date_range:
    movers = history.get_historical_movers(date)
    regime = get_regime_for_date(date)
    
    # Calculate avg returns by regime
    # ...
```

### 4. Volatility Patterns

```python
# Identify high-volatility periods
stats = []
for date in date_range:
    day_stats = history.get_statistics_summary(date, date)
    stats.append({
        'date': date,
        'volatility': day_stats['max_gainer_change'] - day_stats['worst_loser_change']
    })

# Find most volatile days
high_vol_days = sorted(stats, key=lambda x: x['volatility'], reverse=True)[:10]
```

---

## Maintenance

### Check Archive Status

```bash
# Database summary
/home/mfan/work/bin/python query_history.py --summary

# Check database size
ls -lh data/agent_data/xai-grok-4-latest/momentum_history.db

# Expected: ~100KB per day of data
# 1 year = ~36MB
# 5 years = ~180MB
```

### Manual Archive

```python
from tools.momentum_history import archive_from_cache

# Archive specific date
cache_path = 'data/agent_data/xai-grok-4-latest/momentum_cache.db'
history_path = 'data/agent_data/xai-grok-4-latest/momentum_history.db'

success = archive_from_cache(cache_path, history_path, '2025-11-10')
```

### Export Data

```bash
# Export to CSV for external analysis
sqlite3 momentum_history.db <<EOF
.headers on
.mode csv
.output movers_nov_2025.csv
SELECT * FROM historical_movers 
WHERE scan_date BETWEEN '2025-11-01' AND '2025-11-30';
.quit
