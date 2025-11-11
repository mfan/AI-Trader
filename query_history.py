#!/usr/bin/env python3
"""
Historical Momentum Query Tool

Query and analyze historical momentum scan data for backtesting and research.
"""

import sys
import argparse
from datetime import datetime, timedelta
sys.path.insert(0, '/home/mfan/work/aitrader')

from tools.momentum_history import MomentumHistory


def query_date_range(history: MomentumHistory, start: str, end: str = None):
    """Query movers for a date range."""
    print(f"\n{'='*80}")
    print(f"HISTORICAL MOVERS: {start}" + (f" to {end}" if end else ""))
    print(f"{'='*80}")
    
    movers = history.get_historical_movers(start, end)
    
    if not movers:
        print("No data found for this date range.")
        return
    
    gainers = [m for m in movers if m['direction'] == 'gainer']
    losers = [m for m in movers if m['direction'] == 'loser']
    
    print(f"\n📈 GAINERS ({len(gainers)}):")
    for m in gainers[:10]:
        print(f"   {m['rank']:2d}. {m['symbol']:6s} {m['change_pct']:+7.2f}%  Vol: {m['volume']:,}")
    
    print(f"\n📉 LOSERS ({len(losers)}):")
    for m in losers[:10]:
        print(f"   {m['rank']:2d}. {m['symbol']:6s} {m['change_pct']:+7.2f}%  Vol: {m['volume']:,}")
    
    print(f"\n{'='*80}\n")


def query_symbol(history: MomentumHistory, symbol: str, days: int = 30):
    """Query historical data for a specific symbol."""
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    data = history.get_symbol_history(symbol, start, end)
    
    print(f"\n{'='*80}")
    print(f"SYMBOL HISTORY: {symbol} (Last {days} days)")
    print(f"{'='*80}")
    
    if not data:
        print(f"No historical data found for {symbol}")
        return
    
    print(f"\nAppeared in momentum scans: {len(data)} times")
    print(f"\nRecent appearances:")
    print(f"{'Date':<12} {'Direction':<8} {'Change %':<10} {'Volume':<15}")
    print("-" * 80)
    
    for record in data[:20]:
        print(f"{record['scan_date']:<12} {record['direction']:<8} {record['change_pct']:+7.2f}%   {record['volume']:>12,}")
    
    print(f"\n{'='*80}\n")


def show_statistics(history: MomentumHistory, start: str, end: str = None):
    """Show aggregated statistics."""
    if end is None:
        end = start
    
    stats = history.get_statistics_summary(start, end)
    
    print(f"\n{'='*80}")
    print(f"STATISTICS: {start}" + (f" to {end}" if start != end else ""))
    print(f"{'='*80}")
    
    if stats.get('error'):
        print(f"Error: {stats['error']}")
        return
    
    print(f"\n📊 Summary:")
    print(f"   Trading Days:          {stats['days']}")
    print(f"   Avg Gainers per Day:   {stats['avg_gainers_per_day']:.1f}")
    print(f"   Avg Losers per Day:    {stats['avg_losers_per_day']:.1f}")
    print(f"\n📈 Gainer Statistics:")
    print(f"   Avg Daily Move:        {stats['avg_daily_gainer_pct']:+.2f}%")
    print(f"   Best Single Move:      {stats['best_gainer_pct']:+.2f}%")
    print(f"\n📉 Loser Statistics:")
    print(f"   Avg Daily Move:        {stats['avg_daily_loser_pct']:+.2f}%")
    print(f"   Worst Single Move:     {stats['worst_loser_pct']:+.2f}%")
    
    print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='Query historical momentum data')
    parser.add_argument('--db', default='data/agent_data/xai-grok-4-latest/momentum_history.db',
                       help='Path to history database')
    parser.add_argument('--summary', action='store_true',
                       help='Show database summary')
    parser.add_argument('--date', type=str,
                       help='Query specific date (YYYY-MM-DD)')
    parser.add_argument('--range', type=str, nargs=2, metavar=('START', 'END'),
                       help='Query date range (START END)')
    parser.add_argument('--symbol', type=str,
                       help='Query specific symbol')
    parser.add_argument('--days', type=int, default=30,
                       help='Days to look back for symbol query (default: 30)')
    parser.add_argument('--stats', type=str, nargs='*', metavar='DATE',
                       help='Show statistics for date or date range')
    
    args = parser.parse_args()
    
    # Initialize history
    history = MomentumHistory(args.db)
    
    # Show summary
    if args.summary or (not args.date and not args.range and not args.symbol and not args.stats):
        history.print_history_summary()
    
    # Query by date
    if args.date:
        query_date_range(history, args.date)
    
    # Query by date range
    if args.range:
        query_date_range(history, args.range[0], args.range[1])
    
    # Query by symbol
    if args.symbol:
        query_symbol(history, args.symbol.upper(), args.days)
    
    # Show statistics
    if args.stats is not None:
        if len(args.stats) == 0:
            # Get latest date
            date_info = history.get_date_range()
            if date_info.get('latest'):
                show_statistics(history, date_info['latest'])
        elif len(args.stats) == 1:
            show_statistics(history, args.stats[0])
        elif len(args.stats) == 2:
            show_statistics(history, args.stats[0], args.stats[1])


if __name__ == '__main__':
    main()
