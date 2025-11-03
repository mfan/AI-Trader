"""
Technical Analysis Indicators Module using TA-Lib

This module provides technical analysis calculations for trading decisions.
Uses the industry-standard TA-Lib library for fast, accurate computations.

Optimized for swing trading and day trading strategies.
"""

import numpy as np
import pandas as pd
import talib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime


class TechnicalAnalysis:
    """
    Technical Analysis engine using TA-Lib
    
    Provides common technical indicators optimized for swing/day trading:
    - Trend: SMA, EMA, MACD, ADX
    - Momentum: RSI, Stochastic, CCI
    - Volatility: Bollinger Bands, ATR
    - Volume: OBV, Volume-weighted indicators
    """
    
    def __init__(self):
        """Initialize the technical analysis engine"""
        self.version = talib.__version__
    
    @staticmethod
    def validate_data(data: np.ndarray, min_length: int = 1) -> bool:
        """
        Validate input data for technical indicators
        
        Args:
            data: Input price/volume array
            min_length: Minimum required data points
            
        Returns:
            True if valid, False otherwise
        """
        if data is None or len(data) < min_length:
            return False
        if not isinstance(data, np.ndarray):
            return False
        if data.dtype != np.float64:
            return False
        return True
    
    def calculate_sma(self, close: np.ndarray, period: int = 20) -> np.ndarray:
        """
        Simple Moving Average
        
        Args:
            close: Closing prices
            period: Period for SMA calculation (default: 20)
            
        Returns:
            SMA values
        """
        return talib.SMA(close, timeperiod=period)
    
    def calculate_ema(self, close: np.ndarray, period: int = 20) -> np.ndarray:
        """
        Exponential Moving Average
        
        Args:
            close: Closing prices
            period: Period for EMA calculation (default: 20)
            
        Returns:
            EMA values
        """
        return talib.EMA(close, timeperiod=period)
    
    def calculate_rsi(self, close: np.ndarray, period: int = 14) -> np.ndarray:
        """
        Relative Strength Index
        
        Args:
            close: Closing prices
            period: Period for RSI calculation (default: 14)
            
        Returns:
            RSI values (0-100)
        """
        return talib.RSI(close, timeperiod=period)
    
    def calculate_macd(
        self, 
        close: np.ndarray,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Moving Average Convergence Divergence
        
        Args:
            close: Closing prices
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line period (default: 9)
            
        Returns:
            Tuple of (macd, signal, histogram)
        """
        macd, signal, hist = talib.MACD(
            close,
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period
        )
        return macd, signal, hist
    
    def calculate_bbands(
        self,
        close: np.ndarray,
        period: int = 20,
        nbdevup: float = 2.0,
        nbdevdn: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Bollinger Bands
        
        Args:
            close: Closing prices
            period: Period for moving average (default: 20)
            nbdevup: Number of std devs for upper band (default: 2.0)
            nbdevdn: Number of std devs for lower band (default: 2.0)
            
        Returns:
            Tuple of (upper, middle, lower) bands
        """
        upper, middle, lower = talib.BBANDS(
            close,
            timeperiod=period,
            nbdevup=nbdevup,
            nbdevdn=nbdevdn
        )
        return upper, middle, lower
    
    def calculate_atr(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """
        Average True Range - Volatility indicator
        
        Args:
            high: High prices
            low: Low prices
            close: Closing prices
            period: Period for ATR calculation (default: 14)
            
        Returns:
            ATR values
        """
        return talib.ATR(high, low, close, timeperiod=period)
    
    def calculate_stoch(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        fastk_period: int = 14,
        slowk_period: int = 3,
        slowd_period: int = 3
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Stochastic Oscillator
        
        Args:
            high: High prices
            low: Low prices
            close: Closing prices
            fastk_period: Fast %K period (default: 14)
            slowk_period: Slow %K period (default: 3)
            slowd_period: Slow %D period (default: 3)
            
        Returns:
            Tuple of (slowk, slowd)
        """
        slowk, slowd = talib.STOCH(
            high, low, close,
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowd_period=slowd_period
        )
        return slowk, slowd
    
    def calculate_adx(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """
        Average Directional Index - Trend strength
        
        Args:
            high: High prices
            low: Low prices
            close: Closing prices
            period: Period for ADX calculation (default: 14)
            
        Returns:
            ADX values (0-100)
        """
        return talib.ADX(high, low, close, timeperiod=period)
    
    def calculate_obv(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        On Balance Volume
        
        Args:
            close: Closing prices
            volume: Volume data
            
        Returns:
            OBV values
        """
        return talib.OBV(close, volume)
    
    def calculate_cci(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 20
    ) -> np.ndarray:
        """
        Commodity Channel Index
        
        Args:
            high: High prices
            low: Low prices
            close: Closing prices
            period: Period for CCI calculation (default: 20)
            
        Returns:
            CCI values
        """
        return talib.CCI(high, low, close, timeperiod=period)
    
    def calculate_vwap(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray
    ) -> np.ndarray:
        """
        Volume Weighted Average Price
        
        Args:
            high: High prices
            low: Low prices
            close: Closing prices
            volume: Volume data
            
        Returns:
            VWAP values
        """
        typical_price = (high + low + close) / 3.0
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap
    
    def get_comprehensive_analysis(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray,
        open_price: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive technical analysis
        
        Args:
            high: High prices
            low: Low prices
            close: Closing prices
            volume: Volume data
            open_price: Opening prices (optional)
            
        Returns:
            Dictionary with all technical indicators
        """
        # Convert to float64 if needed
        high = np.asarray(high, dtype=np.float64)
        low = np.asarray(low, dtype=np.float64)
        close = np.asarray(close, dtype=np.float64)
        volume = np.asarray(volume, dtype=np.float64)
        
        results = {}
        
        try:
            # Trend Indicators
            results['sma_20'] = self.calculate_sma(close, 20)
            results['sma_50'] = self.calculate_sma(close, 50)
            results['ema_12'] = self.calculate_ema(close, 12)
            results['ema_26'] = self.calculate_ema(close, 26)
            
            # MACD
            macd, signal, hist = self.calculate_macd(close)
            results['macd'] = macd
            results['macd_signal'] = signal
            results['macd_hist'] = hist
            
            # Momentum Indicators
            results['rsi_14'] = self.calculate_rsi(close, 14)
            slowk, slowd = self.calculate_stoch(high, low, close)
            results['stoch_k'] = slowk
            results['stoch_d'] = slowd
            results['cci_20'] = self.calculate_cci(high, low, close, 20)
            
            # Volatility Indicators
            upper, middle, lower = self.calculate_bbands(close)
            results['bb_upper'] = upper
            results['bb_middle'] = middle
            results['bb_lower'] = lower
            results['atr_14'] = self.calculate_atr(high, low, close)
            
            # Trend Strength
            results['adx_14'] = self.calculate_adx(high, low, close)
            
            # Volume Indicators
            results['obv'] = self.calculate_obv(close, volume)
            results['vwap'] = self.calculate_vwap(high, low, close, volume)
            
            # Latest values (most recent)
            latest = {}
            for key, values in results.items():
                if isinstance(values, np.ndarray):
                    latest[key] = float(values[-1]) if not np.isnan(values[-1]) else None
                else:
                    latest[key] = values
            
            return {
                'success': True,
                'indicators': results,
                'latest': latest,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_trading_signals(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray
    ) -> Dict[str, Any]:
        """
        Generate trading signals based on technical indicators
        
        Args:
            high: High prices
            low: Low prices  
            close: Closing prices
            volume: Volume data
            
        Returns:
            Dictionary with trading signals and confidence scores
        """
        analysis = self.get_comprehensive_analysis(high, low, close, volume)
        
        if not analysis['success']:
            return analysis
        
        latest = analysis['latest']
        signals = {
            'timestamp': datetime.now().isoformat(),
            'signals': []
        }
        
        # RSI signals
        rsi = latest.get('rsi_14')
        if rsi:
            if rsi < 30:
                signals['signals'].append({
                    'indicator': 'RSI',
                    'signal': 'OVERSOLD',
                    'action': 'BUY',
                    'value': rsi,
                    'confidence': 'HIGH' if rsi < 20 else 'MEDIUM'
                })
            elif rsi > 70:
                signals['signals'].append({
                    'indicator': 'RSI',
                    'signal': 'OVERBOUGHT',
                    'action': 'SELL',
                    'value': rsi,
                    'confidence': 'HIGH' if rsi > 80 else 'MEDIUM'
                })
        
        # MACD signals
        macd = latest.get('macd')
        macd_signal = latest.get('macd_signal')
        if macd and macd_signal:
            if macd > macd_signal:
                signals['signals'].append({
                    'indicator': 'MACD',
                    'signal': 'BULLISH_CROSSOVER',
                    'action': 'BUY',
                    'value': f'{macd:.4f} > {macd_signal:.4f}',
                    'confidence': 'MEDIUM'
                })
            elif macd < macd_signal:
                signals['signals'].append({
                    'indicator': 'MACD',
                    'signal': 'BEARISH_CROSSOVER',
                    'action': 'SELL',
                    'value': f'{macd:.4f} < {macd_signal:.4f}',
                    'confidence': 'MEDIUM'
                })
        
        # Bollinger Bands signals
        bb_upper = latest.get('bb_upper')
        bb_lower = latest.get('bb_lower')
        current_price = close[-1]
        
        if bb_upper and bb_lower:
            if current_price >= bb_upper:
                signals['signals'].append({
                    'indicator': 'Bollinger Bands',
                    'signal': 'PRICE_AT_UPPER_BAND',
                    'action': 'SELL',
                    'value': f'{current_price:.2f} >= {bb_upper:.2f}',
                    'confidence': 'MEDIUM'
                })
            elif current_price <= bb_lower:
                signals['signals'].append({
                    'indicator': 'Bollinger Bands',
                    'signal': 'PRICE_AT_LOWER_BAND',
                    'action': 'BUY',
                    'value': f'{current_price:.2f} <= {bb_lower:.2f}',
                    'confidence': 'MEDIUM'
                })
        
        # Stochastic signals
        stoch_k = latest.get('stoch_k')
        if stoch_k:
            if stoch_k < 20:
                signals['signals'].append({
                    'indicator': 'Stochastic',
                    'signal': 'OVERSOLD',
                    'action': 'BUY',
                    'value': stoch_k,
                    'confidence': 'MEDIUM'
                })
            elif stoch_k > 80:
                signals['signals'].append({
                    'indicator': 'Stochastic',
                    'signal': 'OVERBOUGHT',
                    'action': 'SELL',
                    'value': stoch_k,
                    'confidence': 'MEDIUM'
                })
        
        # Overall signal
        buy_signals = sum(1 for s in signals['signals'] if s['action'] == 'BUY')
        sell_signals = sum(1 for s in signals['signals'] if s['action'] == 'SELL')
        
        if buy_signals > sell_signals:
            signals['overall'] = 'BUY'
            signals['strength'] = buy_signals - sell_signals
        elif sell_signals > buy_signals:
            signals['overall'] = 'SELL'
            signals['strength'] = sell_signals - buy_signals
        else:
            signals['overall'] = 'NEUTRAL'
            signals['strength'] = 0
        
        return signals


# Singleton instance
_ta_engine = None

def get_ta_engine() -> TechnicalAnalysis:
    """
    Get or create the Technical Analysis engine (singleton)
    
    Returns:
        TechnicalAnalysis instance
    """
    global _ta_engine
    if _ta_engine is None:
        _ta_engine = TechnicalAnalysis()
    return _ta_engine


if __name__ == "__main__":
    # Test the technical analysis engine
    print("🧪 Testing Technical Analysis Engine...")
    print("=" * 60)
    
    ta = get_ta_engine()
    print(f"TA-Lib version: {ta.version}")
    
    # Sample data
    np.random.seed(42)
    n = 100
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    high = close + np.abs(np.random.randn(n))
    low = close - np.abs(np.random.randn(n))
    volume = np.random.randint(1000, 10000, n).astype(np.float64)
    
    # Convert to float64
    high = high.astype(np.float64)
    low = low.astype(np.float64)
    close = close.astype(np.float64)
    
    print(f"\nTest data: {n} bars")
    print(f"Price range: ${low.min():.2f} - ${high.max():.2f}")
    print("-" * 60)
    
    # Get comprehensive analysis
    analysis = ta.get_comprehensive_analysis(high, low, close, volume)
    
    if analysis['success']:
        print("\n📊 Latest Technical Indicators:")
        for key, value in analysis['latest'].items():
            if value is not None:
                print(f"  {key}: {value:.2f}")
        
        print("\n" + "=" * 60)
        
        # Get trading signals
        signals = ta.get_trading_signals(high, low, close, volume)
        
        print(f"\n🎯 Trading Signals:")
        print(f"Overall: {signals['overall']} (Strength: {signals['strength']})")
        print("\nDetailed Signals:")
        for signal in signals['signals']:
            print(f"  [{signal['indicator']}] {signal['signal']}")
            print(f"    Action: {signal['action']}")
            print(f"    Value: {signal['value']}")
            print(f"    Confidence: {signal['confidence']}")
            print()
        
        print("=" * 60)
        print("✅ Technical Analysis engine test completed successfully!")
    else:
        print(f"❌ Error: {analysis['error']}")
