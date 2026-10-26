"""
ML Strategy Data Infrastructure

Downloads and caches daily OHLCV bars for the strategy universe.
Follows the book's data hygiene rules:
- Point-in-time snapshots only (no restated/adjusted-on-the-fly surprises)
- Local cache so training and live inference use identical data pipelines
- Explicit trading-calendar alignment (drop symbols with missing days rather than ffill-forward hallucinated prices)
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger('MLData')

CACHE_DIR = os.path.join(project_root, "data", "ml_bars")
os.makedirs(CACHE_DIR, exist_ok=True)

# Liquid universe: mega/large-cap stocks + sector ETFs (regime features).
# Kept point-in-time honest: only currently-listed, currently-liquid names.
UNIVERSE = [
    # Mega cap tech
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
    # Tech
    "NFLX", "ADBE", "CRM", "ORCL", "CSCO", "INTC", "AMD", "QCOM",
    "AVGO", "TXN", "AMAT", "LRCX", "KLAC", "MU", "MRVL", "NOW",
    # Financials
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "AXP",
    "V", "MA", "PYPL", "SQ", "COIN",
    # Healthcare
    "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT",
    "GILD", "REGN", "VRTX", "BIIB", "MRNA",
    # Consumer
    "HD", "NKE", "SBUX", "MCD", "DIS", "BKNG",
    "COST", "WMT", "TGT", "LOW", "ABNB", "UBER", "DASH",
    # Energy
    "XOM", "CVX", "COP", "SLB", "OXY", "MPC", "PSX", "VLO",
    # Industrials
    "CAT", "DE", "BA", "UPS", "RTX", "LMT", "GE", "HON",
    # High momentum/volatility
    "PLTR", "SNOW", "CRWD", "NET", "DDOG", "ZS", "PANW", "SMCI",
    "MSTR", "RIOT", "MARA", "SHOP", "HOOD",
    # ETFs (market regime + tradeable)
    "SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV",
    "SMH", "SOXX", "ARKK", "TLT", "GLD",
]

TRADEABLE_UNIVERSE = [s for s in UNIVERSE if s not in ("SPY", "QQQ", "DIA")]  # SPY/QQQ/DIA reserved as regime features


def _cache_path(symbol: str) -> str:
    return os.path.join(CACHE_DIR, f"{symbol}.csv")


def download_daily_bars(symbols: List[str], start: str, end: Optional[str] = None,
                        force: bool = False) -> Dict[str, int]:
    """
    Download daily bars for symbols into the local CSV cache (incremental).

    Returns {symbol: row_count} for successfully cached symbols.
    """
    from tools.alpaca_data_feed import AlpacaDataFeed
    from alpaca.data.timeframe import TimeFrame

    feed = AlpacaDataFeed(feed='iex')
    end = end or datetime.now().strftime("%Y-%m-%d")
    counts = {}

    # Batch requests: Alpaca accepts multi-symbol requests
    BATCH = 50
    pending = []
    for sym in symbols:
        path = _cache_path(sym)
        if force or not os.path.exists(path):
            pending.append((sym, start))
        else:
            # Incremental: fetch from last cached date onward
            try:
                df = pd.read_csv(path, parse_dates=["timestamp"])
                if df.empty:
                    pending.append((sym, start))
                    continue
                last_ts = df["timestamp"].max()
                next_start = (last_ts + timedelta(days=1)).strftime("%Y-%m-%d")
                if next_start < end:
                    pending.append((sym, next_start))
                else:
                    counts[sym] = len(df)
            except Exception:
                pending.append((sym, start))

    for i in range(0, len(pending), BATCH):
        batch = pending[i:i + BATCH]
        # Group by start date (usually uniform)
        by_start: Dict[str, List[str]] = {}
        for sym, st in batch:
            by_start.setdefault(st, []).append(sym)

        for st, syms in by_start.items():
            try:
                start_dt = datetime.strptime(st, "%Y-%m-%d")
                end_dt = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
                bars = feed.get_bars(syms, start_dt, end_dt, TimeFrame.Day)
                today = datetime.now().date()
                for sym in syms:
                    rows = bars.get(sym, [])
                    if not rows:
                        logger.warning(f"   ⚠️ No bars for {sym}")
                        continue
                    df_new = pd.DataFrame(rows)
                    df_new["timestamp"] = pd.to_datetime(df_new["timestamp"])
                    # Never cache today's (incomplete intraday) bar — signals
                    # must be computed from completed daily bars only
                    df_new = df_new[df_new["timestamp"].dt.date < today]
                    if df_new.empty:
                        continue
                    path = _cache_path(sym)
                    if os.path.exists(path):
                        df_old = pd.read_csv(path, parse_dates=["timestamp"])
                        df_new = pd.concat([df_old, df_new]).drop_duplicates(subset="timestamp").sort_values("timestamp")
                    df_new.to_csv(path, index=False)
                    counts[sym] = len(df_new)
                time.sleep(0.5)  # be kind to the rate limiter
            except Exception as e:
                logger.error(f"   ❌ Batch download failed for {syms[:5]}...: {e}")

    logger.info(f"✅ Cached daily bars for {len(counts)}/{len(symbols)} symbols")
    return counts


def load_universe(symbols: Optional[List[str]] = None, min_history_days: int = 260) -> Dict[str, pd.DataFrame]:
    """
    Load cached daily bars into DataFrames indexed by timestamp.
    Symbols with insufficient history are dropped (no padding/ffill hallucination).
    """
    symbols = symbols or UNIVERSE
    out = {}
    for sym in symbols:
        path = _cache_path(sym)
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp").sort_index()
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            if len(df) >= min_history_days:
                out[sym] = df
        except Exception as e:
            logger.warning(f"⚠️ Could not load {sym}: {e}")
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    counts = download_daily_bars(UNIVERSE, start="2023-01-01")
    print(f"Downloaded: {len(counts)} symbols")
    for sym, n in sorted(counts.items()):
        print(f"  {sym}: {n} bars")
