# Active Trader — ML-Driven ETF Momentum System

> **Strategy v4.0** — built exclusively on the methodology of Stefan Jansen's
> *Machine Learning for Trading* (3rd ed.). Full research write-up:
> **[ML_STRATEGY_REPORT.md](ML_STRATEGY_REPORT.md)** (rendered HTML: `docs/strategy_report.html`)

## Overview

The Active Trader is an **autonomous systematic trading system** running 24/7 as a
systemd service on Linux, trading a $1M Alpaca **paper account**. The current strategy
is **ETF time-series momentum (TSMOM)** — selected by a disciplined, book-prescribed
research process in which three cross-sectional ML variants were tested, honestly
evaluated, and **rejected for lack of out-of-sample edge**.

> *"The process is your edge."* — the production advantage comes from the
> research-to-execution workflow, not from a fashionable algorithm.

### Key Features

- 📈 **Evidence-based strategy**: 12-1 time-series momentum on 10 liquid sector/asset ETFs
- 🧪 **Honest research pipeline**: walk-forward validation with purged/embargoed labels, realistic costs, parameter sensitivity analysis — failures reported, not hidden
- 🏆 **Validated results** (2024-06 → 2026-10, after 5bps costs): **Sharpe 1.56**, +34.6%/yr, −15.5% max drawdown, 0.14 daily turnover
- ⚖️ **Inverse-volatility sizing**: top-3 positive-momentum ETFs, 35% per-name cap
- 🛡️ **Layered risk controls**: 2.5×ATR disaster stops (2-min monitoring), −8% monthly drawdown circuit breaker, absolute-momentum regime defense (flat when no trends)
- 🔁 **Verified execution**: order fills confirmed by polling — submission is never trusted; broker↔state reconciliation at every startup
- 💤 **24/7 daemon**: deep sleep outside market hours, daily 9:35 AM ET signal cycle

## The Strategy (v4.0 — ETF Time-Series Momentum)

### Economic Hypothesis

Asset-class and sector trends **persist over medium horizons** (a robust, heavily
documented anomaly). Absolute (time-series) momentum also provides a built-in regime
defense: when nothing trends up, the strategy goes flat.

### Rules (fixed a priori — not grid-searched)

| Component | Rule |
|---|---|
| Universe | 10 liquid ETFs: XLK, XLF, XLE, XLV, SMH, SOXX, ARKK, TLT, GLD, IWM |
| Signal | 252-day return **skipping the most recent 21 days** (classic 12-1 momentum) |
| Selection | Top-3 ETFs with **positive** momentum; flat if none qualify |
| Sizing | Inverse 21-day realized volatility, capped at 35% per name (≤95% gross) |
| Rebalance | Daily membership check; legs traded only when drift > 2% of equity |
| Stops | 2.5 × ATR(14) disaster stop per position, checked every 2 minutes |
| Breaker | −8% from month-start equity → flatten and halt for the month |

### Why not the ML model?

Three pre-registered cross-sectional ML variants (gradient boosting on a 13-factor
panel over ~100 stocks) were walk-forward tested and showed **no out-of-sample edge**
(Rank IC ≈ 0, net Sharpe −0.35 to −0.74). Per the book's evidence discipline they were
**rejected, not deployed**. The ML machinery remains available for research
(`backtest_ml.py --strategy ml`) and earns live capital only if its rolling IC turns
sustainably positive. Full results: [ML_STRATEGY_REPORT.md](ML_STRATEGY_REPORT.md) §4.

## Quick Start

### Prerequisites

```bash
cd /home/mfan/work/aitrader
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# ML research stack
pip install scikit-learn markdown pandas numpy
```

Create `.env` (never commit it — see `.env.example`):

```bash
ALPACA_API_KEY=PK...          # paper account key
ALPACA_SECRET_KEY=...
ALPACA_PAPER_TRADING=true
```

### Running

**Production (systemd):**
```bash
sudo ./manage_services.sh install       # install unit files
sudo ./manage_services.sh restart-all   # MCP services + trader
sudo journalctl -u active-trader -f     # follow logs
```

**Development:**
```bash
source .venv/bin/activate
python active_trader.py
```

### Research & Validation

```bash
# Re-run the strategy backtest (walk-forward, after costs)
.venv/bin/python backtest_ml.py --strategy tsmom            # deployed strategy
.venv/bin/python backtest_ml.py --strategy tsmom --lookback 63 --top-k 4  # sensitivity
.venv/bin/python backtest_ml.py --strategy ml --factor-set momentum       # ML research track

# Refresh the market-data cache
.venv/bin/python tools/ml_data.py

# Render the report to HTML
.venv/bin/python tools/render_report.py
```

## System Architecture

```
active_trader.py            Daily TSMOM driver (systemd: active-trader.service)
├── tools/ml_data.py        Universe + Alpaca IEX daily-bar cache (data/ml_bars/)
├── tools/ml_alpha.py       Factor library, embargoed walk-forward, backtest engines
├── backtest_ml.py          Research CLI (walk-forward evaluation)
├── tools/alpaca_trading.py Broker client (fill-verified orders)
├── tools/alpaca_data_feed.py Market data (IEX feed for free tier)
├── tools/market_schedule.py  Market hours / holidays / deep-sleep timing
└── tools/render_report.py  Markdown → styled HTML report
```

**Daily cycle (market days):**
1. **9:25 AM ET** — wake from deep sleep
2. **9:35 AM** — incremental data refresh (completed bars only) → 12-1 momentum per
   ETF → top-3 positive → inverse-vol weights → banded rebalance (sells before buys,
   all fills verified)
3. **Every 2 min** — disaster-stop monitoring + monthly drawdown breaker
4. **Startup** — broker↔state reconciliation (adopts orphans, drops ghosts, syncs qty)

## Risk Management

| Control | Limit |
|---|---|
| Positions | Max 3 (top-3 momentum) |
| Per-name weight | ≤ 35% of equity (inverse-vol scaled) |
| Gross exposure | ≤ 95% of equity |
| Disaster stop | 2.5 × ATR(14) below entry, monitored every 2 min |
| Monthly breaker | −8% from month-start equity → flat + halt |
| Regime defense | Flat when no ETF has positive 12-1 momentum |

## Data & State

| Path | Contents |
|---|---|
| `data/ml_bars/` | Cached daily OHLCV per symbol (IEX feed, incremental) |
| `data/ml_strategy_state.json` | Live positions, stops, history, breaker state |
| `data/ml_backtest_*.csv` | Backtest daily returns (regenerable) |
| `logs/active_trader_ml.log` | Strategy log (signals, fills, risk events) |

> Runtime artifacts and secrets (`.env*`, `data/ml_*`, state files, logs) are
> gitignored — never commit them.

## Documentation

- **[ML_STRATEGY_REPORT.md](ML_STRATEGY_REPORT.md)** — full research report: book distillation, all variant results (including failures), deployment decision, limitations
- `docs/strategy_report.html` — rendered HTML version (`tools/render_report.py`)
- **[CLAUDE.md](CLAUDE.md)** — operational handbook, changelog, troubleshooting

## Key Files Reference

| File | Purpose |
|---|---|
| `active_trader.py` | Main strategy driver (TSMOM) |
| `tools/ml_data.py` | Universe definition, data download/cache |
| `tools/ml_alpha.py` | Factors, walk-forward ML, backtest engines |
| `backtest_ml.py` | Research/validation CLI |
| `archive/momentum_strategy_20261025/` | Retired strategies (reference only) |

## Version History

### v4.0 (Oct 25, 2026) — Book-Distilled ETF Time-Series Momentum
Complete strategy replacement grounded in Jansen's *Machine Learning for Trading*.
Cross-sectional ML rejected after honest walk-forward evaluation; ETF TSMOM validated
(Sharpe 1.56 OOS after costs) and deployed. New research/backtest/report tooling.
Also: IEX feed fix, systemd restart resilience, broker reconciliation, verified fills.

### v3.x and earlier — *archived*
Mean-reversion day trader (v3.0), Elder Triple Screen LLM agent (v2.0), and modular
architecture (v1.5) are preserved in `archive/momentum_strategy_20261025/` for
reference. Retired due to unverifiable edge and production state-sync defects
(Jun–Oct 2026 post-mortem in CLAUDE.md).
