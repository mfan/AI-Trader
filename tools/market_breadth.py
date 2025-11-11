"""
Market Breadth Analysis Tool

Analyzes market internals to determine true market direction:
- Advance/Decline Ratio
- New Highs/Lows
- Up/Down Volume Ratio
- Sector Performance

Provides more accurate market regime detection than SPY alone.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import sqlite3
import os


class MarketBreadthAnalyzer:
    """Analyzes market breadth indicators for trend detection"""
    
    def __init__(self, cache_db_path: str = None, signature: str = None):
        """
        Initialize market breadth analyzer
        
        Args:
            cache_db_path: Path to SQLite cache database (optional)
            signature: Agent signature to auto-find database (e.g., 'xai-grok-4-latest')
        """
        if cache_db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # If signature provided, use agent-specific database
            if signature:
                cache_db_path = os.path.join(
                    base_dir, "data", "agent_data", signature, "momentum_cache.db"
                )
            else:
                # Try to find the most recent agent database
                agent_data_dir = os.path.join(base_dir, "data", "agent_data")
                if os.path.exists(agent_data_dir):
                    # Look for any agent with momentum_cache.db
                    agents = [d for d in os.listdir(agent_data_dir) 
                             if os.path.isdir(os.path.join(agent_data_dir, d))]
                    
                    for agent in agents:
                        test_path = os.path.join(agent_data_dir, agent, "momentum_cache.db")
                        if os.path.exists(test_path):
                            cache_db_path = test_path
                            print(f"📊 Using momentum cache from agent: {agent}")
                            break
                
                # Fallback to old location
                if cache_db_path is None or not os.path.exists(cache_db_path):
                    cache_db_path = os.path.join(base_dir, "data", "momentum_cache.db")
        
        self.cache_db_path = cache_db_path
    
    def calculate_advance_decline_ratio(
        self, 
        scan_date: Optional[str] = None
    ) -> Dict:
        """
        Calculate Advance/Decline ratio from momentum cache
        
        Uses previous day's scan data to determine how many stocks
        closed higher vs lower.
        
        Args:
            scan_date: Date to analyze (YYYY-MM-DD), defaults to latest
            
        Returns:
            Dict with:
                - advancing: Number of stocks that closed higher
                - declining: Number of stocks that closed lower
                - ratio: Advancing/Declining ratio
                - interpretation: "BULLISH", "BEARISH", or "NEUTRAL"
                - strength: 1-5 (how strong the signal is)
        """
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            # Get latest scan date if not provided
            if scan_date is None:
                cursor.execute("""
                    SELECT scan_date 
                    FROM daily_movers 
                    ORDER BY scan_date DESC 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                if not result:
                    return {
                        "error": "No scan data available",
                        "advancing": 0,
                        "declining": 0,
                        "ratio": 0,
                        "interpretation": "NEUTRAL",
                        "strength": 0
                    }
                scan_date = result[0]
            
            # Count advancing stocks (positive price change)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM daily_movers 
                WHERE scan_date = ? AND change_pct > 0
            """, (scan_date,))
            advancing = cursor.fetchone()[0]
            
            # Count declining stocks (negative price change)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM daily_movers 
                WHERE scan_date = ? AND change_pct < 0
            """, (scan_date,))
            declining = cursor.fetchone()[0]
            
            conn.close()
            
            # Calculate ratio and interpretation
            total_stocks = advancing + declining
            
            if declining == 0:
                ratio = float(advancing) if advancing > 0 else 0
            else:
                ratio = advancing / declining
            
            # Determine market interpretation
            # Ratio > 2.0 = Strong bullish (2x more advancing)
            # Ratio > 1.3 = Bullish (30%+ more advancing)
            # Ratio 0.7-1.3 = Neutral (balanced)
            # Ratio < 0.7 = Bearish (30%+ more declining)
            # Ratio < 0.5 = Strong bearish (2x more declining)
            
            if ratio > 2.0:
                interpretation = "STRONG_BULLISH"
                strength = 5
            elif ratio > 1.3:
                interpretation = "BULLISH"
                strength = 3
            elif ratio > 0.7:
                interpretation = "NEUTRAL"
                strength = 1
            elif ratio > 0.5:
                interpretation = "BEARISH"
                strength = 3
            else:
                interpretation = "STRONG_BEARISH"
                strength = 5
            
            return {
                "scan_date": scan_date,
                "advancing": advancing,
                "declining": declining,
                "unchanged": total_stocks - advancing - declining,
                "total_stocks": total_stocks,
                "ratio": round(ratio, 2),
                "percentage_advancing": round((advancing / total_stocks * 100), 1) if total_stocks > 0 else 0,
                "interpretation": interpretation,
                "strength": strength
            }
            
        except Exception as e:
            print(f"❌ Error calculating advance/decline ratio: {e}")
            return {
                "error": str(e),
                "advancing": 0,
                "declining": 0,
                "ratio": 0,
                "interpretation": "NEUTRAL",
                "strength": 0
            }
    
    def analyze_sector_breadth(
        self,
        scan_date: Optional[str] = None,
        min_stocks_per_sector: int = 3
    ) -> Dict:
        """
        Analyze which sectors are leading/lagging
        
        Args:
            scan_date: Date to analyze
            min_stocks_per_sector: Minimum stocks required for valid sector signal
            
        Returns:
            Dict with sector performance data
        """
        # TODO: Implement sector analysis when we add sector metadata
        # For now, return placeholder
        return {
            "message": "Sector breadth analysis coming soon",
            "sectors": {}
        }
    
    def get_volume_breadth(
        self,
        scan_date: Optional[str] = None
    ) -> Dict:
        """
        Calculate up/down volume ratio
        
        Analyzes volume flowing into advancing vs declining stocks.
        
        Args:
            scan_date: Date to analyze
            
        Returns:
            Dict with volume analysis
        """
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            # Get latest scan date if not provided
            if scan_date is None:
                cursor.execute("""
                    SELECT scan_date 
                    FROM daily_movers 
                    ORDER BY scan_date DESC 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                if not result:
                    return {"error": "No scan data available"}
                scan_date = result[0]
            
            # Sum volume for advancing stocks
            cursor.execute("""
                SELECT COALESCE(SUM(volume), 0)
                FROM daily_movers 
                WHERE scan_date = ? AND change_pct > 0
            """, (scan_date,))
            up_volume = cursor.fetchone()[0]
            
            # Sum volume for declining stocks
            cursor.execute("""
                SELECT COALESCE(SUM(volume), 0)
                FROM daily_movers 
                WHERE scan_date = ? AND change_pct < 0
            """, (scan_date,))
            down_volume = cursor.fetchone()[0]
            
            conn.close()
            
            # Calculate ratio
            if down_volume == 0:
                ratio = float(up_volume) if up_volume > 0 else 0
            else:
                ratio = up_volume / down_volume
            
            # Interpret volume breadth
            if ratio > 2.0:
                interpretation = "STRONG_BULLISH"
                strength = 5
            elif ratio > 1.3:
                interpretation = "BULLISH"
                strength = 3
            elif ratio > 0.7:
                interpretation = "NEUTRAL"
                strength = 1
            elif ratio > 0.5:
                interpretation = "BEARISH"
                strength = 3
            else:
                interpretation = "STRONG_BEARISH"
                strength = 5
            
            return {
                "scan_date": scan_date,
                "up_volume": up_volume,
                "down_volume": down_volume,
                "ratio": round(ratio, 2),
                "interpretation": interpretation,
                "strength": strength
            }
            
        except Exception as e:
            print(f"❌ Error calculating volume breadth: {e}")
            return {"error": str(e)}
    
    def get_comprehensive_market_regime(
        self,
        scan_date: Optional[str] = None
    ) -> Dict:
        """
        Combine multiple breadth indicators for comprehensive market regime
        
        This is the PRIMARY method to use for market regime detection.
        It combines:
        - Advance/Decline ratio
        - Volume breadth
        - Momentum distribution
        
        Args:
            scan_date: Date to analyze
            
        Returns:
            Dict with:
                - regime: "STRONG_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "STRONG_BEARISH"
                - strength: 1-5 (confidence in regime)
                - components: Individual breadth metrics
                - recommendation: Trading strategy for this regime
        """
        # Get all breadth components
        ad_ratio = self.calculate_advance_decline_ratio(scan_date)
        volume_breadth = self.get_volume_breadth(scan_date)
        
        # Average the strength scores
        strength_scores = []
        interpretations = []
        
        if not ad_ratio.get("error"):
            strength_scores.append(ad_ratio["strength"])
            interpretations.append(ad_ratio["interpretation"])
        
        if not volume_breadth.get("error"):
            strength_scores.append(volume_breadth["strength"])
            interpretations.append(volume_breadth["interpretation"])
        
        # Calculate consensus
        if not strength_scores:
            return {
                "error": "No breadth data available",
                "regime": "NEUTRAL",
                "strength": 0
            }
        
        avg_strength = sum(strength_scores) / len(strength_scores)
        
        # Determine consensus regime
        bullish_count = sum(1 for i in interpretations if "BULLISH" in i)
        bearish_count = sum(1 for i in interpretations if "BEARISH" in i)
        
        if bullish_count > bearish_count:
            if avg_strength >= 4:
                regime = "STRONG_BULLISH"
            elif avg_strength >= 2:
                regime = "BULLISH"
            else:
                regime = "NEUTRAL"
        elif bearish_count > bullish_count:
            if avg_strength >= 4:
                regime = "STRONG_BEARISH"
            elif avg_strength >= 2:
                regime = "BEARISH"
            else:
                regime = "NEUTRAL"
        else:
            regime = "NEUTRAL"
        
        # Generate trading recommendations
        recommendations = {
            "STRONG_BULLISH": "Aggressive long bias. Buy calls on momentum gainers. Hold swing positions 2-3 days.",
            "BULLISH": "Long bias. Buy calls on best setups. Scale into winners.",
            "NEUTRAL": "Selective trading. Mean reversion only. Quick in/out. Consider cash.",
            "BEARISH": "Short bias. Buy puts or inverse ETFs (SQQQ, SPXU). Scale into shorts.",
            "STRONG_BEARISH": "Aggressive short bias. Buy puts on weak stocks. Hold inverse ETF positions."
        }
        
        return {
            "scan_date": ad_ratio.get("scan_date", scan_date),
            "regime": regime,
            "strength": round(avg_strength, 1),
            "recommendation": recommendations.get(regime, "No clear direction - stay in cash"),
            "components": {
                "advance_decline": ad_ratio,
                "volume_breadth": volume_breadth
            },
            "summary": f"{regime} market with {round(avg_strength, 1)}/5 strength"
        }


# Convenience function for easy import
def get_market_regime(scan_date: Optional[str] = None) -> Dict:
    """
    Quick function to get current market regime
    
    Args:
        scan_date: Date to analyze (defaults to latest)
        
    Returns:
        Market regime analysis dict
    """
    analyzer = MarketBreadthAnalyzer()
    return analyzer.get_comprehensive_market_regime(scan_date)


if __name__ == "__main__":
    # Test market breadth analysis
    print("=" * 80)
    print("MARKET BREADTH ANALYSIS TEST")
    print("=" * 80)
    
    analyzer = MarketBreadthAnalyzer()
    
    # Test A/D ratio
    print("\n📊 Advance/Decline Ratio:")
    ad_ratio = analyzer.calculate_advance_decline_ratio()
    if not ad_ratio.get("error"):
        print(f"   Date: {ad_ratio['scan_date']}")
        print(f"   Advancing: {ad_ratio['advancing']}")
        print(f"   Declining: {ad_ratio['declining']}")
        print(f"   Ratio: {ad_ratio['ratio']}")
        print(f"   % Advancing: {ad_ratio['percentage_advancing']}%")
        print(f"   Interpretation: {ad_ratio['interpretation']} (strength: {ad_ratio['strength']}/5)")
    else:
        print(f"   Error: {ad_ratio['error']}")
    
    # Test volume breadth
    print("\n📊 Volume Breadth:")
    vol_breadth = analyzer.get_volume_breadth()
    if not vol_breadth.get("error"):
        print(f"   Date: {vol_breadth['scan_date']}")
        print(f"   Up Volume: {vol_breadth['up_volume']:,}")
        print(f"   Down Volume: {vol_breadth['down_volume']:,}")
        print(f"   Ratio: {vol_breadth['ratio']}")
        print(f"   Interpretation: {vol_breadth['interpretation']} (strength: {vol_breadth['strength']}/5)")
    else:
        print(f"   Error: {vol_breadth['error']}")
    
    # Test comprehensive regime
    print("\n🎯 Comprehensive Market Regime:")
    regime = analyzer.get_comprehensive_market_regime()
    if not regime.get("error"):
        print(f"   Date: {regime['scan_date']}")
        print(f"   Regime: {regime['regime']}")
        print(f"   Strength: {regime['strength']}/5")
        print(f"   Summary: {regime['summary']}")
        print(f"   Recommendation: {regime['recommendation']}")
    else:
        print(f"   Error: {regime['error']}")
