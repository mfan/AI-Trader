"""
ML Alpha Engine — factor library, walk-forward model, and backtest.

Methodology distilled from Stefan Jansen, "Machine Learning for Trading":
- Cross-sectional alpha factors from price/volume (momentum, reversal, volatility, volume, TA)
- Forward-return target, cross-sectionally rank-normalized per date
- Walk-forward (rolling) train/predict — never train on the future (no lookahead)
- Information Coefficient (Spearman rank IC) as the primary predictive metric
- Simple cost-aware daily backtest of a top-k portfolio
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger('MLAlpha')

MODEL_DIR = os.path.join(project_root, "data", "ml_models")
os.makedirs(MODEL_DIR, exist_ok=True)

# ─── Factor definitions ───
# Groups mirror the book's factor taxonomy. Factor SETS are competing economic
# hypotheses, each tested separately (mixed sets let contradictory signals cancel).
ALL_FACTORS = [
    "mom_5", "mom_21", "mom_63", "mom_126",      # raw trailing momentum
    "mom_126_skip21",                             # classic 12-1 style: t-126..t-21 (skip recent)
    "mom_63_skip5",                               # t-63..t-5
    "rev_1", "rev_5",                             # short-term reversal
    "rsi_14",                                     # oscillator
    "ema_dist",                                   # trend distance from EMA21
    "macd_hist",                                  # MACD histogram
    "vol_21",                                     # realized volatility (risk)
    "atr_pct",                                    # ATR / close (risk)
    "vol_ratio",                                  # relative volume
    "range_pos",                                  # position within 21d range
    "spy_mom_21", "spy_rsi_14", "spy_vol_21",     # market regime context
]

_REGIME = ["spy_mom_21", "spy_rsi_14", "spy_vol_21"]
_RISK = ["vol_21", "atr_pct", "vol_ratio"]

FACTOR_SETS = {
    # Hypothesis A: medium-horizon momentum/trend persists (Jegadeesh-Titman style,
    # most-recent period skipped as the book prescribes)
    "momentum": ["mom_21", "mom_63_skip5", "mom_126_skip21", "ema_dist", "macd_hist",
                 "rsi_14", "range_pos"] + _RISK + _REGIME,
    # Hypothesis B: short-term reversal — recent losers bounce (liquidity provision)
    "reversal": ["rev_1", "rev_5", "rsi_14", "range_pos"] + _RISK + _REGIME,
    # Hypothesis C: combined (baseline; risks internal cancellation)
    "mixed": [f for f in ALL_FACTORS],
}

FACTOR_NAMES = FACTOR_SETS["mixed"]  # backward compat


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def compute_factors(df: pd.DataFrame, spy: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Compute the factor panel for one symbol from its daily OHLCV bars.
    All factors use only trailing data (shifted where needed) — no lookahead.
    """
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    ret = c.pct_change()

    f = pd.DataFrame(index=df.index)
    f["mom_5"] = c.pct_change(5)
    f["mom_21"] = c.pct_change(21)
    f["mom_63"] = c.pct_change(63)
    f["mom_126"] = c.pct_change(126)
    # Skip-period momentum (book convention: exclude the most recent days to
    # avoid contamination by short-term reversal)
    f["mom_126_skip21"] = c.shift(21) / c.shift(126) - 1
    f["mom_63_skip5"] = c.shift(5) / c.shift(63) - 1
    f["rev_1"] = -ret                                   # reversal: yesterday's loser
    f["rev_5"] = -c.pct_change(5)
    f["rsi_14"] = _rsi(c, 14) / 100.0                   # scaled to ~[0,1]
    ema21 = c.ewm(span=21, adjust=False).mean()
    f["ema_dist"] = c / ema21 - 1
    ema12, ema26 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    f["macd_hist"] = (macd - macd.ewm(span=9, adjust=False).mean()) / c
    f["vol_21"] = ret.rolling(21).std()
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    f["atr_pct"] = tr.rolling(14).mean() / c
    f["vol_ratio"] = v / v.rolling(21).mean()
    hi21, lo21 = h.rolling(21).max(), l.rolling(21).min()
    f["range_pos"] = (c - lo21) / (hi21 - lo21).replace(0, np.nan)

    if spy is not None:
        sc = spy["close"].reindex(df.index).ffill()
        sret = sc.pct_change()
        f["spy_mom_21"] = sc.pct_change(21)
        f["spy_rsi_14"] = _rsi(sc, 14) / 100.0
        f["spy_vol_21"] = sret.rolling(21).std()
    return f


def build_dataset(universe: Dict[str, pd.DataFrame], forward_days: int = 5,
                  factor_set: str = "mixed") -> Tuple[pd.DataFrame, pd.Series]:
    """
    Assemble the full (date, symbol) panel: factors + forward returns.

    Target: forward N-day return, cross-sectionally rank-normalized per date
    (the book's approach for learning relative outperformance).
    """
    spy = universe.get("SPY")
    cols = FACTOR_SETS.get(factor_set, FACTOR_SETS["mixed"])
    frames = []
    for sym, df in universe.items():
        if sym == "SPY":
            continue
        f = compute_factors(df, spy)
        f["fwd_ret"] = df["close"].shift(-forward_days) / df["close"] - 1
        f["symbol"] = sym
        f["date"] = f.index
        frames.append(f)

    panel = pd.concat(frames).dropna()
    # Cross-sectional rank-normalize the target per date → [-0.5, 0.5]
    panel["target"] = panel.groupby("date")["fwd_ret"].rank(pct=True) - 0.5
    panel = panel.set_index(["date", "symbol"]).sort_index()
    return panel[cols], panel["target"]


# ─── Walk-forward model ───

def walk_forward_predict(X: pd.DataFrame, y: pd.Series,
                         train_days: int = 504, refit_every: int = 21,
                         embargo_days: int = 5,
                         min_train_rows: int = 5000) -> pd.Series:
    """
    Rolling walk-forward prediction (the book's anti-lookahead discipline):
    train on trailing `train_days` of data, predict the next `refit_every` days,
    then slide forward and refit. An embargo gap of `embargo_days` between the
    train and test windows prevents leakage from overlapping forward labels
    (purged/embargoed validation, the book's ch. on backtesting).
    Returns out-of-sample predictions only.
    """
    from sklearn.ensemble import HistGradientBoostingRegressor

    dates = X.index.get_level_values("date").unique().sort_values()
    preds = pd.Series(index=X.index, dtype=float)

    start_idx = train_days
    while start_idx < len(dates):
        train_dates = dates[start_idx - train_days:start_idx - embargo_days]
        test_dates = dates[start_idx:start_idx + refit_every]

        tr_mask = X.index.get_level_values("date").isin(train_dates)
        te_mask = X.index.get_level_values("date").isin(test_dates)

        Xtr, ytr = X[tr_mask], y[tr_mask]
        if len(Xtr) < min_train_rows:
            start_idx += refit_every
            continue

        model = HistGradientBoostingRegressor(
            max_iter=200, learning_rate=0.05, max_depth=6,
            l2_regularization=1.0, random_state=42
        )
        model.fit(Xtr, ytr)
        preds[te_mask] = model.predict(X[te_mask])
        start_idx += refit_every

    return preds


def rank_ic(preds: pd.Series, y: pd.Series) -> pd.Series:
    """Daily Spearman rank IC between predictions and realized targets."""
    df = pd.DataFrame({"p": preds, "y": y}).dropna()
    return df.groupby(level="date").apply(lambda g: g["p"].corr(g["y"], method="spearman"))


# ─── Backtest ───

def backtest_topk(preds: pd.Series, universe: Dict[str, pd.DataFrame],
                  top_k: int = 5, cost_bps: float = 5.0,
                  regime_filter: bool = True) -> pd.DataFrame:
    """
    Cost-aware daily backtest: hold the top-k predicted names, inverse-volatility
    weighted, rebalanced daily when the top-k membership changes.
    Optional regime filter: go flat when SPY < its 63d SMA (book's trend filter).
    Returns a DataFrame with daily strategy returns and diagnostics.
    """
    close = pd.DataFrame({s: df["close"] for s, df in universe.items()})
    ret = close.pct_change(fill_method=None)

    pred_df = preds.unstack("symbol")  # date x symbol predictions
    pred_df = pred_df.reindex(close.index)
    # Only trade names present in the provided universe (predictions may cover more)
    pred_df = pred_df[[c for c in pred_df.columns if c in close.columns]]

    # Regime filter: SPY above/below 63-day SMA
    spy_close = universe["SPY"]["close"]
    spy_sma63 = spy_close.rolling(63).mean()
    risk_on = (spy_close > spy_sma63).reindex(close.index).fillna(False)

    # Inverse-vol weights from 21d realized vol
    vol = ret.rolling(21).std()

    positions = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    current_holdings: List[str] = []

    for dt in close.index:
        p = pred_df.loc[dt].dropna()
        if regime_filter and not risk_on.get(dt, False):
            current_holdings = []
            continue
        if len(p) < top_k:
            continue
        new_top = list(p.nlargest(top_k).index)
        if set(new_top) != set(current_holdings):
            current_holdings = new_top
        if not current_holdings:
            continue
        w = 1.0 / vol.loc[dt, current_holdings].replace(0, np.nan)
        w = (w / w.sum()).fillna(0)
        positions.loc[dt, current_holdings] = w

    # Returns: positions held during day t earn ret at t+1 (trade at close)
    strat_ret = (positions.shift(1) * ret).sum(axis=1)
    turnover = positions.diff().abs().sum(axis=1)
    cost = turnover * (cost_bps / 1e4)
    strat_ret_net = strat_ret - cost

    out = pd.DataFrame({
        "gross": strat_ret,
        "net": strat_ret_net,
        "turnover": turnover,
        "n_positions": (positions > 0).sum(axis=1),
    })
    return out


def backtest_etf_tsmom(universe: Dict[str, pd.DataFrame], top_k: int = 3,
                       lookback: int = 126, skip: int = 21,
                       cost_bps: float = 5.0) -> pd.DataFrame:
    """
    ETF time-series momentum — the book's simplest surviving case study.
    Hypothesis: asset-class trends persist over medium horizons.
    Rule: hold top-k ETFs with POSITIVE skip-period momentum, inverse-vol weighted;
    flat otherwise. Membership checked daily, trades only on change.
    """
    etfs = [s for s in universe if s not in ("SPY", "QQQ", "DIA")]  # benchmarks excluded
    close = pd.DataFrame({s: universe[s]["close"] for s in etfs}).dropna()
    ret = close.pct_change(fill_method=None)

    signal = close.shift(skip) / close.shift(lookback) - 1
    vol = ret.rolling(21).std()

    positions = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    current: List[str] = []
    for dt in close.index:
        sig = signal.loc[dt].dropna()
        positive = sig[sig > 0]
        new_top = list(positive.nlargest(top_k).index)
        if set(new_top) != set(current):
            current = new_top
        if not current:
            continue
        w = 1.0 / vol.loc[dt, current].replace(0, np.nan)
        w = (w / w.sum()).fillna(0)
        positions.loc[dt, current] = w

    strat_ret = (positions.shift(1) * ret).sum(axis=1)
    turnover = positions.diff().abs().sum(axis=1)
    out = pd.DataFrame({
        "gross": strat_ret,
        "net": strat_ret - turnover * (cost_bps / 1e4),
        "turnover": turnover,
        "n_positions": (positions > 0).sum(axis=1),
    })
    return out


def performance_stats(bt: pd.DataFrame, col: str = "net") -> Dict[str, float]:
    """Standard performance summary (annualized, 252 trading days)."""
    r = bt[col].dropna()
    if r.empty:
        return {}
    cum = (1 + r).prod()
    years = len(r) / 252
    ann_ret = cum ** (1 / years) - 1 if years > 0 else np.nan
    ann_vol = r.std() * np.sqrt(252)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else np.nan
    equity = (1 + r).cumprod()
    dd = (equity / equity.cummax() - 1).min()
    return {
        "annual_return": float(ann_ret),
        "annual_vol": float(ann_vol),
        "sharpe": float(sharpe),
        "max_drawdown": float(dd),
        "hit_rate": float((r > 0).mean()),
        "avg_daily_turnover": float(bt["turnover"].mean()),
    }
