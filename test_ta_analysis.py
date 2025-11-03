"""
Test Technical Analysis for OKLO and CRWV
Date: November 3, 2025

This script tests the technical analysis integration using real Alpaca data.
"""

import sys
import os
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tools.alpaca_data_feed import AlpacaDataFeed
from tools.technical_indicators import get_ta_engine
import numpy as np


def analyze_stock(symbol: str, data_feed: AlpacaDataFeed, ta_engine):
    """
    Perform comprehensive technical analysis on a stock
    
    Args:
        symbol: Stock symbol to analyze
        data_feed: AlpacaDataFeed instance
        ta_engine: TechnicalAnalysis instance
    """
    print(f"\n{'='*80}")
    print(f"📊 TECHNICAL ANALYSIS: {symbol}")
    print(f"{'='*80}")
    
    # Calculate date range (30 days for newer IPOs like OKLO/CRWV)
    end_date = datetime(2025, 10, 31)  # Last trading day (Friday Oct 31st)
    start_date = end_date - timedelta(days=35)  # ~30 trading days
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    print(f"Date Range: {start_str} to {end_str}")
    print(f"Analysis Date: {end_str} (Latest Available Data)")
    print("-" * 80)
    
    try:
        # Get historical bars
        bars_dict = data_feed.get_daily_bars([symbol], start_str, end_str)
        
        if not bars_dict or symbol not in bars_dict or not bars_dict[symbol]:
            print(f"❌ No data available for {symbol}")
            return
        
        bars = bars_dict[symbol]
        print(f"✅ Retrieved {len(bars)} trading days of data")
        
        # Extract OHLCV arrays
        high = np.array([float(bar['high']) for bar in bars], dtype=np.float64)
        low = np.array([float(bar['low']) for bar in bars], dtype=np.float64)
        close = np.array([float(bar['close']) for bar in bars], dtype=np.float64)
        volume = np.array([float(bar['volume']) for bar in bars], dtype=np.float64)
        
        # Get latest bar data
        latest_bar = bars[-1]
        print(f"\n📈 Latest Price Data ({latest_bar['timestamp']}):")
        print(f"   Open:   ${float(latest_bar['open']):.2f}")
        print(f"   High:   ${float(latest_bar['high']):.2f}")
        print(f"   Low:    ${float(latest_bar['low']):.2f}")
        print(f"   Close:  ${float(latest_bar['close']):.2f}")
        print(f"   Volume: {latest_bar['volume']:,}")
        if latest_bar.get('vwap'):
            print(f"   VWAP:   ${float(latest_bar['vwap']):.2f}")
        
        # Calculate comprehensive technical analysis
        print(f"\n🔬 Calculating Technical Indicators...")
        analysis = ta_engine.get_comprehensive_analysis(high, low, close, volume)
        
        if not analysis['success']:
            print(f"❌ Failed to calculate indicators: {analysis.get('error', 'Unknown error')}")
            return
        
        # Display indicators
        latest = analysis['latest']
        print(f"\n📊 TECHNICAL INDICATORS:")
        print(f"\n   Trend Indicators:")
        print(f"      SMA(20):  ${latest.get('sma_20'):.2f}" if latest.get('sma_20') else "      SMA(20):  N/A")
        print(f"      SMA(50):  ${latest.get('sma_50'):.2f}" if latest.get('sma_50') else "      SMA(50):  N/A (need more data)")
        print(f"      EMA(12):  ${latest.get('ema_12'):.2f}" if latest.get('ema_12') else "      EMA(12):  N/A")
        print(f"      EMA(26):  ${latest.get('ema_26'):.2f}" if latest.get('ema_26') else "      EMA(26):  N/A")
        
        print(f"\n   MACD:")
        macd_val = latest.get('macd')
        signal_val = latest.get('macd_signal')
        hist_val = latest.get('macd_hist')
        
        print(f"      MACD:       {macd_val:.4f}" if macd_val else "      MACD:       N/A")
        print(f"      Signal:     {signal_val:.4f}" if signal_val else "      Signal:     N/A")
        print(f"      Histogram:  {hist_val:.4f}" if hist_val else "      Histogram:  N/A")
        
        if macd_val and signal_val:
            if macd_val > signal_val:
                print(f"      Status: ✅ BULLISH (MACD > Signal)")
            else:
                print(f"      Status: ⚠️  BEARISH (MACD < Signal)")
        
        print(f"\n   Momentum Indicators:")
        rsi = latest.get('rsi_14')
        print(f"      RSI(14):    {rsi:.2f}" if rsi else "      RSI(14):    N/A")
        if rsi:
            if rsi < 30:
                print(f"                  🟢 OVERSOLD - Strong BUY signal")
            elif rsi > 70:
                print(f"                  🔴 OVERBOUGHT - Strong SELL signal")
            elif rsi < 40:
                print(f"                  🟡 Weak - Potential BUY")
            elif rsi > 60:
                print(f"                  🟡 Strong - Potential SELL")
            else:
                print(f"                  ⚪ NEUTRAL")
        
        stoch_k = latest.get('stoch_k')
        stoch_d = latest.get('stoch_d')
        print(f"      Stoch %K:   {stoch_k:.2f}" if stoch_k else "      Stoch %K:   N/A")
        print(f"      Stoch %D:   {stoch_d:.2f}" if stoch_d else "      Stoch %D:   N/A")
        
        cci = latest.get('cci_20')
        print(f"      CCI(20):    {cci:.2f}" if cci else "      CCI(20):    N/A")
        
        print(f"\n   Volatility Indicators:")
        bb_upper = latest.get('bb_upper')
        bb_middle = latest.get('bb_middle')
        bb_lower = latest.get('bb_lower')
        current_price = close[-1]
        
        if bb_upper and bb_middle and bb_lower:
            print(f"      BB Upper:   ${bb_upper:.2f}")
            print(f"      BB Middle:  ${bb_middle:.2f}")
            print(f"      BB Lower:   ${bb_lower:.2f}")
            print(f"      Current:    ${current_price:.2f}")
            
            bb_range = bb_upper - bb_lower
            position_in_band = ((current_price - bb_lower) / bb_range) * 100 if bb_range > 0 else 50
            print(f"      Position:   {position_in_band:.1f}% in band")
            
            if current_price >= bb_upper:
                print(f"                  🔴 At/Above Upper Band - SELL signal")
            elif current_price <= bb_lower:
                print(f"                  🟢 At/Below Lower Band - BUY signal")
        
        atr = latest.get('atr_14')
        print(f"      ATR(14):    ${atr:.2f}" if atr else "      ATR(14):    N/A")
        if atr and current_price:
            atr_percent = (atr / current_price) * 100
            print(f"                  ({atr_percent:.2f}% of price)")
        
        print(f"\n   Trend Strength:")
        adx = latest.get('adx_14')
        print(f"      ADX(14):    {adx:.2f}" if adx else "      ADX(14):    N/A")
        if adx:
            if adx > 25:
                print(f"                  🔥 STRONG TREND")
            elif adx > 20:
                print(f"                  📈 MODERATE TREND")
            else:
                print(f"                  💤 WEAK/NO TREND")
        
        print(f"\n   Volume Indicators:")
        obv = latest.get('obv')
        vwap = latest.get('vwap')
        print(f"      OBV:        {obv:,.0f}" if obv else "      OBV:        N/A")
        print(f"      VWAP:       ${vwap:.2f}" if vwap else "      VWAP:       N/A")
        if vwap and current_price:
            if current_price > vwap:
                print(f"                  ✅ Price above VWAP (Bullish)")
            else:
                print(f"                  ⚠️  Price below VWAP (Bearish)")
        
        # Generate trading signals
        print(f"\n{'='*80}")
        print(f"🎯 TRADING SIGNALS FOR {symbol}")
        print(f"{'='*80}")
        
        signals = ta_engine.get_trading_signals(high, low, close, volume)
        
        overall = signals.get('overall', 'NEUTRAL')
        strength = signals.get('strength', 0)
        
        # Display overall recommendation
        print(f"\n🔔 OVERALL RECOMMENDATION: ", end="")
        if overall == 'BUY':
            print(f"🟢 BUY (Strength: {strength})")
        elif overall == 'SELL':
            print(f"🔴 SELL (Strength: {strength})")
        else:
            print(f"⚪ NEUTRAL (Strength: {strength})")
        
        # Display individual signals
        signal_list = signals.get('signals', [])
        if signal_list:
            print(f"\n📋 Individual Signals ({len(signal_list)} total):")
            
            buy_signals = [s for s in signal_list if s['action'] == 'BUY']
            sell_signals = [s for s in signal_list if s['action'] == 'SELL']
            
            if buy_signals:
                print(f"\n   🟢 BUY Signals:")
                for signal in buy_signals:
                    conf_icon = "⭐" if signal['confidence'] == 'HIGH' else "⚡"
                    print(f"      {conf_icon} {signal['indicator']}: {signal['signal']}")
                    print(f"         Value: {signal['value']}")
                    print(f"         Confidence: {signal['confidence']}")
            
            if sell_signals:
                print(f"\n   🔴 SELL Signals:")
                for signal in sell_signals:
                    conf_icon = "⭐" if signal['confidence'] == 'HIGH' else "⚡"
                    print(f"      {conf_icon} {signal['indicator']}: {signal['signal']}")
                    print(f"         Value: {signal['value']}")
                    print(f"         Confidence: {signal['confidence']}")
        else:
            print(f"\n   ⚪ No strong signals detected - Market in neutral zone")
        
        # Trading recommendation
        print(f"\n{'='*80}")
        print(f"💡 RECOMMENDATION FOR TOMORROW (11/3/2025):")
        print(f"{'='*80}")
        
        if overall == 'BUY' and strength >= 2:
            print(f"   ✅ STRONG BUY - Consider opening/adding to position")
            print(f"   📍 Entry: Around current price ${current_price:.2f}")
            if atr:
                stop_loss = current_price - (atr * 2)
                take_profit = current_price + (atr * 3)
                print(f"   🛑 Stop Loss: ${stop_loss:.2f} (2x ATR)")
                print(f"   🎯 Take Profit: ${take_profit:.2f} (3x ATR)")
        elif overall == 'BUY' and strength == 1:
            print(f"   🟡 MODERATE BUY - Watch for confirmation")
            print(f"   📍 Consider small position or wait for stronger signals")
        elif overall == 'SELL' and strength >= 2:
            print(f"   ⛔ STRONG SELL - Consider closing/reducing position")
            print(f"   📍 Exit: Around current price ${current_price:.2f}")
        elif overall == 'SELL' and strength == 1:
            print(f"   🟡 MODERATE SELL - Watch for confirmation")
            print(f"   📍 Consider taking partial profits or tightening stops")
        else:
            print(f"   ⚪ HOLD/WAIT - No clear directional bias")
            print(f"   📍 Wait for clearer signals before entering")
            print(f"   📍 Use this time to monitor and prepare watchlist")
        
        print(f"\n")
        
    except Exception as e:
        print(f"\n❌ Error analyzing {symbol}: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Main test function"""
    print("="*80)
    print("🧪 TECHNICAL ANALYSIS TEST")
    print("Testing TA-Lib integration with Alpaca Data Feed")
    print("="*80)
    print(f"Analysis Date: October 31, 2025 (Last Trading Day)")
    # Using OKLO and CRWV - newer IPOs with limited history
    symbols_to_test = ["OKLO", "CRWV"]  
    print(f"Symbols: {', '.join(symbols_to_test)}")
    print(f"Lookback Period: All available data (may be limited for new IPOs)")
    print("="*80)
    
    # Initialize components
    print("\n🔧 Initializing components...")
    data_feed = AlpacaDataFeed()
    ta_engine = get_ta_engine()
    print(f"✅ Alpaca Data Feed initialized")
    print(f"✅ TA-Lib Engine initialized (v{ta_engine.version})")
    
    # Analyze each symbol
    for symbol in symbols_to_test:
        analyze_stock(symbol, data_feed, ta_engine)
    
    # Summary
    print("="*80)
    print("✅ TECHNICAL ANALYSIS COMPLETE")
    print("="*80)
    print("\nNext Steps:")
    print("  1. Review the technical indicators and signals above")
    print("  2. Cross-reference with fundamental analysis if available")
    print("  3. Consider market conditions and news events")
    print("  4. Set appropriate stop-loss and take-profit levels")
    print("  5. Use proper position sizing based on risk tolerance")
    print("\n⚠️  DISCLAIMER: This is for educational purposes only.")
    print("   Always do your own research before trading.")
    print("="*80)


if __name__ == "__main__":
    main()
