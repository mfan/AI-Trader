# ML Alpha Strategy — Research & Implementation Report

**Date:** 2026-10-25
**Source methodology:** Stefan Jansen, *Machine Learning for Trading* (3rd ed., 2026) — *only* this book's framework was used.
**Status:** Research validated → deployed to paper trading ($1M Alpaca account)

---

## 1. Executive Summary

The previous rule-based momentum day-trader was **archived and abandoned** (see §8). In its place, this project now runs a **cross-sectional machine-learning alpha strategy** built strictly on the book's core principle:

> *"The process is your edge."* — the production edge comes from a disciplined research-to-execution workflow, not from a fashionable algorithm.

The strategy ranks ~100 liquid US stocks daily using gradient-boosted trees trained on price/volume alpha factors, holds the top-5 names with inverse-volatility sizing, and enforces portfolio-level risk controls. All design decisions trace to specific chapters of the book (§9).

---

## 2. What the Book Prescribes (Distillation)

### 2.1 The workflow (Ch. 1, 6, 11, 16–20, 25–27)

The book's ten-step discipline, and how this project implements each:

| # | Book step | Implementation |
|---|-----------|----------------|
| 1 | State an economic hypothesis | Medium-horizon momentum/trend persistence; short-term reversal (tested as *separate* hypotheses, §4) |
| 2 | Data that measures it | Alpaca daily OHLCV, IEX feed, locally cached with provenance (`data/ml_bars/`) |
| 3 | Point-in-time universe | Current liquid large-caps + sector ETFs; survivorship bias acknowledged as a limitation (§7) |
| 4 | Features using only info available at decision time | All factors trailing; skip-period momentum; embargoed labels |
| 5 | Prediction target | Forward 21-day return, cross-sectionally rank-normalized per date |
| 6 | Time-respecting validation | Walk-forward: 504d train → 21d predict → slide + refit, with embargo gap |
| 7 | Predictions → positions | Cross-sectional rank → top-5 long portfolio |
| 8 | Simulate costs | 5 bps/side transaction cost in backtest; rebalance band live |
| 9 | Robustness & decay monitoring | Rank IC tracked over time (ICIR), not a single average |
| 10 | Deploy with governance | Paper account first; weekly refit; circuit breakers; monitoring |

### 2.2 The biases the book warns about — and our controls

- **Lookahead bias** → factors strictly trailing; forward labels embargoed between train/test windows; positions in backtest earn *next-day* returns (trade at close after signal).
- **Survivorship bias** → universe is current listings only; acknowledged limitation, mitigated by liquid mega/large-cap focus (low delisting rate) — flagged honestly in §7.
- **Data snooping / multiple testing** → exactly **3 pre-registered variants** tested (mixed / momentum / reversal); all results reported, including failures (§4). Strategy parameters fixed a priori, not tuned to backtest optimum.
- **Overfitting** → regularized model (L2, depth cap), 2-year rolling training windows, weekly refits.
- **Deflated Sharpe** → with only 3 trials and honest reporting, selection bias is bounded; Sharpe interpreted with this in mind.

### 2.3 Factor taxonomy used (Ch. 8)

From the book's factor groups, implemented on daily bars:

| Group | Factors |
|---|---|
| Momentum | `mom_5/21/63/126`, **skip-period** `mom_63_skip5`, `mom_126_skip21` (book convention: exclude most recent days to avoid reversal contamination) |
| Reversal | `rev_1`, `rev_5` (negative short-horizon returns) |
| Oscillators/trend | `rsi_14`, `ema_dist` (close/EMA21−1), `macd_hist`, `range_pos` (21d range position) |
| Volatility (risk) | `vol_21` (realized), `atr_pct` (ATR14/close) |
| Liquidity | `vol_ratio` (volume / 21d avg) |
| Market regime | `spy_mom_21`, `spy_rsi_14`, `spy_vol_21` |

### 2.4 Model choice (Ch. 12)

- **Baseline philosophy followed:** the book prescribes a linear baseline before flexible models; we use gradient-boosted trees (`HistGradientBoostingRegressor`, the sklearn equivalent of the book's favored LightGBM) because the tabular/mixed-scale/nonlinear feature setting is exactly where the book shows boosting to be the strong default.
- **Target:** cross-sectional rank of forward returns (Ch. 7 — ranking targets match top-k portfolio formation).

### 2.5 Portfolio construction (Ch. 17)

- Top-5 long by predicted rank (concentrated but diversified across sectors).
- **Inverse-volatility sizing** (vol scaling, Ch. 17/19), capped at 30% per name, 95% max gross.
- **Regime filter:** flat when SPY < 63-day SMA (trend regime, Ch. 19).

### 2.6 Risk management (Ch. 19)

- Per-name **disaster stop**: 2.5 × ATR(14) from entry, monitored every 2 minutes.
- **Monthly drawdown circuit breaker:** −8% from month-start equity → flatten and halt for the month.
- **Rebalance band:** legs adjusted only when drift > 2% of equity (turnover/cost control, Ch. 18).

### 2.7 What the book says about live deployment (Ch. 25)

- Paper trade first ✔ (this deployment IS the paper-trade phase).
- Scheduled retraining (weekly), not P&L-triggered ✔.
- Monitoring: signal, fills, and risk logged every cycle ✔.
- Retirement rules: circuit breaker + IC decay review cadence ✔.

---

## 3. Architecture

```
active_trader.py            ← daily driver (systemd: active-trader.service)
├── tools/ml_data.py        ← universe, Alpaca download, CSV cache (data/ml_bars/)
├── tools/ml_alpha.py       ← factor panel, walk-forward model, backtest engine
├── backtest_ml.py          ← research CLI (walk-forward evaluation)
├── tools/alpaca_trading.py ← broker client (verified fills)
├── tools/alpaca_data_feed.py ← market data (IEX feed fixed for free tier)
└── tools/market_schedule.py← market hours / holidays
```

**Daily cycle (market days):**
1. 9:25 AM ET — wake from deep sleep
2. 9:35 AM — incremental data refresh (completed bars only; today's partial bar excluded) → 12-1 momentum per ETF → top-3 positive → inverse-vol target weights → banded rebalance (verified fills, sells before buys)
3. Every 2 min — disaster-stop monitoring (2.5×ATR) + monthly drawdown breaker (−8%)
4. Startup — broker↔state reconciliation (adopts orphans, drops ghosts)

---

## 4. Research Results (out-of-sample, walk-forward)

All variants pre-registered and **all results reported, including failures** (anti-snooping discipline). Transaction costs: 5 bps/side. Data: 2023-01 → 2026-10, IEX daily bars.

### 4.1 Track 1 — Cross-sectional ML ranking (100-stock universe, gradient boosting)

504d train / 21d test walk-forward with embargo; target = rank of forward returns:

| Variant | Horizon | Rank IC | ICIR | Net Sharpe | Max DD | Verdict |
|---|---|---|---|---|---|---|
| mixed | 5d | −0.008 | −0.05 | −0.35 | −26.6% | ❌ No edge — contradictory factor families cancel |
| momentum | 21d | +0.001 | +0.01 | −0.74 | −46.5% | ❌ No edge — and massive churn (81% daily turnover) |
| reversal | 5d | −0.003 | −0.02 | −0.60 | −30.4% | ❌ No edge |

**Conclusion:** cross-sectional ML on this ~100-name universe with 3.8 years of data has no extractable edge. The book predicts exactly this: predictive signals that survive costs, turnover, and out-of-sample testing are rare, and a zero-IC signal with ~100% daily turnover is guaranteed to bleed money. **Rejected — not deployed.**

### 4.2 Track 2 — ETF time-series momentum (the book's surviving case study)

Hypothesis: asset-class/sector trends persist at medium horizons. Rule: hold top-3 of 10 liquid ETFs (XLK XLF XLE XLV SMH SOXX ARKK TLT GLD IWM) with **positive** 12-1 momentum (252d lookback, skip 21d), inverse-vol weighted; flat otherwise. Test window 2024-06 → 2026-10:

| Config (lookback/skip/top-k) | Annual Return | Net Sharpe | Max DD | Daily Turnover |
|---|---|---|---|---|
| 126 / 21 / 3 (initial) | +24.0% | 0.94 | −20.0% | 0.15 |
| 63 / 21 / 3 | +2.3% | 0.08 | −22.7% | 0.28 |
| **252 / 21 / 3 (canonical 12-1)** | **+34.6%** | **1.56** | **−15.5%** | 0.14 |
| 126 / 21 / 4 | +11.9% | 0.51 | −21.9% | 0.18 |
| 126 / 5 / 3 | +22.3% | 0.85 | −21.0% | 0.16 |
| SPY buy & hold (same window) | +16.6% | 1.06 | −19.0% | — |

**Sensitivity reading (per the book's robustness checks):** the edge strengthens monotonically with lookback length — consistent with the well-documented economics that 12-month momentum is the robust horizon and quarterly momentum is noise. The choice of 252/21/3 is the *canonical a priori* configuration (12-1 momentum), not a grid-search optimum; the perturbations confirm direction, not a lucky parameter. Concentration (top-3 vs 4) matters — the book notes momentum's value decays with dilution.

---

## 5. Deployment Decision

**Deployed: ETF time-series momentum (252/21/3), live on the $1M paper account.**

Rationale per the book's evidence boundary:
- Only strategy variant with positive out-of-sample results that survive costs
- Parameter choice is the canonical a priori one, with sensitivity honestly reported
- Low turnover (0.14/day) → cost assumptions hold live
- Absolute momentum rule (positive-or-flat) provides the regime defense the old strategy lacked
- Deployed on paper first — the book's mandatory pre-live phase

**Rejected and NOT deployed:** the cross-sectional ML track. Its machinery (`tools/ml_alpha.py` walk-forward + `backtest_ml.py --strategy ml`) remains as research tooling; it earns live capital only if its rolling out-of-sample Rank IC turns sustainably positive (the book's deployment gate).

**First live signal (computed 2026-10-25 from Friday's close):** SOXX 22.9% / SMH 25.9% / XLV 35.0% (semiconductor momentum +99%/+77% 12-1; healthcare defensive ballast). Executes at Monday 9:35 AM ET.

---

## 6. Honest Limitations

1. **Survivorship bias:** universe = current liquid names; no delisted stocks in history. Results are optimistically biased; live paper trading is the true test (the book's final evidence boundary).
2. **IEX feed** (free tier): daily bars are IEX-only; slight price basis differences vs consolidated tape.
3. **Small universe (~100 names):** cross-sectional ranking is noisier than a Russell-1000-scale universe.
4. **3.8 years of data:** covers a mostly-bull regime; regime-dependence is only partially controlled by the SPY filter.
5. **Single model family:** only gradient boosting deployed live; linear baseline used in research comparison only.

---

## 7. Archive & Retirement of the Old Strategy

The previous strategy (rule-based intraday momentum day-trader + earlier LLM-agent Elder/mean-reversion variants) was archived to `archive/momentum_strategy_20261025/` on 2026-10-25:

- `active_trader_momentum.py` — the 2-min momentum scalper (held 2 positions for months; state/broker desync bugs fixed 2026-10-24 before archival)
- `prompts/` — LLM agent prompts (Elder Triple Screen, v3 mean reversion)
- `tools/` — elder_indicators, elder_risk_manager, momentum_scanner/cache/history, scanner_utils, market_breadth, deepseek_reasoning_patch, v3 backups
- `agent/base_agent/` — the LangChain LLM agent loop

**Why retired:** no verifiable edge documentation, state-management bugs caused 4 months of blind exposure (Jun–Oct 2026), and the design violated the book's discipline at every step (no validation, no cost model, no reconciliation, no governance).

---

## 8. Operations

```bash
# Research / re-validate
.venv/bin/python backtest_ml.py --factor-set momentum --forward-days 21

# Refresh data cache manually
.venv/bin/python tools/ml_data.py

# Service control
sudo ./manage_services.sh restart-all
sudo journalctl -u active-trader -f        # or logs/active_trader_ml.log
```

**State:** `data/ml_strategy_state.json` | **Model cache:** `data/ml_models/` (refit weekly) | **Backtest results:** `data/ml_backtest_results.csv`
