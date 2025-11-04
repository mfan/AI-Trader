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
# REMOVED: from tools.price_tools import add_no_trade_record  # No longer needed - Alpaca manages positions
from prompts.agent_prompt import get_agent_system_prompt, STOP_SIGNAL

# Load environment variables
load_dotenv()


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
        
        # Set OpenAI/DeepSeek configuration with smart fallback
        if openai_base_url is None:
            # Check if this is a DeepSeek model
            if "deepseek" in basemodel.lower():
                self.openai_base_url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
                print(f"🧠 Using DeepSeek API: {self.openai_base_url}")
            else:
                self.openai_base_url = os.getenv("OPENAI_API_BASE")
                print(f"🤖 Using OpenAI API: {self.openai_base_url}")
        else:
            self.openai_base_url = openai_base_url
            
        if openai_api_key is None:
            # Check if this is a DeepSeek model
            if "deepseek" in basemodel.lower():
                self.openai_api_key = os.getenv("DEEPSEEK_API_KEY")
                if self.openai_api_key:
                    print(f"✅ DeepSeek API key loaded from environment")
                else:
                    print(f"⚠️  Warning: DEEPSEEK_API_KEY not found in environment")
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
                print(f"🧠 Using DeepSeek API: {self.openai_base_url}")
                if self.openai_api_key:
                    print("✅ DeepSeek API key loaded from environment")
                else:
                    print("⚠️  No API key found - may use default")
                    
                self.model = ChatOpenAI(
                    model=self.basemodel,
                    base_url=self.openai_base_url,
                    api_key=self.openai_api_key,
                    max_retries=3,
                    timeout=30
                )
                print(f"✅ AI model initialized: {self.basemodel}")
            
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
                    timeout=30
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

        # Step 4: TA
            context_lines.append("\nStep 4 – focus on technical analysis.")
            print(f"ℹ️  Step 4: Using technical analysis only")

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
    
    async def _ainvoke_with_retry(self, message: List[Dict[str, str]]) -> Any:
        """Agent invocation with retry"""
        for attempt in range(1, self.max_retries + 1):
            try:
                return await self.agent.ainvoke(
                    {"messages": message}, 
                    {"recursion_limit": 100}
                )
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
        
        # Update system prompt
        self.agent = create_agent(
            self.model,
            tools=self.tools,
            system_prompt=get_agent_system_prompt(today_date, self.signature),
        )
        
        # Prefetch mandatory portfolio context
        prefetch_summary = await self._prefetch_portfolio_context()

        # Initial user query including prefetched context
        initial_content = (
            f"Portfolio context fetched automatically via MCP tools on {today_date}:\n"
            f"{prefetch_summary}\n\n"
            "Review the data, complete any remaining news checks, and update the portfolio accordingly."
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
                
                # Log agent's analysis and decision
                print(f"\n{'='*80}")
                print(f"🤖 AGENT ANALYSIS - Step {current_step}")
                print(f"{'='*80}")
                print(agent_response)
                print(f"{'='*80}\n")
                
                # Check stop signal
                if STOP_SIGNAL in agent_response:
                    print("✅ Received stop signal, trading session ended")
                    self._log_message(log_file, [{"role": "assistant", "content": agent_response}])
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
                new_messages = [
                    {"role": "assistant", "content": agent_response},
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
        """Handle trading results - simplified for Alpaca"""
        if_trade = get_config_value("IF_TRADE")
        
        print(f"\n{'='*80}")
        print(f"📊 TRADING SESSION SUMMARY - {today_date}")
        print(f"{'='*80}")
        
        if if_trade:
            write_config_value("IF_TRADE", False)
            print("✅ Trading completed - positions managed by Alpaca")
            print("   Trades were executed during this session")
        else:
            print("📊 No trades executed - positions unchanged in Alpaca")
            print("   Portfolio analysis completed with no action required")
            write_config_value("IF_TRADE", False)
        
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
