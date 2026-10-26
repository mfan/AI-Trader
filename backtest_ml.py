#!/usr/bin/env python3
"""
Walk-forward backtest for the ML alpha strategy (Jansen methodology).

Runs: data load -> factor panel -> walk-forward predictions -> rank IC -> top-k backtest.
Usage: .venv/bin/python backtest_ml.py [--forward-days 5] [--top-k 5]
"""

import os
import sys
import argparse
import logging

import numpy as np
import pandas as pd

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tools.ml_data import load_universe, UNIVERSE, TRADEABLE_UNIVERSE
from tools.ml_alpha import build_dataset, walk_forward_predict, rank_ic, backtest_topk, performance_stats

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MLBacktest')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forward-days", type=int, default=5)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--train-days", type=int, default=504)
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--factor-set", default="mixed", choices=["mixed", "momentum", "reversal"])
    ap.add_argument("--strategy", default="ml", choices=["ml", "tsmom"],
                    help="ml = cross-sectional ML ranking; tsmom = ETF time-series momentum (book case study)")
    ap.add_argument("--lookback", type=int, default=126, help="tsmom momentum lookback days")
    ap.add_argument("--skip", type=int, default=21, help="tsmom skip days")
    ap.add_argument("--embargo-days", type=int, default=None, help="defaults to forward-days")
    ap.add_argument("--no-regime-filter", action="store_true")
    args = ap.parse_args()
    embargo = args.embargo_days if args.embargo_days is not None else args.forward_days

    logger.info("📦 Loading universe from cache...")
    universe = load_universe(UNIVERSE)
    logger.info(f"   {len(universe)} symbols loaded")

    if args.strategy == "tsmom":
        from tools.ml_alpha import backtest_etf_tsmom
        etf_universe = {s: universe[s] for s in ["XLK", "XLF", "XLE", "XLV", "SMH", "SOXX",
                                                  "ARKK", "TLT", "GLD", "IWM", "SPY", "QQQ"]
                        if s in universe}
        top_k = args.top_k if args.top_k != 5 else 3
        bt = backtest_etf_tsmom(etf_universe, top_k=top_k, lookback=args.lookback,
                                skip=args.skip, cost_bps=args.cost_bps)
        bt = bt.loc["2024-06-01":]  # warmup for 126d lookback
        stats = performance_stats(bt, "net")
        print(f"\n=== ETF Time-Series Momentum (top-3, {args.cost_bps}bps/side, net) ===")
        for k, v in stats.items():
            print(f"{k:22s} {v:,.4f}")
        spy_ret = universe["SPY"]["close"].pct_change().reindex(bt.index)
        bstats = performance_stats(pd.DataFrame({"net": spy_ret, "turnover": 0.0}), "net")
        print(f"\n=== SPY Buy & Hold (same period) ===")
        for k, v in bstats.items():
            print(f"{k:22s} {v:,.4f}")
        out_path = os.path.join(project_root, "data", "ml_backtest_tsmom.csv")
        bt.to_csv(out_path)
        print(f"\n💾 Daily results saved to {out_path}")
        return

    logger.info(f"🧮 Building factor panel (set={args.factor_set})...")
    X, y = build_dataset(universe, forward_days=args.forward_days, factor_set=args.factor_set)
    logger.info(f"   Panel: {X.shape[0]:,} rows x {X.shape[1]} factors")

    logger.info(f"🔁 Walk-forward prediction (train={args.train_days}d, refit 21d, embargo={embargo}d)...")
    preds = walk_forward_predict(X, y, train_days=args.train_days, embargo_days=embargo)
    logger.info(f"   Out-of-sample predictions: {preds.notna().sum():,} rows")

    # Predictive quality: rank IC
    ic = rank_ic(preds, y)
    print(f"\n=== Predictive Quality (out-of-sample) ===")
    print(f"Rank IC mean:  {ic.mean():.4f}")
    print(f"Rank IC std:   {ic.std():.4f}")
    print(f"ICIR (IC/std): {ic.mean() / ic.std():.4f}" if ic.std() > 0 else "ICIR: n/a")
    print(f"IC > 0 share:  {(ic > 0).mean():.1%}")

    # Backtest on tradeable universe only
    trade_universe = {s: universe[s] for s in TRADEABLE_UNIVERSE if s in universe}
    trade_universe["SPY"] = universe["SPY"]
    bt = backtest_topk(preds, trade_universe, top_k=args.top_k,
                       cost_bps=args.cost_bps, regime_filter=not args.no_regime_filter)
    bt = bt.loc[preds.dropna().index.get_level_values("date").min():]

    stats = performance_stats(bt, "net")
    print(f"\n=== Backtest (top-{args.top_k}, {args.cost_bps}bps/side, net) ===")
    for k, v in stats.items():
        print(f"{k:22s} {v:,.4f}")

    # Benchmark comparison
    spy_ret = universe["SPY"]["close"].pct_change().reindex(bt.index)
    bench = pd.DataFrame({"net": spy_ret, "turnover": 0.0})
    bstats = performance_stats(bench, "net")
    print(f"\n=== SPY Buy & Hold (same period) ===")
    for k, v in bstats.items():
        print(f"{k:22s} {v:,.4f}")

    out_path = os.path.join(project_root, "data", "ml_backtest_results.csv")
    bt.to_csv(out_path)
    print(f"\n💾 Daily results saved to {out_path}")


if __name__ == "__main__":
    main()
