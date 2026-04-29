"""
BaseAgent class - Base class for trading agents
Encapsulates core functionality including MCP tool management, AI agent creation, and trading execution
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from dotenv import load_dotenv

# Import project tools
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tools.general_tools import extract_conversation, extract_tool_messages, get_config_value, write_config_value
from tools.deepseek_reasoning_patch import apply_deepseek_reasoning_patch, extract_reasoning_content
# REMOVED: from tools.price_tools import add_no_trade_record  # No longer needed - Alpaca manages positions
from prompts.agent_prompt import get_agent_system_prompt, STOP_SIGNAL

# Load environment variables
load_dotenv()

# Apply DeepSeek Reasoner patch early - before any LLM calls
# This preserves reasoning_content through LangChain's message conversion,
# which is required by DeepSeek's API for multi-turn conversations.
# Safe for non-DeepSeek models (no-op when reasoning_content is absent).
apply_deepseek_reasoning_patch()


class BaseAgent:
    """
    Base class for trading agents
    
    Main functionalities:
    1. MCP tool management and connection
    2. AI agent creation and configuration
    3. Trading execution and decision loops
    4. Logging and management
    5. Position and configuration management
    """
    
    # Default NASDAQ 100 stock symbols
    DEFAULT_STOCK_SYMBOLS = [
        "NVDA", "MSFT", "AAPL", "GOOG", "GOOGL", "AMZN", "META", "AVGO", "TSLA",
        "NFLX", "PLTR", "COST", "ASML", "AMD", "CSCO", "AZN", "TMUS", "MU", "LIN",
        "PEP", "SHOP", "APP", "INTU", "AMAT", "LRCX", "PDD", "QCOM", "ARM", "INTC",
        "BKNG", "AMGN", "TXN", "ISRG", "GILD", "KLAC", "PANW", "ADBE", "HON",
        "CRWD", "CEG", "ADI", "ADP", "DASH", "CMCSA", "VRTX", "MELI", "SBUX",
        "CDNS", "ORLY", "SNPS", "MSTR", "MDLZ", "ABNB", "MRVL", "CTAS", "TRI",
        "MAR", "MNST", "CSX", "ADSK", "PYPL", "FTNT", "AEP", "WDAY", "REGN", "ROP",
        "NXPI", "DDOG", "AXON", "ROST", "IDXX", "EA", "PCAR", "FAST", "EXC", "TTWO",
        "XEL", "ZS", "PAYX", "WBD", "BKR", "CPRT", "CCEP", "FANG", "TEAM", "CHTR",
        "KDP", "MCHP", "GEHC", "VRSK", "CTSH", "CSGP", "KHC", "ODFL", "DXCM", "TTD",
        "ON", "BIIB", "LULU", "CDW", "GFS"
    ]
    
    def __init__(
        self,
        signature: str,
        basemodel: str,
        stock_symbols: Optional[List[str]] = None,
        mcp_config: Optional[Dict[str, Dict[str, Any]]] = None,
        log_path: Optional[str] = None,
        max_steps: int = 10,
        max_retries: int = 3,
        base_delay: float = 0.5,
        openai_base_url: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        initial_cash: float = 10000.0,
        init_date: str = "2025-10-13"
    ):
        """
        Initialize BaseAgent
        
        Args:
            signature: Agent signature/name
            basemodel: Base model name
            stock_symbols: List of stock symbols, defaults to NASDAQ 100
            mcp_config: MCP tool configuration, including port and URL information
            log_path: Log path, defaults to ./data/agent_data
            max_steps: Maximum reasoning steps
            max_retries: Maximum retry attempts
            base_delay: Base delay time for retries
            openai_base_url: OpenAI API base URL
            openai_api_key: OpenAI API key
            initial_cash: Initial cash amount
            init_date: Initialization date
        """
        self.signature = signature
        self.basemodel = basemodel
        self.stock_symbols = stock_symbols or self.DEFAULT_STOCK_SYMBOLS
        self.max_steps = max_steps
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.initial_cash = initial_cash
        self.init_date = init_date
        
        # Set MCP configuration
        self.mcp_config = mcp_config or self._get_default_mcp_config()
        
        # Set log path
        self.base_log_path = log_path or "./data/agent_data"
        
        # Set OpenAI/DeepSeek/XAI configuration with smart fallback
        if openai_base_url is None:
            # Check model type and use appropriate API
            if "deepseek" in basemodel.lower():
                self.openai_base_url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
                print(f"🧠 Using DeepSeek API: {self.openai_base_url}")
            elif "grok" in basemodel.lower() or "xai" in basemodel.lower():
                self.openai_base_url = os.getenv("XAI_API_BASE", "https://api.x.ai/v1")
                print(f"🤖 Using XAI Grok API: {self.openai_base_url}")
            else:
                self.openai_base_url = os.getenv("OPENAI_API_BASE")
                print(f"🤖 Using OpenAI API: {self.openai_base_url}")
        else:
            self.openai_base_url = openai_base_url
            
        if openai_api_key is None:
            # Check model type and use appropriate API key
            if "deepseek" in basemodel.lower():
                self.openai_api_key = os.getenv("DEEPSEEK_API_KEY")
                if self.openai_api_key:
                    print(f"✅ DeepSeek API key loaded from environment")
                else:
                    print(f"⚠️  Warning: DEEPSEEK_API_KEY not found in environment")
            elif "grok" in basemodel.lower() or "xai" in basemodel.lower():
                self.openai_api_key = os.getenv("XAI_API_KEY")
                if self.openai_api_key:
                    print(f"✅ XAI Grok API key loaded from environment")
                else:
                    print(f"⚠️  Warning: XAI_API_KEY not found in environment")
            else:
                self.openai_api_key = os.getenv("OPENAI_API_KEY")
                if self.openai_api_key:
                    print(f"✅ OpenAI API key loaded from environment")
                else:
                    print(f"⚠️  Warning: OPENAI_API_KEY not found in environment")
        else:
            self.openai_api_key = openai_api_key
        
        # Initialize components
        self.client: Optional[MultiServerMCPClient] = None
        self.tools: Optional[List] = None
        self.tool_lookup: Dict[str, Any] = {}
        self.model: Optional[ChatOpenAI] = None
        self.agent: Optional[Any] = None
        
        # Data paths (for logging only, NOT for position tracking)
        self.data_path = os.path.join(self.base_log_path, self.signature)
        # Note: We no longer use position.jsonl - all positions managed by Alpaca
        
    def _get_default_mcp_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Get default MCP configuration with Alpaca integration
        
        Uses Alpaca official MCP server for all data and trading operations.
        Provides 60+ tools for stocks, options, crypto trading and real-time market data.
        All portfolio calculations (positions, P&L, balances) handled by Alpaca.
        """
        print("🚀 Using Alpaca MCP integration (Data + Trade)")
        return {
            "alpaca_data": {
                "transport": "streamable_http",
                "url": f"http://localhost:{os.getenv('ALPACA_DATA_HTTP_PORT', '8004')}/mcp",
            },
            "alpaca_trade": {
                "transport": "streamable_http",
                "url": f"http://localhost:{os.getenv('ALPACA_TRADE_HTTP_PORT', '8005')}/mcp",
            },
        }
    
    async def initialize(self) -> None:
        """Initialize MCP client and AI model"""
        print(f"🚀 Initializing agent: {self.signature}")
        
        try:
            # Create MCP client
            self.client = MultiServerMCPClient(self.mcp_config)
            
            # Get tools
            self.tools = await self.client.get_tools()
            self.tool_lookup = {tool.name: tool for tool in self.tools}

            if "get_company_info" in self.tool_lookup:
                self.tools = [tool for tool in self.tools if tool.name != "get_company_info"]
                self.tool_lookup.pop("get_company_info", None)
                print("ℹ️ Removed unsupported get_company_info tool; using search_news for company updates")

            print(f"✅ Loaded {len(self.tools)} MCP tools")
            
            # Create AI model - do this BEFORE any potential tool failures
            if self.model is None:  # Only create if not already created
                # Determine model type for logging
                if "grok" in self.basemodel.lower() or "xai" in self.basemodel.lower():
                    model_type = "XAI Grok"
                elif "deepseek" in self.basemodel.lower():
                    model_type = "DeepSeek"
                elif "gpt" in self.basemodel.lower():
                    model_type = "OpenAI"
                else:
                    model_type = "Custom"
                
                print(f"🧠 Using {model_type} API: {self.openai_base_url}")
                if self.openai_api_key:
                    print(f"✅ {model_type} API key loaded from environment")
                else:
                    print("⚠️  No API key found - may use default")
                    
                self.model = ChatOpenAI(
                    model=self.basemodel,
                    base_url=self.openai_base_url,
                    api_key=self.openai_api_key,
                    max_retries=3,
                    timeout=120  # Increased from 30s for Grok-4-latest (handles complex prompts)
                )
                print(f"✅ AI model initialized: {self.basemodel} ({model_type})")
            
            # Note: agent will be created in run_trading_session() based on specific date
            # because system_prompt needs the current date and price information
            
            print(f"✅ Agent {self.signature} initialization completed")
            
        except Exception as e:
            print(f"❌ Error during initialization: {e}")
            # Ensure model is created even if MCP tools fail
            if self.model is None:
                print("⚠️  MCP tools failed but creating AI model anyway...")
                self.model = ChatOpenAI(
                    model=self.basemodel,
                    base_url=self.openai_base_url,
                    api_key=self.openai_api_key,
                    max_retries=3,
                    timeout=120  # Increased from 30s for Grok-4-latest (handles complex prompts)
                )
                print(f"✅ AI model initialized: {self.basemodel}")
            raise  # Re-raise to let caller handle the error
    
    def _setup_logging(self, today_date: str) -> str:
        """Set up log file path"""
        log_path = os.path.join(self.base_log_path, self.signature, 'log', today_date)
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        return os.path.join(log_path, "log.jsonl")

    def _normalize_tool_output(self, result: Any) -> Any:
        """Normalize MCP tool output into Python primitives"""
        if result is None:
            return None
        if hasattr(result, "model_dump"):
            result = result.model_dump()
        elif hasattr(result, "dict"):
            result = result.dict()
        if isinstance(result, str):
            text = result.strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return result

    async def _call_mcp_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Safely call an MCP tool if available"""
        if not self.tool_lookup:
            return None
        tool = self.tool_lookup.get(tool_name)
        if tool is None:
            print(f"⚠️ MCP tool '{tool_name}' not available")
            return None
        arguments = arguments or {}
        try:
            raw = await tool.ainvoke(arguments)
        except TypeError as err:
            if "not callable" in str(err) and hasattr(tool, "arun"):
                try:
                    raw = await tool.arun(**arguments)
                except Exception as inner_exc:
                    print(f"❌ Error calling MCP tool '{tool_name}': {inner_exc}")
                    return None
            else:
                print(f"❌ Error calling MCP tool '{tool_name}': {err}")
                return None
        except Exception as exc:
            print(f"❌ Error calling MCP tool '{tool_name}': {exc}")
            return None
        return self._normalize_tool_output(raw)

    @staticmethod
    def _format_json_block(data: Any) -> str:
        if data is None:
            return "No data available."
        if isinstance(data, str):
            return data
        try:
            return json.dumps(data, indent=2)
        except TypeError:
            return str(data)

    async def _scan_market_opportunities(self, today_date: str, top_n: int = 15) -> str:
        """
        Scan ETFs for mean reversion opportunities (v3.0 Strategy).
        
        Checks for:
        - Price deviation from VWAP (>0.3% for standard, >0.5% for leveraged)
        - RSI extremes (<30 oversold, >70 overbought)
        
        Args:
            today_date: Current trading date
            top_n: Number of top opportunities to return (default: 15)
            
        Returns:
            Formatted string with market breadth and ETF scan results
        """
        print(f"\n{'='*80}")
        print(f"🔍 SCANNING ETFs FOR MEAN REVERSION SETUPS (v3.0 Strategy)")
        print(f"{'='*80}")
        print(f"📊 Analyzing {len(self.stock_symbols)} ETFs...")
        
        # Get market breadth analysis first (CRITICAL for regime determination)
        from tools.market_breadth import MarketBreadthAnalyzer
        breadth_analyzer = MarketBreadthAnalyzer()
        market_regime = breadth_analyzer.get_comprehensive_market_regime()
        
        print(f"\n📊 MARKET BREADTH ANALYSIS:")
        if not market_regime.get("error"):
            print(f"   Regime: {market_regime['regime']}")
            print(f"   Strength: {market_regime['strength']}/5")
            ad_data = market_regime['components']['advance_decline']
            print(f"   A/D Ratio: {ad_data['ratio']} ({ad_data['advancing']} up, {ad_data['declining']} down)")
            print(f"   Recommendation: {market_regime['recommendation']}")
        else:
            print(f"   ⚠️  Market breadth unavailable: {market_regime.get('error')}")
        
        # Define leveraged ETFs (need wider thresholds)
        leveraged_etfs = {"TQQQ", "SQQQ", "SPXL", "SPXS", "UPRO", "SPXU", "SOXL", "SOXS", "TNA", "TZA"}
        
        # Define leveraged bull/bear ETFs for trend filter
        leveraged_bulls = {"TQQQ", "SPXL", "UPRO", "SOXL", "TNA"}
        leveraged_bears = {"SQQQ", "SPXS", "SPXU", "SOXS", "TZA"}
        
        # Calculate date range (last 30 days for TA)
        end_date = datetime.strptime(today_date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=30)
        start_str = start_date.strftime("%Y-%m-%d")
        
        # TREND FILTER: Get SPY's SMA(20) to determine market trend
        spy_uptrend = None
        try:
            spy_bars_result = await self._call_mcp_tool(
                "get_stock_bars",
                arguments={
                    "symbol": "SPY",
                    "start_date": start_str,
                    "end_date": today_date,
                    "timeframe": "1Day"
                }
            )
            spy_sma_result = await self._call_mcp_tool(
                "get_technical_indicators",
                arguments={
                    "symbol": "SPY",
                    "start_date": start_str,
                    "end_date": today_date,
                    "indicators": ["sma"]
                }
            )
            
            if spy_bars_result and spy_sma_result:
                spy_bars = spy_bars_result.get("bars", [])
                spy_latest = spy_sma_result.get("latest_values", {})
                spy_sma20 = spy_latest.get("sma_20")
                
                if spy_bars and spy_sma20:
                    spy_close = float(spy_bars[-1].get("close", 0))
                    spy_uptrend = spy_close > spy_sma20
                    trend_status = "UPTREND" if spy_uptrend else "DOWNTREND"
                    print(f"\n📈 TREND FILTER: SPY ${spy_close:.2f} vs SMA(20) ${spy_sma20:.2f} → {trend_status}")
                    if spy_uptrend:
                        print(f"   ⚠️  Will SKIP shorting leveraged bulls: {', '.join(leveraged_bulls)}")
                    else:
                        print(f"   ⚠️  Will SKIP shorting leveraged bears: {', '.join(leveraged_bears)}")
        except Exception as e:
            print(f"   ⚠️  Trend filter unavailable: {e}")
        
        opportunities = []
        scanned_count = 0
        error_count = 0
        
        # Scan all ETFs for VWAP + RSI setups
        for symbol in self.stock_symbols:
            try:
                scanned_count += 1
                if scanned_count % 5 == 0:
                    print(f"   ⏳ Scanned {scanned_count}/{len(self.stock_symbols)} ETFs...")
                
                # Get bars with VWAP (using 1Min for intraday precision)
                bars_result = await self._call_mcp_tool(
                    "get_stock_bars",
                    arguments={
                        "symbol": symbol,
                        "start_date": start_str,
                        "end_date": today_date,
                        "timeframe": "1Day"
                    }
                )
                
                if not bars_result or not isinstance(bars_result, dict):
                    continue
                    
                bars = bars_result.get("bars", [])
                if not bars or len(bars) < 5:
                    continue
                
                # Get latest bar with VWAP
                latest_bar = bars[-1]
                current_price = float(latest_bar.get("close", 0))
                vwap = float(latest_bar.get("vwap", 0)) if latest_bar.get("vwap") else None
                
                if not vwap or vwap == 0:
                    continue
                
                # Calculate VWAP deviation
                vwap_deviation = ((current_price - vwap) / vwap) * 100
                
                # Get RSI and Stochastic from technical indicators
                indicators_result = await self._call_mcp_tool(
                    "get_technical_indicators",
                    arguments={
                        "symbol": symbol,
                        "start_date": start_str,
                        "end_date": today_date,
                        "indicators": ["rsi", "stochastic"]
                    }
                )
                
                rsi = None
                stoch_k = None
                if indicators_result and isinstance(indicators_result, dict):
                    latest_values = indicators_result.get("latest_values", {})
                    rsi = latest_values.get("rsi_14")
                    stoch_k = latest_values.get("stoch_k")
                
                if rsi is None and stoch_k is None:
                    continue
                
                # Determine thresholds based on ETF type
                is_leveraged = symbol in leveraged_etfs
                vwap_threshold = 0.5 if is_leveraged else 0.25  # v3.0: Relaxed to 0.25% for more opportunities
                
                # Check for mean reversion setup
                signal = None
                strength = 0
                momentum_signal = None
                
                # Determine if momentum is oversold or overbought (RSI OR Stochastic)
                is_oversold = (rsi is not None and rsi < 30) or (stoch_k is not None and stoch_k < 20)
                is_overbought = (rsi is not None and rsi > 70) or (stoch_k is not None and stoch_k > 80)
                
                # LONG setup: Price below VWAP + oversold momentum (RSI OR Stochastic)
                if vwap_deviation < -vwap_threshold and is_oversold:
                    signal = "BUY"
                    # Calculate strength based on how extreme the signals are
                    if rsi is not None and rsi < 20:
                        strength = 3
                        momentum_signal = f"RSI={rsi:.1f}"
                    elif stoch_k is not None and stoch_k < 10:
                        strength = 3
                        momentum_signal = f"Stoch={stoch_k:.1f}"
                    else:
                        strength = 2
                        if rsi is not None and rsi < 30:
                            momentum_signal = f"RSI={rsi:.1f}"
                        elif stoch_k is not None:
                            momentum_signal = f"Stoch={stoch_k:.1f}"
                    if abs(vwap_deviation) > vwap_threshold * 2:
                        strength += 1  # Bonus for large deviation
                
                # SHORT setup: Price above VWAP + overbought momentum (RSI OR Stochastic)
                elif vwap_deviation > vwap_threshold and is_overbought:
                    # TREND FILTER: Don't short leveraged bulls in uptrend, or leveraged bears in downtrend
                    skip_short = False
                    skip_reason = None
                    
                    if spy_uptrend is not None:
                        if spy_uptrend and symbol in leveraged_bulls:
                            skip_short = True
                            skip_reason = f"SPY uptrend - skip shorting bull ETF"
                        elif not spy_uptrend and symbol in leveraged_bears:
                            skip_short = True
                            skip_reason = f"SPY downtrend - skip shorting bear ETF"
                    
                    if skip_short:
                        # Log but don't create signal
                        print(f"   ⚠️  {symbol}: {skip_reason} (Stoch={stoch_k:.1f if stoch_k else 'N/A'}, VWAP={vwap_deviation:+.2f}%)")
                    else:
                        signal = "SELL"
                        # Calculate strength based on how extreme the signals are
                        if rsi is not None and rsi > 80:
                            strength = 3
                            momentum_signal = f"RSI={rsi:.1f}"
                        elif stoch_k is not None and stoch_k > 90:
                            strength = 3
                            momentum_signal = f"Stoch={stoch_k:.1f}"
                        else:
                            strength = 2
                            if rsi is not None and rsi > 70:
                                momentum_signal = f"RSI={rsi:.1f}"
                            elif stoch_k is not None:
                                momentum_signal = f"Stoch={stoch_k:.1f}"
                        if abs(vwap_deviation) > vwap_threshold * 2:
                            strength += 1  # Bonus for large deviation
                
                if signal and strength >= 2:
                    etf_type = "3x Leveraged" if is_leveraged else "Standard"
                    opportunities.append({
                        "symbol": symbol,
                        "signal": signal,
                        "strength": strength,
                        "price": current_price,
                        "vwap": vwap,
                        "vwap_deviation": f"{vwap_deviation:+.2f}%",
                        "rsi": round(rsi, 1) if rsi else None,
                        "stoch_k": round(stoch_k, 1) if stoch_k else None,
                        "momentum_signal": momentum_signal,
                        "etf_type": etf_type,
                        "stop_pct": "0.3%" if is_leveraged else "0.5%"
                    })
                
            except Exception as e:
                error_count += 1
                if error_count <= 5:  # Only log first 5 errors
                    print(f"   ⚠️  Error scanning {symbol}: {str(e)[:80]}")
                continue
        
        print(f"\n✅ ETF scan complete:")
        print(f"   📊 Scanned: {scanned_count} ETFs")
        print(f"   🎯 Found: {len(opportunities)} mean reversion setups")
        if error_count > 0:
            print(f"   ⚠️  Errors: {error_count} (ETFs skipped)")
        
        # Sort by signal strength (highest first)
        opportunities.sort(key=lambda x: x["strength"], reverse=True)
        
        # Format market breadth first (CRITICAL - agent needs this for regime determination)
        breadth_lines = ["\n📊 MARKET BREADTH ANALYSIS (Yesterday's Close):"]
        breadth_lines.append("="*80)
        
        if not market_regime.get("error"):
            ad_data = market_regime['components']['advance_decline']
            vol_data = market_regime['components']['volume_breadth']
            
            breadth_lines.append(f"\n🎯 MARKET REGIME: {market_regime['regime']}")
            breadth_lines.append(f"   Confidence: {market_regime['strength']}/5")
            breadth_lines.append(f"\n📈 Advance/Decline:")
            breadth_lines.append(f"   • Advancing: {ad_data['advancing']} stocks ({ad_data['percentage_advancing']}%)")
            breadth_lines.append(f"   • Declining: {ad_data['declining']} stocks")
            breadth_lines.append(f"   • A/D Ratio: {ad_data['ratio']} ({ad_data['interpretation']})")
            breadth_lines.append(f"\n📊 Volume Flow:")
            breadth_lines.append(f"   • Up Volume: {vol_data['up_volume']:,}")
            breadth_lines.append(f"   • Down Volume: {vol_data['down_volume']:,}")
            breadth_lines.append(f"   • Volume Ratio: {vol_data['ratio']} ({vol_data['interpretation']})")
            breadth_lines.append(f"\n💡 TRADING STRATEGY:")
            breadth_lines.append(f"   {market_regime['recommendation']}")
            breadth_lines.append("\n" + "="*80)
        else:
            breadth_lines.append(f"⚠️  Market breadth data unavailable")
            breadth_lines.append("="*80)
        
        # Format top opportunities
        if len(opportunities) == 0:
            opp_lines = [
                f"\n🔍 MARKET SCAN RESULTS:",
                f"No A+ or B setups found (strength ≥2).",
                f"Current market may be ranging or lacks clear signals.",
                f"Consider waiting for better setups or use get_trading_signals() for individual stocks.",
                ""
            ]
        else:
            opp_lines = [f"\n🎯 TOP {min(top_n, len(opportunities))} MEAN REVERSION SETUPS:"]
            opp_lines.append("="*80)
            
            for i, opp in enumerate(opportunities[:top_n], 1):
                signal_emoji = "🟢" if opp["signal"] == "BUY" else "🔴" if opp["signal"] == "SELL" else "⚪"
                opp_lines.append(f"\n#{i} {signal_emoji} {opp['symbol']} - {opp['signal']} (Strength: {opp['strength']})")
                opp_lines.append(f"   Price: ${opp['price']:.2f} | VWAP: ${opp['vwap']:.2f} | Deviation: {opp['vwap_deviation']}")
                opp_lines.append(f"   RSI: {opp['rsi']} | Type: {opp['etf_type']} | Stop: {opp['stop_pct']}")
            
            if len(opportunities) > top_n:
                opp_lines.append(f"\n... and {len(opportunities) - top_n} more opportunities available")
            
            opp_lines.append("\n" + "="*80)
        
        # Combine breadth analysis with opportunities
        return "\n".join(breadth_lines + opp_lines)
    
    async def _prefetch_portfolio_context(self) -> str:
        """Gather mandatory portfolio context before trading"""
        context_lines: List[str] = []
        
        print(f"\n{'='*80}")
        print(f"📊 FETCHING PORTFOLIO CONTEXT")
        print(f"{'='*80}")

        # Step 1: Portfolio Summary
        print("🔍 Step 1: Fetching portfolio summary...")
        portfolio_summary = await self._call_mcp_tool("get_portfolio_summary")
        if portfolio_summary:
            context_lines.append("Step 1 – get_portfolio_summary():")
            context_lines.append(self._format_json_block(portfolio_summary))
            print(f"✅ Portfolio summary retrieved")
        else:
            context_lines.append("Step 1 – get_portfolio_summary(): failed (no data)")
            print(f"⚠️  Portfolio summary failed")

        # Step 2: Account Info
        print("🔍 Step 2: Fetching account information...")
        account_info = await self._call_mcp_tool("get_account_info")
        if account_info:
            context_lines.append("\nStep 2 – get_account_info():")
            context_lines.append(self._format_json_block(account_info))
            print(f"✅ Account info retrieved")
            if isinstance(account_info, dict):
                print(f"   💰 Buying Power: ${account_info.get('buying_power', 'N/A')}")
                print(f"   💵 Cash: ${account_info.get('cash', 'N/A')}")
                print(f"   📈 Portfolio Value: ${account_info.get('portfolio_value', 'N/A')}")
        else:
            context_lines.append("\nStep 2 – get_account_info(): failed (no data)")
            print(f"⚠️  Account info failed")

        # Step 3: Current Positions
        print("🔍 Step 3: Fetching current positions...")
        positions_data = await self._call_mcp_tool("get_positions")
        position_symbols: List[str] = []
        if positions_data:
            context_lines.append("\nStep 3 – get_positions():")
            context_lines.append(self._format_json_block(positions_data))
            if isinstance(positions_data, dict):
                raw_positions = positions_data.get("positions")
                if isinstance(raw_positions, dict):
                    position_symbols = list(raw_positions.keys())
                    print(f"✅ Current positions retrieved: {len(position_symbols)} positions")
                    for symbol in position_symbols[:10]:  # Show first 10
                        pos_data = raw_positions.get(symbol, {})
                        qty = pos_data.get('qty', 0)
                        print(f"   📍 {symbol}: {qty} shares")
                    if len(position_symbols) > 10:
                        print(f"   ... and {len(position_symbols) - 10} more positions")
        else:
            context_lines.append("\nStep 3 – get_positions(): failed (no data)")
            print(f"⚠️  Positions data failed")

        # Step 4: Focus on TA
        context_lines.append("\nStep 4 – Using technical analysis for trading decisions")
        print(f"ℹ️  Step 4: Technical analysis mode active")

        context_lines.append("\nUse this context to decide holds/trims/exits and complete the workflow.")
        print(f"{'='*80}\n")
        
        return "\n".join(context_lines)
    
    def _log_message(self, log_file: str, new_messages: List[Dict[str, str]]) -> None:
        """Log messages to log file"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "signature": self.signature,
            "new_messages": new_messages
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    # Maximum seconds for a single agent.ainvoke() call.
    # Without a timeout, SSE/network hangs can block the process for hours.
    AGENT_INVOKE_TIMEOUT_SECONDS = 300  # 5 minutes

    async def _ainvoke_with_retry(self, message: List[Dict[str, str]]) -> Any:
        """Agent invocation with retry and per-call timeout."""
        for attempt in range(1, self.max_retries + 1):
            try:
                return await asyncio.wait_for(
                    self.agent.ainvoke(
                        {"messages": message},
                        {"recursion_limit": 100}
                    ),
                    timeout=self.AGENT_INVOKE_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                print(f"⏱️ Attempt {attempt} timed out after {self.AGENT_INVOKE_TIMEOUT_SECONDS}s")
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Agent ainvoke timed out after {self.max_retries} attempts "
                        f"({self.AGENT_INVOKE_TIMEOUT_SECONDS}s each)"
                    )
                print(f"⚠️ Retrying after {self.base_delay * attempt} seconds...")
                await asyncio.sleep(self.base_delay * attempt)
            except Exception as e:
                if attempt == self.max_retries:
                    raise e
                print(f"⚠️ Attempt {attempt} failed, retrying after {self.base_delay * attempt} seconds...")
                print(f"Error details: {e}")
                await asyncio.sleep(self.base_delay * attempt)
    
    async def run_trading_session(self, today_date: str) -> None:
        """
        Run single day trading session
        
        Args:
            today_date: Trading date
        """
        print(f"📈 Starting trading session: {today_date}")
        
        # Verify model is initialized
        if self.model is None:
            error_msg = "❌ AI model not initialized. Call initialize() first."
            print(error_msg)
            raise RuntimeError(error_msg)
        
        # Set up logging
        log_file = self._setup_logging(today_date)
        
        # Get current market session from config
        current_session = get_config_value("MARKET_SESSION", "REGULAR")
        
        # Update system prompt
        self.agent = create_agent(
            self.model,
            tools=self.tools,
            system_prompt=get_agent_system_prompt(today_date, self.signature, session=current_session),
        )
        
        # Prefetch mandatory portfolio context
        prefetch_summary = await self._prefetch_portfolio_context()
        
        # Scan market for trading opportunities (all watchlist symbols with TA)
        market_scan = await self._scan_market_opportunities(today_date, top_n=15)

        # Initial user query including prefetched context AND market scan
        initial_content = (
            f"📊 COMPREHENSIVE TRADING ANALYSIS for {today_date}\n"
            f"{'='*80}\n\n"
            f"PART 1: CURRENT PORTFOLIO STATUS\n"
            f"{prefetch_summary}\n\n"
            f"PART 2: MARKET OPPORTUNITIES (Pre-scanned with Technical Analysis)\n"
            f"{market_scan}\n\n"
            f"{'='*80}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Review your current portfolio and decide on any position management (hold/trim/exit)\n"
            f"2. Analyze the top trading opportunities provided above\n"
            f"3. For any A+ setups (strength ≥3), consider opening new positions\n"
            f"4. Use get_technical_indicators() for deeper analysis if needed\n"
            f"5. Ensure proper position sizing and risk management (1% risk per trade)\n"
            f"6. When finished, send {STOP_SIGNAL} to end the session\n\n"
            f"Begin your analysis now."
        )
        user_query = [{"role": "user", "content": initial_content}]
        message = user_query.copy()
        
        # Log initial message
        self._log_message(log_file, user_query)
        
        # Trading loop
        current_step = 0
        while current_step < self.max_steps:
            current_step += 1
            print(f"🔄 Step {current_step}/{self.max_steps}")
            
            try:
                # Call agent
                response = await self._ainvoke_with_retry(message)
                
                # Extract agent response
                agent_response = extract_conversation(response, "final")
                
                # Extract reasoning_content for DeepSeek Reasoner model
                # Required by DeepSeek API: assistant messages in multi-turn
                # conversations must include the reasoning_content field.
                reasoning_content = extract_reasoning_content(response)
                
                # Log agent's analysis and decision
                print(f"\n{'='*80}")
                print(f"🤖 AGENT ANALYSIS - Step {current_step}")
                print(f"{'='*80}")
                if reasoning_content:
                    # Show abbreviated reasoning (first 300 chars)
                    preview = reasoning_content[:300] + "..." if len(reasoning_content) > 300 else reasoning_content
                    print(f"💭 Reasoning: {preview}")
                    print(f"{'─'*80}")
                print(agent_response)
                print(f"{'='*80}\n")
                
                # Check stop signal
                if STOP_SIGNAL in agent_response:
                    print("✅ Received stop signal, trading session ended")
                    log_msg = {"role": "assistant", "content": agent_response}
                    if reasoning_content:
                        log_msg["reasoning_content"] = reasoning_content
                    self._log_message(log_file, [log_msg])
                    
                    # Wait briefly for any pending orders to execute
                    print("⏳ Waiting 3 seconds for pending orders to execute...")
                    await asyncio.sleep(3)
                    break
                
                # Extract tool messages
                tool_msgs = extract_tool_messages(response)
                tool_response = '\n'.join([msg.content for msg in tool_msgs])
                
                # Log tool activities
                if tool_response:
                    print(f"\n{'─'*80}")
                    print(f"🔧 TOOL EXECUTION RESULTS - Step {current_step}")
                    print(f"{'─'*80}")
                    print(tool_response)
                    print(f"{'─'*80}\n")
                
                # Prepare new messages
                # Include reasoning_content for DeepSeek Reasoner compatibility
                assistant_msg = {"role": "assistant", "content": agent_response}
                if reasoning_content:
                    assistant_msg["reasoning_content"] = reasoning_content
                
                new_messages = [
                    assistant_msg,
                    {"role": "user", "content": f'Tool results: {tool_response}'}
                ]
                
                # Add new messages
                message.extend(new_messages)
                
                # Log messages
                self._log_message(log_file, new_messages[0])
                self._log_message(log_file, new_messages[1])
                
            except Exception as e:
                print(f"❌ Trading session error: {str(e)}")
                print(f"Error details: {e}")
                import traceback
                traceback.print_exc()
                raise
        
        # Handle trading results
        await self._handle_trading_result(today_date)
    
    async def _handle_trading_result(self, today_date: str) -> None:
        """Handle trading results - verify order execution, record trades, and enforce risk management"""
        
        print(f"\n{'='*80}")
        print(f"📊 TRADING SESSION SUMMARY - {today_date}")
        print(f"{'='*80}")
        
        # Get updated portfolio
        portfolio = await self._call_mcp_tool("get_portfolio_summary")
        if portfolio and isinstance(portfolio, dict):
            print(f"\n💼 Updated Portfolio:")
            print(f"   💰 Cash: ${portfolio.get('cash', 'N/A')}")
            print(f"   📈 Portfolio Value: ${portfolio.get('portfolio_value', 'N/A')}")
            print(f"   📊 Active Positions: {portfolio.get('position_count', 'N/A')}")
            
            # === RISK MANAGEMENT INTEGRATION ===
            # Record trades and update equity in Elder Risk Manager
            try:
                from tools.elder_risk_manager import ElderRiskManager
                import os
                
                log_path = os.environ.get("LOG_PATH", "./data/agent_data")
                risk_mgr = ElderRiskManager(
                    data_dir=os.path.join(log_path, self.signature)
                )
                
                # Update equity with real broker data
                equity = portfolio.get('portfolio_value') or portfolio.get('equity')
                if equity is not None:
                    if isinstance(equity, str):
                        equity = float(equity)
                    can_trade, risk_msg = risk_mgr.update_equity(equity)
                    print(f"\n🛡️  Risk Management Update:")
                    print(f"   {risk_msg}")
                
                # Get today's orders to record P&L
                orders = await self._call_mcp_tool("get_orders", {"status": "filled", "limit": 50})
                if orders and isinstance(orders, list):
                    # Count filled orders from today
                    today_fills = 0
                    today_pnl = 0.0
                    for order in orders:
                        # Check if order is from today
                        filled_at = order.get('filled_at', '') or order.get('created_at', '')
                        if today_date in str(filled_at):
                            today_fills += 1
                            # Try to extract P&L (if available from position data)
                            pnl = order.get('realized_pl', 0) or 0
                            if isinstance(pnl, str):
                                try:
                                    pnl = float(pnl)
                                except:
                                    pnl = 0.0
                            today_pnl += pnl
                    
                    if today_fills > 0:
                        print(f"\n📋 Today's Activity:")
                        print(f"   📝 Filled Orders: {today_fills}")
                        if today_pnl != 0:
                            risk_mgr.record_trade(today_pnl)
                            print(f"   💰 Recorded P&L: ${today_pnl:,.2f}")
                
                # Get and display risk status
                risk_status = risk_mgr.get_risk_status()
                print(f"\n🛡️  Risk Status:")
                print(f"   📅 Month: {risk_status.get('month', 'N/A')}")
                print(f"   📉 Drawdown: {risk_status.get('drawdown_percent', 0):.2f}% (limit: 6%)")
                print(f"   📊 Trades this month: {risk_status.get('trades_count', 0)}")
                print(f"   ✅ Trading allowed: {risk_status.get('trading_allowed', True)}")
                
            except ImportError:
                print(f"\n⚠️  Elder Risk Manager not available - skipping risk tracking")
            except Exception as risk_err:
                print(f"\n⚠️  Risk management update error: {risk_err}")
        
        # === POSITION SIZE COMPLIANCE CHECK ===
        # Verify no position exceeds 20% of equity
        try:
            positions = await self._call_mcp_tool("get_positions")
            account = await self._call_mcp_tool("get_account_info")
            
            if positions and account:
                equity = float(account.get('portfolio_value') or account.get('equity') or 0)
                max_position_value = equity * 0.20  # 20% cap
                
                if equity > 0:
                    violations = []
                    for pos in positions:
                        if isinstance(pos, dict):
                            symbol = pos.get('symbol', 'UNKNOWN')
                            market_value = abs(float(pos.get('market_value', 0)))
                            pct_of_equity = (market_value / equity) * 100
                            
                            if market_value > max_position_value:
                                violations.append(f"   🚨 {symbol}: ${market_value:,.2f} ({pct_of_equity:.1f}% of equity) EXCEEDS 20% cap!")
                    
                    if violations:
                        print(f"\n⚠️  POSITION SIZE VIOLATIONS DETECTED:")
                        for v in violations:
                            print(v)
                        print(f"   💡 Max position value at 20%: ${max_position_value:,.2f}")
                        print(f"   ⚡ These oversized positions should be trimmed next cycle")
                    else:
                        print(f"\n✅ All positions within 20% size limit")
        except Exception as pos_err:
            print(f"\n⚠️  Position compliance check error: {pos_err}")
        
        print("\n✅ ROUND COMPLETED")
        print("   Portfolio analysis/trading completed")
        
        print(f"{'='*80}\n")
    
    def register_agent(self) -> None:
        """
        ⚠️ DEPRECATED - No longer used with Alpaca integration
        
        Previously created position.jsonl files for local position tracking.
        Now all positions are managed by Alpaca's portfolio system.
        
        This method is kept for backward compatibility but does nothing.
        """
        print(f"⚠️ register_agent() is deprecated - Alpaca manages all positions")
        print(f"💰 Initial cash and positions are configured in Alpaca paper trading account")
        return
    
    def get_trading_dates(self, init_date: str, end_date: str) -> List[str]:
        """
        Get trading date list - NO LOCAL FILE TRACKING
        
        Simply generates all weekdays between init_date and end_date.
        Alpaca manages all positions - no local state needed.
        
        Args:
            init_date: Start date
            end_date: End date
            
        Returns:
            List of trading dates (weekdays only)
        """
        trading_dates = []
        
        init_date_obj = datetime.strptime(init_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        
        current_date = init_date_obj
        
        while current_date <= end_date_obj:
            if current_date.weekday() < 5:  # Weekdays only (Mon-Fri)
                trading_dates.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        
        return trading_dates
    
    async def run_with_retry(self, today_date: str) -> None:
        """Run method with retry"""
        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"🔄 Attempting to run {self.signature} - {today_date} (Attempt {attempt})")
                await self.run_trading_session(today_date)
                print(f"✅ {self.signature} - {today_date} run successful")
                return
            except Exception as e:
                print(f"❌ Attempt {attempt} failed: {str(e)}")
                import traceback
                traceback.print_exc()
                if attempt == self.max_retries:
                    print(f"💥 {self.signature} - {today_date} all retries failed")
                    raise
                else:
                    wait_time = self.base_delay * attempt
                    print(f"⏳ Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
    
    async def run_date_range(self, init_date: str, end_date: str) -> None:
        """
        Run all trading days in date range
        
        Args:
            init_date: Start date
            end_date: End date
        """
        print(f"📅 Running date range: {init_date} to {end_date}")
        
        # Get trading date list
        trading_dates = self.get_trading_dates(init_date, end_date)
        
        if not trading_dates:
            print(f"ℹ️ No trading days to process")
            return
        
        print(f"📊 Trading days to process: {trading_dates}")
        
        # Process each trading day
        for date in trading_dates:
            print(f"🔄 Processing {self.signature} - Date: {date}")
            
            # Set configuration
            write_config_value("TODAY_DATE", date)
            write_config_value("SIGNATURE", self.signature)
            
            try:
                await self.run_with_retry(date)
            except Exception as e:
                print(f"❌ Error processing {self.signature} - Date: {date}")
                print(e)
                raise
        
        print(f"✅ {self.signature} processing completed")
    
    def get_position_summary(self) -> Dict[str, Any]:
        """
        Get position summary from Alpaca (not from local files)
        
        NOTE: This method is deprecated. Use Alpaca MCP tools directly:
        - get_account_info() for account details
        - get_positions() for current positions
        """
        return {
            "message": "Use Alpaca MCP tools to get real-time position data",
            "recommended_tools": [
                "get_account_info() - Get cash, buying power, equity",
                "get_positions() - Get all current positions",
                "get_portfolio_summary() - Get comprehensive portfolio data"
            ]
        }
    
    def __str__(self) -> str:
        return f"BaseAgent(signature='{self.signature}', basemodel='{self.basemodel}', stocks={len(self.stock_symbols)})"
    
    def __repr__(self) -> str:
        return self.__str__()
