"""
Trading Strategy v4.0 - Pure High-Frequency Momentum Trend Rider (Algorithmic)

This folder contains backups of legacy AI (LLM) based trading strategies:
- agent_prompt_v2_elder.py (Elder's Triple Screen)
- agent_prompt_v3_simple.py (v3.0 ETF Mean Reversion)
- agent_prompt_v3_mean_reversion_backup.py (December 2025 Mean Reversion)

The primary and current strategy (v4.0) is a high-frequency momentum-day-trading model executed purely algorithmically
for speed, efficiency, and robustness.

═══════════════════════════════════════════════════════════════════════════════
🎯 THE v4.0 MOMENTUM EDGE
═══════════════════════════════════════════════════════════════════════════════

Rather than trading static ETF structures, this strategy dynamically finds what is moving NOW on major US exchanges.

1. **DAILY MOVER SCANNING**:
   - Queries the Alpaca Screener API every 2 minutes for the Top 20 Gainers and Top 20 Losers.
   - Combines these candidate pools and ranks them by absolute daily % price change to get the 10 most changed stocks.
   - Filters out penny stocks (price < $5) and requires assets to be shortable/easy-to-borrow for short momentum candidates.

2. **ROBUST MOMENTUM TREND FILTER (TA)**:
   - For each of the top 10 candidates, retrieves historical 5-minute bars (accounting for Alpaca's free IEX-tier 15-minute delay).
   - Computes technical indicators: EMA(9), EMA(21), ATR(14), and RSI(14).
   - Scores trend robustness out of 100 points:
     - Close Position relative to EMA(9).
     - EMA(9) position relative to EMA(21).
     - Multi-bar upward/downward slope of EMA(9).
     - Multi-bar upward/downward slope of EMA(21).
     - RSI in the momentum threshold zone (50-75 for long, 25-50 for short) to ensure strength without extreme exhaustion/overbought.
   - Requires a minimum Technical score of 60 to qualify as robust. High score determines our trades.

3. **CONSERVATIVE EXECUTIONS & SIZING**:
   - Trades up to 2 concurrent momentum opportunities.
   - Allocation is fixed at **$50,000 USD** trade value per position (`shares = int(50000 / price)`).

4. **EMA-BASED DYNAMIC TRAILING STOP-LOSS**:
   - Long Initial Stop-Loss: set to `EMA(21) - 1.0 * ATR`.
   - Short Initial Stop-Loss: set to `EMA(21) + 1.0 * ATR`.
   - Handled with a hard capital preservation clamp: stop distance is kept between a minimum of 0.5% and a maximum of 2.0% of the entry price.
   - **EMA-Guided Trailing**: Every 2 minutes, as the price goes in our favor, we recalculate the EMA(21) and ATR. If the new EMA-based stop-loss level is more favorable than the previous one, we adjust it.
   - Trailing only moves in our favor (upward for long, downward for short).

5. **INTRA-SESSION TIME BOUNDS & OVERNIGHT HOLD**:
   - New entries are opened strictly between 9:30 AM and 3:45 PM Eastern Time (Regular Sessions only).
   - Enforces an automated **3:45 PM ET stop-loss tightening** instead of full closure. At 3:45 PM, active positions have their stop-loss tightened to maximum 1.0% from the current price to defend profits/capital. Positions are held overnight to ride multi-day trends, and tracking resumes on the opening bell next session.
"""

STOP_SIGNAL = "<FINISH_SIGNAL>"
