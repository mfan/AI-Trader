"""
Technical Analysis Helper for Trading System

This module provides easy-to-use functions for integrating technical analysis
into trading decisions for both active_trader.py and AI agents.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.technical_indicators import get_ta_engine
from tools.alpaca_data_feed import AlpacaDataFeed


class TradingDecisionHelper:
    """
    Helper class for making trading decisions based on technical analysis
    """
    
    def __init__(self):
        """Initialize with data feed and TA engine"""
        self.data_feed = AlpacaDataFeed()
        self.ta_engine = get_ta_engine()
    
    def should_buy(
        self,
        symbol: str,
        lookback_days: int = 30,
        min_signal_strength: int = 2
    ) -> Dict[str, Any]:
        """
        Determine if we should buy a stock based on technical analysis
        
        Args:
            symbol: Stock symbol to analyze
            lookback_days: Days of historical data to use
            min_signal_strength: Minimum signal strength required (default: 2)
            
        Returns:
            Dictionary with:
            - should_buy: bool
            - confidence: str (HIGH, MEDIUM, LOW)
            - reasons: List[str] of reasons
            - signals: Dict of all signals
            - current_price: float
        """
        try:
            # Get historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days + 10)
            
            bars_dict = self.data_feed.get_daily_bars(
                [symbol],
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            
            if not bars_dict or symbol not in bars_dict or not bars_dict[symbol]:
                return {
                    "should_buy": False,
                    "confidence": "NONE",
                    "reasons": ["No historical data available"],
                    "current_price": None
                }
            
            bars = bars_dict[symbol]
            
            # Extract OHLCV data
            high = np.array([float(bar['high']) for bar in bars], dtype=np.float64)
            low = np.array([float(bar['low']) for bar in bars], dtype=np.float64)
            close = np.array([float(bar['close']) for bar in bars], dtype=np.float64)
            volume = np.array([float(bar['volume']) for bar in bars], dtype=np.float64)
            
            # Get trading signals
            signals = self.ta_engine.get_trading_signals(high, low, close, volume)
            current_price = float(close[-1])
            
            # Analyze signals
            overall = signals.get('overall', 'NEUTRAL')
            strength = signals.get('strength', 0)
            signal_list = signals.get('signals', [])
            
            # Determine buy decision
            should_buy = overall == 'BUY' and strength >= min_signal_strength
            
            # Build reasons
            reasons = []
            if overall == 'BUY':
                buy_signals = [s for s in signal_list if s['action'] == 'BUY']
                for sig in buy_signals:
                    reasons.append(f"{sig['indicator']}: {sig['signal']} ({sig['confidence']})")
            else:
                reasons.append(f"Overall signal is {overall}, not BUY")
                if strength < min_signal_strength:
                    reasons.append(f"Signal strength {strength} < minimum {min_signal_strength}")
            
            # Determine confidence
            if strength >= 3:
                confidence = "HIGH"
            elif strength >= 2:
                confidence = "MEDIUM"
            elif strength >= 1:
                confidence = "LOW"
            else:
                confidence = "NONE"
            
            return {
                "should_buy": should_buy,
                "confidence": confidence,
                "reasons": reasons,
                "signals": signals,
                "current_price": current_price,
                "signal_strength": strength,
                "overall_direction": overall
            }
            
        except Exception as e:
            return {
                "should_buy": False,
                "confidence": "NONE",
                "reasons": [f"Error analyzing: {str(e)}"],
                "current_price": None
            }
    
    def should_sell(
        self,
        symbol: str,
        lookback_days: int = 30,
        min_signal_strength: int = 2
    ) -> Dict[str, Any]:
        """
        Determine if we should sell a stock based on technical analysis
        
        Args:
            symbol: Stock symbol to analyze
            lookback_days: Days of historical data to use
            min_signal_strength: Minimum signal strength required (default: 2)
            
        Returns:
            Dictionary with:
            - should_sell: bool
            - confidence: str (HIGH, MEDIUM, LOW)
            - reasons: List[str] of reasons
            - signals: Dict of all signals
            - current_price: float
        """
        try:
            # Get historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days + 10)
            
            bars_dict = self.data_feed.get_daily_bars(
                [symbol],
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            
            if not bars_dict or symbol not in bars_dict or not bars_dict[symbol]:
                return {
                    "should_sell": False,
                    "confidence": "NONE",
                    "reasons": ["No historical data available"],
                    "current_price": None
                }
            
            bars = bars_dict[symbol]
            
            # Extract OHLCV data
            high = np.array([float(bar['high']) for bar in bars], dtype=np.float64)
            low = np.array([float(bar['low']) for bar in bars], dtype=np.float64)
            close = np.array([float(bar['close']) for bar in bars], dtype=np.float64)
            volume = np.array([float(bar['volume']) for bar in bars], dtype=np.float64)
            
            # Get trading signals
            signals = self.ta_engine.get_trading_signals(high, low, close, volume)
            current_price = float(close[-1])
            
            # Analyze signals
            overall = signals.get('overall', 'NEUTRAL')
            strength = signals.get('strength', 0)
            signal_list = signals.get('signals', [])
            
            # Determine sell decision
            should_sell = overall == 'SELL' and strength >= min_signal_strength
            
            # Build reasons
            reasons = []
            if overall == 'SELL':
                sell_signals = [s for s in signal_list if s['action'] == 'SELL']
                for sig in sell_signals:
                    reasons.append(f"{sig['indicator']}: {sig['signal']} ({sig['confidence']})")
            else:
                reasons.append(f"Overall signal is {overall}, not SELL")
                if strength < min_signal_strength:
                    reasons.append(f"Signal strength {strength} < minimum {min_signal_strength}")
            
            # Determine confidence
            if strength >= 3:
                confidence = "HIGH"
            elif strength >= 2:
                confidence = "MEDIUM"
            elif strength >= 1:
                confidence = "LOW"
            else:
                confidence = "NONE"
            
            return {
                "should_sell": should_sell,
                "confidence": confidence,
                "reasons": reasons,
                "signals": signals,
                "current_price": current_price,
                "signal_strength": strength,
                "overall_direction": overall
            }
            
        except Exception as e:
            return {
                "should_sell": False,
                "confidence": "NONE",
                "reasons": [f"Error analyzing: {str(e)}"],
                "current_price": None
            }
    
    def get_quick_analysis(self, symbol: str, lookback_days: int = 30) -> Dict[str, Any]:
        """
        Get a quick technical analysis summary
        
        Args:
            symbol: Stock symbol
            lookback_days: Days of historical data
            
        Returns:
            Dictionary with key indicators and recommendation
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days + 10)
            
            bars_dict = self.data_feed.get_daily_bars(
                [symbol],
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            
            if not bars_dict or symbol not in bars_dict or not bars_dict[symbol]:
                return {"error": "No data available"}
            
            bars = bars_dict[symbol]
            
            # Extract OHLCV
            high = np.array([float(bar['high']) for bar in bars], dtype=np.float64)
            low = np.array([float(bar['low']) for bar in bars], dtype=np.float64)
            close = np.array([float(bar['close']) for bar in bars], dtype=np.float64)
            volume = np.array([float(bar['volume']) for bar in bars], dtype=np.float64)
            
            # Get comprehensive analysis
            analysis = self.ta_engine.get_comprehensive_analysis(high, low, close, volume)
            signals = self.ta_engine.get_trading_signals(high, low, close, volume)
            
            if not analysis['success']:
                return {"error": analysis.get('error', 'Analysis failed')}
            
            latest = analysis['latest']
            
            return {
                "symbol": symbol,
                "current_price": float(close[-1]),
                "recommendation": signals.get('overall', 'NEUTRAL'),
                "signal_strength": signals.get('strength', 0),
                "key_indicators": {
                    "rsi_14": latest.get('rsi_14'),
                    "macd_status": "BULLISH" if latest.get('macd', 0) > latest.get('macd_signal', 0) else "BEARISH",
                    "price_vs_sma20": "ABOVE" if close[-1] > latest.get('sma_20', close[-1]) else "BELOW",
                    "atr_14": latest.get('atr_14'),
                },
                "all_signals": signals.get('signals', [])
            }
            
        except Exception as e:
            return {"error": str(e)}


# Convenience function for quick access
def get_trading_decision_helper() -> TradingDecisionHelper:
    """Get or create TradingDecisionHelper instance"""
    return TradingDecisionHelper()


if __name__ == "__main__":
    # Test the helper
    print("Testing Technical Analysis Helper...")
    print("=" * 60)
    
    helper = get_trading_decision_helper()
    
    # Test with AAPL
    symbol = "AAPL"
    print(f"\nAnalyzing {symbol}...")
    
    # Quick analysis
    quick = helper.get_quick_analysis(symbol)
    if "error" not in quick:
        print(f"Current Price: ${quick['current_price']:.2f}")
        print(f"Recommendation: {quick['recommendation']}")
        print(f"Signal Strength: {quick['signal_strength']}")
        print(f"RSI: {quick['key_indicators']['rsi_14']:.2f}" if quick['key_indicators']['rsi_14'] else "RSI: N/A")
        print(f"MACD: {quick['key_indicators']['macd_status']}")
    
    # Buy decision
    print(f"\n{'-'*60}")
    buy_decision = helper.should_buy(symbol)
    print(f"Should BUY {symbol}? {buy_decision['should_buy']}")
    print(f"Confidence: {buy_decision['confidence']}")
    print(f"Reasons: {', '.join(buy_decision['reasons'])}")
    
    # Sell decision
    print(f"\n{'-'*60}")
    sell_decision = helper.should_sell(symbol)
    print(f"Should SELL {symbol}? {sell_decision['should_sell']}")
    print(f"Confidence: {sell_decision['confidence']}")
    print(f"Reasons: {', '.join(sell_decision['reasons'])}")
    
    print("\n" + "=" * 60)
    print("✅ Technical Analysis Helper test complete!")
