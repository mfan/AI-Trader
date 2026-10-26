"""
Alexander Elder's Trading Indicators
Based on "Trading for a Living" and "Come Into My Trading Room"

Implements Elder's proprietary indicators:
- Triple Screen Trading System
- Impulse System (EMA slope + MACD-Histogram)
- Elder-Ray (Bull Power & Bear Power)
- SafeZone Stops
- Force Index
- MACD-Histogram Divergence Detection
"""

import numpy as np
import pandas as pd
import talib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum


class ImpulseColor(Enum):
    """Impulse System color states"""
    GREEN = "green"  # Trend & momentum up → may buy
    RED = "red"      # Trend & momentum down → may short
    BLUE = "blue"    # Mixed/neutral → stand aside or manage positions


class ElderIndicators:
    """
    Alexander Elder's proprietary technical indicators
    
    Key concepts from "Trading for a Living":
    1. Triple Screen: Use multiple timeframes (weekly → daily → intraday)
    2. Impulse System: Combine trend (EMA) + momentum (MACD-Histogram)
    3. Elder-Ray: Measure bull/bear power relative to EMA
    4. SafeZone: Volatility-aware stops beyond normal noise
    5. Force Index: Volume-weighted price momentum
    """
    
    def __init__(self):
        """Initialize Elder indicators engine"""
        self.version = "1.0.0"
    
    # =====================================================================
    # IMPULSE SYSTEM - Elder's Traffic Light System
    # =====================================================================
    
    def calculate_impulse_system(
        self,
        close: np.ndarray,
        ema_period: int = 13,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Impulse System - Elder's "Traffic Light" for trading
        
        Combines:
        1. EMA slope (trend direction)
        2. MACD-Histogram (momentum)
        
        Rules:
        - GREEN: EMA rising AND MACD-Histogram rising → May BUY, avoid shorts
        - RED: EMA falling AND MACD-Histogram falling → May SHORT, avoid buys
        - BLUE: Mixed signals → Stand aside or manage existing positions
        
        Args:
            close: Closing prices
            ema_period: EMA period (default: 13)
            macd_fast: MACD fast period (default: 12)
            macd_slow: MACD slow period (default: 26)
            macd_signal: MACD signal period (default: 9)
            
        Returns:
            Tuple of (histogram values, color states)
        """
        # Calculate EMA
        ema = talib.EMA(close, timeperiod=ema_period)
        
        # Calculate MACD
        macd, signal, histogram = talib.MACD(
            close,
            fastperiod=macd_fast,
            slowperiod=macd_slow,
            signalperiod=macd_signal
        )
        
        # Determine EMA slope (is EMA rising or falling?)
        ema_slope = np.diff(ema)
        ema_rising = np.concatenate([[False], ema_slope > 0])
        
        # Determine MACD-Histogram slope
        hist_slope = np.diff(histogram)
        hist_rising = np.concatenate([[False], hist_slope > 0])
        
        # Apply Impulse System rules
        colors = []
        for i in range(len(close)):
            if i == 0 or np.isnan(ema[i]) or np.isnan(histogram[i]):
                colors.append(ImpulseColor.BLUE.value)
            elif ema_rising[i] and hist_rising[i]:
                colors.append(ImpulseColor.GREEN.value)  # Both rising → GREEN
            elif not ema_rising[i] and not hist_rising[i]:
                colors.append(ImpulseColor.RED.value)    # Both falling → RED
            else:
                colors.append(ImpulseColor.BLUE.value)   # Mixed → BLUE
        
        return histogram, colors
    
    # =====================================================================
    # ELDER-RAY (Bull Power & Bear Power)
    # =====================================================================
    
    def calculate_elder_ray(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        ema_period: int = 13
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Elder-Ray: Bull Power and Bear Power
        
        Measures the ability of bulls and bears to push prices 
        above/below the EMA (consensus of value).
        
        Bull Power = High - EMA
        Bear Power = Low - EMA
        
        Interpretation:
        - Bull Power > 0 & rising: Bulls strong, consider buying
        - Bull Power < 0 & rising: Bulls strengthening, potential reversal
        - Bear Power < 0 & falling: Bears strong, consider shorting
        - Bear Power > 0 & falling: Bears strengthening, potential reversal
        
        Divergence signals:
        - Price makes new high but Bull Power doesn't → Bearish divergence
        - Price makes new low but Bear Power doesn't → Bullish divergence
        
        Args:
            high: High prices
            low: Low prices
            close: Closing prices
            ema_period: EMA period (default: 13)
            
        Returns:
            Tuple of (bull_power, bear_power)
        """
        # Calculate EMA (consensus of value)
        ema = talib.EMA(close, timeperiod=ema_period)
        
        # Bull Power = High - EMA (how far bulls can push price up)
        bull_power = high - ema
        
        # Bear Power = Low - EMA (how far bears can push price down)
        bear_power = low - ema
        
        return bull_power, bear_power
    
    # =====================================================================
    # SAFEZONE STOPS - Volatility-Aware Stop Losses
    # =====================================================================
    
    def calculate_safezone_stop(
        self,
        high: np.ndarray,
        low: np.ndarray,
        lookback: int = 10,
        coefficient: float = 2.0,
        direction: str = "long"
    ) -> np.ndarray:
        """
        SafeZone Stops - Elder's volatility-aware stop-loss system
        
        Places stops beyond "normal noise" measured from recent extreme points.
        Adapts to volatility - wider stops in volatile markets, tighter in calm markets.
        
        For LONG positions:
        - Find recent lows that penetrated the previous low
        - Measure average downside penetration
        - Set stop = current_low - (coefficient × average_penetration)
        
        For SHORT positions:
        - Find recent highs that penetrated the previous high
        - Measure average upside penetration  
        - Set stop = current_high + (coefficient × average_penetration)
        
        Args:
            high: High prices
            low: Low prices
            lookback: Lookback period for measuring noise (default: 10)
            coefficient: Safety multiplier (default: 2.0 for conservative, 3.0 for very safe)
            direction: "long" or "short"
            
        Returns:
            Array of stop-loss levels
        """
        stops = np.full(len(low), np.nan)
        
        if direction.lower() == "long":
            # For long positions: measure downside penetrations
            for i in range(lookback, len(low)):
                penetrations = []
                
                # Look back at recent bars
                for j in range(i - lookback + 1, i):
                    # Did this bar's low penetrate the previous low?
                    if low[j] < low[j-1]:
                        penetration = low[j-1] - low[j]
                        penetrations.append(penetration)
                
                if penetrations:
                    avg_penetration = np.mean(penetrations)
                    # Stop = current low - (coefficient × average penetration)
                    stops[i] = low[i] - (coefficient * avg_penetration)
                else:
                    # No penetrations: use simple ATR-based stop
                    stops[i] = low[i] - (coefficient * np.std(low[i-lookback:i]))
        
        else:  # short
            # For short positions: measure upside penetrations
            for i in range(lookback, len(high)):
                penetrations = []
                
                # Look back at recent bars
                for j in range(i - lookback + 1, i):
                    # Did this bar's high penetrate the previous high?
                    if high[j] > high[j-1]:
                        penetration = high[j] - high[j-1]
                        penetrations.append(penetration)
                
                if penetrations:
                    avg_penetration = np.mean(penetrations)
                    # Stop = current high + (coefficient × average penetration)
                    stops[i] = high[i] + (coefficient * avg_penetration)
                else:
                    # No penetrations: use simple ATR-based stop
                    stops[i] = high[i] + (coefficient * np.std(high[i-lookback:i]))
        
        return stops
    
    # =====================================================================
    # FORCE INDEX - Volume-Weighted Momentum
    # =====================================================================
    
    def calculate_force_index(
        self,
        close: np.ndarray,
        volume: np.ndarray,
        period: int = 13
    ) -> np.ndarray:
        """
        Force Index - Measures power behind price moves
        
        Force Index = (Close - Previous Close) × Volume
        
        Then smooth with EMA for clearer signals.
        
        Interpretation:
        - Force Index > 0 & rising: Bulls in control, momentum increasing
        - Force Index < 0 & falling: Bears in control, downward momentum
        - Force Index crossing zero: Potential trend change
        - Divergence with price: Early warning of trend weakness
        
        Args:
            close: Closing prices
            volume: Volume data
            period: EMA smoothing period (default: 13)
            
        Returns:
            Smoothed Force Index values
        """
        # Raw Force Index = price change × volume
        price_change = np.diff(close, prepend=close[0])
        raw_force = price_change * volume
        
        # Smooth with EMA
        force_index = talib.EMA(raw_force, timeperiod=period)
        
        return force_index
    
    # =====================================================================
    # MACD-HISTOGRAM DIVERGENCE DETECTION
    # =====================================================================
    
    def detect_macd_divergence(
        self,
        close: np.ndarray,
        histogram: np.ndarray,
        lookback: int = 20,
        tolerance: float = 0.02
    ) -> Dict[str, Any]:
        """
        Detect MACD-Histogram divergences - Elder's early warning signals
        
        Bullish Divergence:
        - Price makes lower low
        - MACD-Histogram makes higher low
        - Signal: Downtrend weakening, potential reversal up
        
        Bearish Divergence:
        - Price makes higher high
        - MACD-Histogram makes lower high
        - Signal: Uptrend weakening, potential reversal down
        
        Args:
            close: Closing prices
            histogram: MACD-Histogram values
            lookback: Lookback period for finding divergences
            tolerance: Price tolerance for peak/trough detection (2%)
            
        Returns:
            Dict with divergence signals and details
        """
        if len(close) < lookback:
            return {
                "bullish_divergence": False,
                "bearish_divergence": False,
                "signal": "NEUTRAL",
                "details": "Insufficient data"
            }
        
        # Find price peaks and troughs
        price_peaks = []
        price_troughs = []
        hist_peaks = []
        hist_troughs = []
        
        for i in range(2, len(close) - 2):
            # Price peak detection
            if (close[i] > close[i-1] and close[i] > close[i-2] and
                close[i] > close[i+1] and close[i] > close[i+2]):
                price_peaks.append((i, close[i]))
                
            # Price trough detection
            if (close[i] < close[i-1] and close[i] < close[i-2] and
                close[i] < close[i+1] and close[i] < close[i+2]):
                price_troughs.append((i, close[i]))
            
            # Histogram peak detection
            if (histogram[i] > histogram[i-1] and histogram[i] > histogram[i-2] and
                histogram[i] > histogram[i+1] and histogram[i] > histogram[i+2]):
                hist_peaks.append((i, histogram[i]))
                
            # Histogram trough detection
            if (histogram[i] < histogram[i-1] and histogram[i] < histogram[i-2] and
                histogram[i] < histogram[i+1] and histogram[i] < histogram[i+2]):
                hist_troughs.append((i, histogram[i]))
        
        # Check for bearish divergence (price higher high, histogram lower high)
        bearish_div = False
        if len(price_peaks) >= 2 and len(hist_peaks) >= 2:
            last_price_peak = price_peaks[-1]
            prev_price_peak = price_peaks[-2]
            
            # Find corresponding histogram peaks
            for h1 in hist_peaks[::-1]:
                if abs(h1[0] - last_price_peak[0]) < 5:  # Within 5 bars
                    for h2 in hist_peaks[::-1]:
                        if abs(h2[0] - prev_price_peak[0]) < 5:
                            # Price made higher high, histogram made lower high
                            if last_price_peak[1] > prev_price_peak[1] and h1[1] < h2[1]:
                                bearish_div = True
                                break
                    break
        
        # Check for bullish divergence (price lower low, histogram higher low)
        bullish_div = False
        if len(price_troughs) >= 2 and len(hist_troughs) >= 2:
            last_price_trough = price_troughs[-1]
            prev_price_trough = price_troughs[-2]
            
            # Find corresponding histogram troughs
            for h1 in hist_troughs[::-1]:
                if abs(h1[0] - last_price_trough[0]) < 5:  # Within 5 bars
                    for h2 in hist_troughs[::-1]:
                        if abs(h2[0] - prev_price_trough[0]) < 5:
                            # Price made lower low, histogram made higher low
                            if last_price_trough[1] < prev_price_trough[1] and h1[1] > h2[1]:
                                bullish_div = True
                                break
                    break
        
        # Determine signal
        if bearish_div and bullish_div:
            signal = "CONFLICTING"
        elif bearish_div:
            signal = "BEARISH_DIVERGENCE"
        elif bullish_div:
            signal = "BULLISH_DIVERGENCE"
        else:
            signal = "NO_DIVERGENCE"
        
        return {
            "bullish_divergence": bullish_div,
            "bearish_divergence": bearish_div,
            "signal": signal,
            "details": {
                "price_peaks_found": len(price_peaks),
                "price_troughs_found": len(price_troughs),
                "hist_peaks_found": len(hist_peaks),
                "hist_troughs_found": len(hist_troughs)
            }
        }
    
    # =====================================================================
    # TRIPLE SCREEN ANALYSIS
    # =====================================================================
    
    def triple_screen_analysis(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray,
        timeframe: str = "daily"
    ) -> Dict[str, Any]:
        """
        Triple Screen Trading System - Elder's multi-timeframe approach
        
        Screen 1 (Higher Timeframe): Market Tide (use weekly if daily trading)
        - Trend direction via MACD-Histogram or slope of 13-week EMA
        - Determines if you go long, short, or stay flat
        
        Screen 2 (Intermediate Timeframe): Market Wave (use daily if intraday trading)
        - Counter-trend oscillator (Stochastic, Force Index, Elder-Ray)
        - Identifies pullbacks in direction of Screen 1 trend
        
        Screen 3 (Lower Timeframe): Intraday Breakout (use intraday if day trading)
        - Entry trigger: breakout of previous day's high/low
        - Trailing stop using SafeZone
        
        Args:
            high: High prices
            low: Low prices
            close: Closing prices
            volume: Volume data
            timeframe: Current timeframe being analyzed
            
        Returns:
            Dict with triple screen analysis results
        """
        # Screen 1: Trend (MACD-Histogram on higher timeframe)
        macd, signal, histogram = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        ema_26 = talib.EMA(close, timeperiod=26)
        
        # Determine trend
        if len(histogram) > 1:
            trend = "UP" if histogram[-1] > 0 else "DOWN"
            trend_strength = abs(histogram[-1])
        else:
            trend = "NEUTRAL"
            trend_strength = 0
        
        # Screen 2: Wave/Oscillator (Stochastic for pullbacks)
        slowk, slowd = talib.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowd_period=3)
        
        # Screen 3: Breakout/Entry (Impulse System for timing)
        hist_impulse, impulse_colors = self.calculate_impulse_system(close)
        
        # Elder-Ray for power analysis
        bull_power, bear_power = self.calculate_elder_ray(high, low, close)
        
        # SafeZone stops
        long_stop = self.calculate_safezone_stop(high, low, direction="long")
        short_stop = self.calculate_safezone_stop(high, low, direction="short")
        
        # Divergence detection
        divergence = self.detect_macd_divergence(close, histogram)
        
        return {
            "timeframe": timeframe,
            "screen_1_trend": {
                "direction": trend,
                "strength": float(trend_strength) if not np.isnan(trend_strength) else 0,
                "macd_histogram": float(histogram[-1]) if len(histogram) > 0 and not np.isnan(histogram[-1]) else 0,
                "ema_26": float(ema_26[-1]) if len(ema_26) > 0 and not np.isnan(ema_26[-1]) else 0
            },
            "screen_2_wave": {
                "stochastic_k": float(slowk[-1]) if len(slowk) > 0 and not np.isnan(slowk[-1]) else 50,
                "stochastic_d": float(slowd[-1]) if len(slowd) > 0 and not np.isnan(slowd[-1]) else 50,
                "oversold": slowk[-1] < 20 if len(slowk) > 0 else False,
                "overbought": slowk[-1] > 80 if len(slowk) > 0 else False
            },
            "screen_3_entry": {
                "impulse_color": impulse_colors[-1] if impulse_colors else "blue",
                "can_buy": impulse_colors[-1] == "green" if impulse_colors else False,
                "can_short": impulse_colors[-1] == "red" if impulse_colors else False,
                "stand_aside": impulse_colors[-1] == "blue" if impulse_colors else True
            },
            "elder_ray": {
                "bull_power": float(bull_power[-1]) if len(bull_power) > 0 and not np.isnan(bull_power[-1]) else 0,
                "bear_power": float(bear_power[-1]) if len(bear_power) > 0 and not np.isnan(bear_power[-1]) else 0,
                "bulls_strong": bull_power[-1] > 0 and bull_power[-1] > bull_power[-2] if len(bull_power) > 1 else False,
                "bears_strong": bear_power[-1] < 0 and bear_power[-1] < bear_power[-2] if len(bear_power) > 1 else False
            },
            "safezone_stops": {
                "long_stop": float(long_stop[-1]) if len(long_stop) > 0 and not np.isnan(long_stop[-1]) else 0,
                "short_stop": float(short_stop[-1]) if len(short_stop) > 0 and not np.isnan(short_stop[-1]) else 0,
                "current_price": float(close[-1]) if len(close) > 0 else 0
            },
            "divergence": divergence,
            "trading_signal": self._generate_triple_screen_signal(
                trend, impulse_colors[-1] if impulse_colors else "blue",
                slowk[-1] if len(slowk) > 0 else 50,
                divergence
            )
        }
    
    def _generate_triple_screen_signal(
        self,
        trend: str,
        impulse_color: str,
        stoch_k: float,
        divergence: Dict[str, Any]
    ) -> str:
        """
        Generate trading signal based on Triple Screen analysis
        
        Elder's Rules:
        1. Trade only in direction of Screen 1 trend
        2. Wait for Screen 2 pullback
        3. Enter on Screen 3 breakout
        """
        # Uptrend scenario
        if trend == "UP":
            if stoch_k < 30:  # Pullback (Screen 2)
                if impulse_color == "green":  # Entry signal (Screen 3)
                    return "STRONG_BUY"
                else:
                    return "BUY_SETUP"  # Wait for green
            elif impulse_color == "green":
                return "BUY"  # Trend trade
            else:
                return "HOLD_LONG"
        
        # Downtrend scenario
        elif trend == "DOWN":
            if stoch_k > 70:  # Rally (Screen 2)
                if impulse_color == "red":  # Entry signal (Screen 3)
                    return "STRONG_SELL"
                else:
                    return "SELL_SETUP"  # Wait for red
            elif impulse_color == "red":
                return "SELL"  # Trend trade
            else:
                return "HOLD_SHORT"
        
        # Divergence overrides
        if divergence.get("bullish_divergence"):
            return "BULLISH_DIVERGENCE_BUY"
        elif divergence.get("bearish_divergence"):
            return "BEARISH_DIVERGENCE_SELL"
        
        return "NEUTRAL"


def get_elder_engine() -> ElderIndicators:
    """Get singleton instance of Elder indicators engine"""
    return ElderIndicators()
