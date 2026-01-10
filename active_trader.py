#!/usr/bin/env python3
"""
Active Day Trading Program - High-Frequency Portfolio Management
Runs continuously during market hours, checking positions and making trading decisions every 2 minutes.

Enhanced with Technical Analysis support via TA-Lib.
Robust error handling for 24/7 reliability.
"""

import os
import asyncio
from datetime import datetime, timedelta
import signal
import sys
import traceback
import logging
from typing import Optional

from dotenv import load_dotenv

# Import tools and prompts
from tools.general_tools import get_config_value, write_config_value
from configs.settings import SystemConfig

# New Modular Imports
from tools.config_loader import load_config
from tools.agent_factory import get_agent_class
from tools.market_schedule import (
    is_market_hours, 
    get_next_market_open, 
    format_time_until, 
    should_close_positions, 
    get_next_check_time
)
from tools.scanner_utils import run_pre_market_scan
from tools.momentum_cache import MomentumCache

load_dotenv()

# Configure production-quality logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('active_trader.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger instance
logger = logging.getLogger('ActiveTrader')

# ETF Watchlist for v3.0 Mean Reversion Strategy
# These are the ONLY instruments traded - no individual stocks
ETF_WATCHLIST = [
    # Standard ETFs (0.5% stop-loss)
    "SPY", "QQQ", "IWM",   # Broad market
    "XLF", "XLE", "XLU",   # Sectors
    "GLD", "TLT",          # Commodities & Bonds
    # Leveraged 3x Bull ETFs (0.5% stop-loss)
    "TQQQ", "SPXL", "UPRO", "SOXL", "TNA",
    # Leveraged 3x Bear ETFs (0.5% stop-loss)
    # NOTE: SPXU removed - cannot be shorted on Alpaca
    "SQQQ", "SPXS", "SOXS", "TZA",
]

# Elder's Risk Management System
ELDER_RISK_ENABLED = False
try:
    from tools.elder_risk_manager import ElderRiskManager
    ELDER_RISK_ENABLED = True
    logging.info("✅ Elder Risk Management System enabled (6% Rule, 2% Rule)")
except ImportError as e:
    logging.warning(f"ℹ️  Elder Risk Management disabled: {e}")
    ELDER_RISK_ENABLED = False

# Technical Analysis Helper (optional)
TA_ENABLED = False
try:
    from tools.ta_helper import get_trading_decision_helper
    TA_ENABLED = True
    logging.info("✅ Technical Analysis support enabled (TA-Lib)")
except ImportError as e:
    logging.warning(f"ℹ️  Technical Analysis disabled (TA-Lib not available): {e}")
    TA_ENABLED = False

# Global flag for graceful shutdown
shutdown_requested = False

# Connection retry configuration
MAX_CONNECTION_RETRIES = SystemConfig.MAX_CONNECTION_RETRIES
CONNECTION_RETRY_DELAY = SystemConfig.CONNECTION_RETRY_DELAY  # seconds

# MCP service health check configuration
MCP_HEALTH_CHECK_RETRIES = SystemConfig.MCP_HEALTH_CHECK_RETRIES
MCP_HEALTH_CHECK_DELAY = SystemConfig.MCP_HEALTH_CHECK_DELAY  # seconds


async def wait_for_mcp_services(timeout=SystemConfig.MCP_WAIT_TIMEOUT):
    """
    Wait for MCP services to be ready before initializing agent
    
    Args:
        timeout: Maximum time to wait in seconds
        
    Returns:
        bool: True if services are ready, False if timeout
    """
    import httpx
    
    mcp_data_url = "http://localhost:8004"
    mcp_trade_url = "http://localhost:8005"
    
    logger.info("🔍 Checking MCP services availability...")
    
    start_time = asyncio.get_event_loop().time()
    retries = 0
    
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        if shutdown_requested:
            return False
            
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                # Try to connect to both services with simple GET requests
                try:
                    data_response = await client.get(mcp_data_url)
                    trade_response = await client.get(mcp_trade_url)
                    
                    # Services are listening if we get any response (even error responses)
                    if data_response is not None and trade_response is not None:
                        logger.info("✅ MCP services are ready!")
                        logger.info(f"   ├─ Alpaca Data MCP (port 8004): Ready")
                        logger.info(f"   └─ Alpaca Trade MCP (port 8005): Ready")
                        return True
                except httpx.HTTPStatusError:
                    # Even HTTP errors mean the service is up
                    logger.info("✅ MCP services are ready!")
                    logger.info(f"   ├─ Alpaca Data MCP (port 8004): Ready")
                    logger.info(f"   └─ Alpaca Trade MCP (port 8005): Ready")
                    return True
                    
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            retries += 1
            if retries % 3 == 0:  # Log every 3rd attempt
                logger.info(f"⏳ Waiting for MCP services... (attempt {retries})")
                logging.debug(f"MCP connection attempt failed: {e}")
            
            await asyncio.sleep(MCP_HEALTH_CHECK_DELAY)
        except Exception as e:
            retries += 1
            if retries % 3 == 0:
                logging.debug(f"Unexpected error checking MCP services: {e}")
            await asyncio.sleep(MCP_HEALTH_CHECK_DELAY)
    
    logger.warning(f"⚠️  MCP services not ready after {timeout}s timeout")
    return False


def signal_handler(sig, frame):
    """Handle Ctrl+C and termination signals gracefully"""
    global shutdown_requested
    if shutdown_requested:
        # Second signal - force exit
        logging.info("\n🛑 Force shutdown requested. Exiting immediately...")
        logger.info("\n🛑 Force shutdown requested. Exiting immediately...")
        sys.exit(1)
    else:
        # First signal - graceful shutdown
        logging.info("\n⚠️  Shutdown signal received. Finishing current cycle... (Press Ctrl+C again to force quit)")
        logger.info("\n⚠️  Shutdown signal received. Finishing current cycle... (Press Ctrl+C again to force quit)")
        shutdown_requested = True


async def run_trading_cycle(agent, cycle_number, session_type="regular"):
    """
    Run a single trading cycle with comprehensive error handling
    
    Args:
        agent: Initialized agent instance
        cycle_number: Current cycle number
        session_type: Type of market session (always "regular")
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Map session type to display name
        session_display = {
            "pre": "PRE-MARKET SESSION 🌅",
            "regular": "REGULAR SESSION",
            "post": "POST-MARKET SESSION 🌙"
        }.get(session_type, "REGULAR SESSION")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🔄 TRADING CYCLE #{cycle_number} - {session_display}")
        logger.info(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*80}\n")
        
        logging.info(f"Starting trading cycle #{cycle_number} (regular)")
        
        # Check if we should close all positions (dynamically determined)
        should_close, close_deadline = should_close_positions(session_type)
        if should_close:
            close_time_str = close_deadline.strftime('%I:%M %p ET') if close_deadline else "market close"
            logging.warning(f"⏰ End of trading day ({close_time_str}) - closing all positions")
            logger.info(f"⏰ End of trading day ({close_time_str}) - closing all positions")
            try:
                # Close all positions before end of day
                logger.info("📉 Executing end-of-day position closure...")
                from tools.alpaca_trading import get_alpaca_client
                client = get_alpaca_client()
                client.trading_client.close_all_positions(cancel_orders=True)
                logger.info("✅ All positions closed and pending orders cancelled")
            except Exception as e:
                logging.error(f"❌ Error closing positions: {e}")
                logger.info(f"❌ Error closing positions: {e}")
            
            # After closing positions, we should probably stop trading for the day or session
            # But the loop continues. Let's just return True to skip this cycle's trading logic
            # Wait, if we return True, it counts as a successful cycle.
            # If we want to stop trading, we should probably set shutdown_requested or just return.
            # For now, let's just return True to indicate "cycle handled (by closing everything)"
            return True
        
        # Get current date for trading
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Update runtime configuration
        write_config_value("TODAY_DATE", current_date)
        write_config_value("MARKET_SESSION", session_type)
        write_config_value("TA_ENABLED", "true" if TA_ENABLED else "false")
        
        # Run trading for current date with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            if shutdown_requested:
                logger.info("🛑 Shutdown requested, skipping trading cycle")
                return False
                
            try:
                await agent.run_date_range(current_date, current_date)
                break  # Success, exit retry loop
            except asyncio.TimeoutError:
                logging.warning(f"⏱️  Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)  # Wait before retry
                else:
                    raise
            except Exception as e:
                logging.error(f"❌ Error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)  # Wait before retry
                else:
                    raise
        
        # Display trading round completion status
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 CYCLE #{cycle_number} SUMMARY (REGULAR)")
        logger.info(f"{'='*80}")
        logger.info(f"📅 Date: {current_date}")
        logger.info(f"⏰ Completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get final status from agent's trading session
        # Note: The agent has already verified order execution in _handle_trading_result()
        # This displays the outcomes for the active_trader log
        
        logger.info(f"✅ TRADING/ANALYSIS ROUND COMPLETED")
        logger.info(f"   Check agent logs for detailed execution report")
        
        logger.info(f"{'='*80}")
        logging.info(f"✅ Cycle #{cycle_number} completed successfully")
        
        logger.info(f"\n✅ Cycle #{cycle_number} completed successfully")
        return True
        
    except KeyboardInterrupt:
        # Re-raise keyboard interrupt to allow graceful shutdown
        raise
    except Exception as e:
        logging.error(f"❌ Error in trading cycle #{cycle_number}: {str(e)}")
        logging.error(f"📋 Traceback: {traceback.format_exc()}")
        logger.info(f"❌ Error in trading cycle #{cycle_number}: {str(e)}")
        return False


class ActiveTraderEngine:
    """
    Engine for running the active trading loop.
    Encapsulates state and logic for the continuous trading process.
    """
    def __init__(self, config_path: Optional[str], interval_minutes: int):
        self.config_path = config_path
        self.interval_minutes = interval_minutes
        
        # Load configuration
        self.config = load_config(config_path)
        self._parse_config()
        
        # Runtime state
        self.agent = None
        self.cycle_number = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5  # Increased for robustness
        self.initialization_retries = 0
        self.momentum_watchlist = None
        self.last_scan_date = None
        self.elder_risk_manager = None

    def _parse_config(self):
        # Get Agent type
        self.agent_type = self.config.get("agent_type", "BaseAgent")
        try:
            self.AgentClass = get_agent_class(self.agent_type)
        except (ValueError, ImportError, AttributeError) as e:
            logging.error(str(e))
            logger.info(str(e))
            sys.exit(1)
        
        # Get model list (only enabled models)
        enabled_models = [
            model for model in self.config["models"] 
            if model.get("enabled", True)
        ]
        
        if not enabled_models:
            logging.error("❌ No enabled models found in configuration")
            sys.exit(1)
        
        # Use first enabled model
        self.model_config = enabled_models[0]
        self.model_name = self.model_config.get("name", "unknown")
        self.basemodel = self.model_config.get("basemodel")
        self.signature = self.model_config.get("signature")
        self.openai_base_url = self.model_config.get("openai_base_url", None)
        self.openai_api_key = self.model_config.get("openai_api_key", None)
        
        # Get agent configuration
        agent_config = self.config.get("agent_config", {})
        self.log_config = self.config.get("log_config", {})
        self.max_steps = agent_config.get("max_steps", 10)
        self.max_retries = agent_config.get("max_retries", 3)
        self.base_delay = agent_config.get("base_delay", 0.5)
        self.initial_cash = agent_config.get("initial_cash", 10000.0)
        self.log_path = self.log_config.get("log_path", "./data/agent_data")

    def _log_startup(self):
        current_date = datetime.now().strftime("%Y-%m-%d")
        logger.info("🚀 ACTIVE DAY TRADING PROGRAM STARTED")
        logger.info(f"{'='*80}")
        logger.info(f"🤖 Agent type: {self.agent_type}")
        logger.info(f"📅 Start date: {current_date}")
        logger.info(f"🤖 Model: {self.model_name} ({self.signature})")
        logger.info(f"⏱️  Check interval: {self.interval_minutes} minutes (HIGH FREQUENCY)")
        logger.info(f"⚙️  Agent config: max_steps={self.max_steps}, max_retries={self.max_retries}")
        logger.info(f"💰 Initial cash: ${self.initial_cash:.2f}")
        logger.info(f"📊 Market Hours (Extended Hours Enabled):")
        logger.info(f"   ├─ 🌅 Pre-market:  4:00 AM - 9:30 AM ET")
        logger.info(f"   ├─ 🟢 Regular:     9:30 AM - 4:00 PM ET")
        logger.info(f"   └─ 🌙 Post-market: 4:00 PM - 8:00 PM ET")
        logger.info(f"   📝 Positions close 15 minutes before market close (dynamic)")
        logger.info(f"🛡️  Error handling: Auto-retry with graceful degradation")
        logger.info(f"{'='*80}\n")
        
        logging.info(f"Agent: {self.agent_type}, Model: {self.model_name}, Interval: {self.interval_minutes}min")
        
        # Initialize runtime configuration
        write_config_value("SIGNATURE", self.signature)
        write_config_value("TODAY_DATE", current_date)

    def _init_risk_manager(self):
        if ELDER_RISK_ENABLED:
            try:
                self.elder_risk_manager = ElderRiskManager(
                    data_dir=os.path.join(self.log_path, self.signature)
                )
                logger.info(f"✅ Elder Risk Manager initialized")
                logger.info(f"   ├─ Monthly drawdown limit: 6%")
                logger.info(f"   ├─ Per-trade risk limit: 2%")
                logger.info(f"   ├─ Total portfolio risk: 6% max")
                logger.info(f"   └─ Initial equity: ${self.initial_cash:,.2f}")
                
                status = self.elder_risk_manager.get_monthly_status()
                if status['suspended']:
                    logger.warning(f"⚠️  TRADING SUSPENDED: Monthly drawdown limit exceeded!")
                    logger.warning(f"   └─ Current drawdown: {status['drawdown_pct']:.2f}% (limit: 6%)")
                else:
                    logger.info(f"   📊 Month status: {status['drawdown_pct']:.2f}% drawdown (OK)")
            except Exception as e:
                logging.error(f"Failed to initialize Elder Risk Manager: {e}")
                self.elder_risk_manager = None

    async def _load_initial_watchlist(self):
        """
        Load ETF watchlist for v3.0 Mean Reversion Strategy.
        Uses fixed ETF list instead of momentum scanning.
        """
        try:
            import pytz
            
            eastern = pytz.timezone('US/Eastern')
            now = datetime.now(eastern)
            today = now.strftime('%Y-%m-%d')
            
            # v3.0 Strategy: Use fixed ETF watchlist (no momentum scanning)
            self.momentum_watchlist = ETF_WATCHLIST.copy()
            self.last_scan_date = today
            
            logger.info(f"✅ Loaded ETF watchlist for v3.0 Mean Reversion Strategy:")
            logger.info(f"   📊 Standard ETFs: SPY, QQQ, IWM, XLF, XLE, XLU, GLD, TLT")
            logger.info(f"   📈 Leveraged Bull: TQQQ, SPXL, UPRO, SOXL, TNA")
            logger.info(f"   📉 Leveraged Bear: SQQQ, SPXS, SPXU, SOXS, TZA")
            logger.info(f"   Total: {len(self.momentum_watchlist)} ETFs")
        except Exception as e:
            logger.warning(f"⚠️  Error loading momentum watchlist: {e}")
            logger.warning(f"   Will retry during daily scan window (9:00-9:30 AM)")

    async def _check_daily_scan(self):
        """
        Daily reset for v3.0 ETF strategy.
        No momentum scanning needed - just reset the date marker.
        """
        try:
            import pytz
            eastern = pytz.timezone('US/Eastern')
            now = datetime.now(eastern)
            today = now.strftime('%Y-%m-%d')
            
            # Reset date marker for new trading day (ETF watchlist stays the same)
            if (now.weekday() < 5 and self.last_scan_date != today):
                logger.info("🌅 New trading day - resetting for v3.0 Mean Reversion Strategy")
                self.momentum_watchlist = ETF_WATCHLIST.copy()
                self.last_scan_date = today
                logger.info(f"✅ ETF watchlist ready: {len(self.momentum_watchlist)} instruments")
                
                # Force agent reinitialization with fresh state
                if self.agent is not None:
                    logger.info("🔄 Reinitializing agent for new trading day...")
                    try:
                        await self.agent.cleanup()
                    except:
                        pass
                    self.agent = None
        except Exception as e:
            logger.error(f"Error in daily reset: {e}")

    async def _handle_sleep_mode(self):
        try:
            import pytz
            eastern = pytz.timezone('US/Eastern')
            now = datetime.now(eastern)
            
            # Calculate next market open
            next_open = get_next_market_open()
            
            if next_open:
                time_until = format_time_until(next_open)
                
                # Only log detailed message on first cycle or every hour
                if self.cycle_number == 1 or self.cycle_number % 60 == 0:
                    logger.info(f"\n{'='*80}")
                    logger.info(f"💤 MARKET CLOSED - INTELLIGENT SLEEP MODE")
                    logger.info(f"{'='*80}")
                    logger.info(f"⏰ Current time: {now.strftime('%A, %B %d, %Y at %I:%M:%S %p ET')}")
                    logger.info(f"")
                    logger.info(f"📅 Market Hours (Extended Hours Enabled):")
                    logger.info(f"   ├─ 🌅 Pre-market:  4:00 AM - 9:30 AM ET")
                    logger.info(f"   ├─ 🟢 Regular:     9:30 AM - 4:00 PM ET")
                    logger.info(f"   └─ 🌙 Post-market: 4:00 PM - 8:00 PM ET")
                    logger.info(f"")
                    logger.info(f"⏭️  Next market opens: {next_open.strftime('%A, %B %d at %I:%M %p ET')}")
                    logger.info(f"⏳ Time until open: {time_until}")
                    logger.info(f"")
                    logger.info(f"😴 Entering intelligent sleep mode - CPU usage minimized")
                    logger.info(f"⏰ Will wake up 5 minutes before market open for preparation")
                    logger.info(f"{'='*80}\n")
                    
                    logging.info(f"Market closed. Next open: {next_open.strftime('%Y-%m-%d %H:%M ET')} ({time_until})")
                
                # Calculate sleep duration
                # Wake up 5 minutes before market open for agent preparation
                wake_up_time = next_open - timedelta(minutes=5)
                sleep_seconds = (wake_up_time - now).total_seconds()
                
                # If wake_up time is in the past or very soon (< 10 seconds), 
                # market is about to open - exit sleep mode immediately
                if sleep_seconds <= 60:
                    # Calculate time until actual market open (not wake time)
                    seconds_until_open = (next_open - now).total_seconds()
                    
                    # If we're past wake time but market hasn't opened yet, wait for market open
                    if seconds_until_open > 0 and seconds_until_open <= 300:  # Within 5 minutes of open
                        logger.info(f"⏰ Market opens in {int(seconds_until_open)}s - waiting for market open...")
                        await asyncio.sleep(seconds_until_open + 1)  # Add 1 second buffer
                        # Market should be open now - exit sleep mode
                        logger.info(f"✅ Market is now open - exiting sleep mode")
                        return
                    elif seconds_until_open <= 0:
                        # Market should already be open - exit immediately
                        logger.info(f"✅ Market should be open - exiting sleep mode")
                        return
                    else:
                        # Still more than 5 minutes until open - shouldn't happen
                        logger.warning(f"⚠️  Unexpected state: wake_up in {sleep_seconds}s, market in {seconds_until_open}s")
                        await asyncio.sleep(60)
                        return
                
                else:  # More than 1 minute until wake up
                    if self.cycle_number == 1:
                        logger.info(f"😴 Sleeping until {wake_up_time.strftime('%I:%M:%S %p ET')} (wake up 5 min before market)...")
                    
                    # Sleep in 1-second chunks to allow immediate shutdown response
                    total_sleep = int(sleep_seconds)
                    
                    for elapsed in range(0, total_sleep):
                        if shutdown_requested:
                            logger.info("🛑 Shutdown requested during sleep mode")
                            break
                        
                        remaining = total_sleep - elapsed
                        
                        # Show countdown every 5 minutes or every minute if < 10 min remaining
                        # Only check logging triggers once per minute
                        if elapsed % 60 == 0:
                            if remaining <= 600 or elapsed % 300 == 0:
                                remaining_formatted = format_time_until(wake_up_time)
                                logger.info(f"💤 Sleep mode active - Wake up in: {remaining_formatted}")
                        
                        await asyncio.sleep(1)
                    
                    if shutdown_requested:
                        return

                    if not shutdown_requested:
                        logger.info(f"\n{'='*80}")
                        logger.info(f"⏰ WAKE UP - Preparing for market open in 5 minutes")
                        logger.info(f"🔄 Agent will start processing when market opens at 9:30 AM ET")
                        logger.info(f"{'='*80}\n")
            else:
                # Couldn't calculate next open - sleep for interval
                await asyncio.sleep(self.interval_minutes * 60)
        except Exception as e:
            logging.error(f"Error calculating market status: {e}")
            # Sleep for interval on error
            await asyncio.sleep(self.interval_minutes * 60)

    async def _ensure_agent_ready(self):
        global shutdown_requested
        if self.agent is None:
            # Wait for MCP services to be ready before initializing
            mcp_ready = await wait_for_mcp_services(timeout=60)
            if not mcp_ready:
                logger.warning("⚠️  MCP services not available, will retry initialization later...")
                await asyncio.sleep(CONNECTION_RETRY_DELAY)
                return False
            
            logger.info("🔧 Initializing trading agent...")
            logging.info("Initializing trading agent...")
            
            try:
                # Require momentum watchlist - no fallback
                if not self.momentum_watchlist:
                    logger.error("❌ Momentum watchlist is empty! Run momentum scan first.")
                    await asyncio.sleep(CONNECTION_RETRY_DELAY)
                    return False
                
                logger.info(f"📊 Using dynamic momentum watchlist: {len(self.momentum_watchlist)} stocks")
                
                self.agent = self.AgentClass(
                    signature=self.signature,
                    basemodel=self.basemodel,
                    stock_symbols=self.momentum_watchlist,
                    log_path=self.log_path,
                    openai_base_url=self.openai_base_url,
                    openai_api_key=self.openai_api_key,
                    max_steps=self.max_steps,
                    max_retries=self.max_retries,
                    base_delay=self.base_delay,
                    initial_cash=self.initial_cash,
                    init_date=datetime.now().strftime("%Y-%m-%d")
                )
                
                logger.info(f"✅ {self.agent_type} instance created successfully")
                logging.info(f"{self.agent_type} instance created successfully")
                
                # Initialize MCP connection and AI model with retry
                for retry in range(MAX_CONNECTION_RETRIES):
                    try:
                        await self.agent.initialize()
                        logger.info("✅ Agent initialization complete")
                        logging.info("Agent initialization complete")
                        self.initialization_retries = 0
                        break
                    except Exception as init_error:
                        logging.error(f"❌ Initialization attempt {retry + 1}/{MAX_CONNECTION_RETRIES} failed: {init_error}")
                        if retry < MAX_CONNECTION_RETRIES - 1:
                            logger.info(f"⚠️  Initialization failed, retrying in {CONNECTION_RETRY_DELAY}s...")
                            await asyncio.sleep(CONNECTION_RETRY_DELAY)
                        else:
                            raise
                
                logger.info("🎯 Starting continuous day trading loop...\n")
                logging.info("Continuous day trading loop started")
                return True
                
            except Exception as e:
                logging.error(f"❌ Fatal error during agent initialization: {e}")
                logging.error(f"Traceback: {traceback.format_exc()}")
                self.initialization_retries += 1
                
                if self.initialization_retries >= MAX_CONNECTION_RETRIES:
                    logger.info(f"❌ Failed to initialize after {MAX_CONNECTION_RETRIES} attempts. Exiting.")
                    shutdown_requested = True
                    return False

                
                logger.info(f"⚠️  Initialization failed, will retry in {CONNECTION_RETRY_DELAY}s...")
                await asyncio.sleep(CONNECTION_RETRY_DELAY)
                return False
        return True

    async def run(self):
        global shutdown_requested
        logging.info("🚀 Starting Active Day Trading Program")
        self._log_startup()
        self._init_risk_manager()
        await self._load_initial_watchlist()
        
        while not shutdown_requested:
            try:
                # CHECK MARKET HOURS FIRST - before any MCP connection attempts
                self.cycle_number += 1
                is_open, session_type = is_market_hours()
                
                # Check if we need to run daily momentum scan
                await self._check_daily_scan()
                
                # FAILSAFE: Double-check market hours before entering sleep mode
                if not is_open:
                    import pytz
                    from datetime import time
                    eastern = pytz.timezone('US/Eastern')
                    now_verify = datetime.now(eastern)
                    current_time_verify = now_verify.time()
                    regular_start = time(9, 30, 0)
                    regular_end = time(16, 0, 0)
                    
                    # Check if we're in market hours AND there's a trading session today
                    if (now_verify.weekday() < 5 and 
                        regular_start <= current_time_verify < regular_end):
                        # Additional check: Is today actually a trading day? (not a holiday)
                        try:
                            from tools.alpaca_trading import get_alpaca_client
                            client = get_alpaca_client()
                            has_session_today = client.is_market_open_today()
                            
                            if has_session_today:
                                logger.warning(f"⚠️  FAILSAFE: Market IS open at {now_verify.strftime('%I:%M:%S %p ET')} - overriding sleep mode")
                                is_open = True
                                session_type = "regular"
                            else:
                                logger.info(f"✅ FAILSAFE confirmed: No trading session today (holiday/half-day)")
                        except Exception as failsafe_error:
                            logger.warning(f"⚠️  FAILSAFE check failed, staying in closed mode: {failsafe_error}")
                
                if not is_open:
                    # Market is closed - enter intelligent sleep mode immediately
                    await self._handle_sleep_mode()
                    continue  # Skip to next iteration without initializing agent
                
                # Market is open - proceed with agent initialization if needed
                if not await self._ensure_agent_ready():
                    continue
                
                # Market is open - agent is initialized - proceed with trading cycle
                
                # 🛡️ CHECK ELDER'S 6% RULE - Monthly Drawdown Brake
                if self.elder_risk_manager is not None:
                    try:
                        # Update equity using real Alpaca account data via MCP
                        equity = None
                        if hasattr(self.agent, '_call_mcp_tool'):
                            try:
                                account_info = await self.agent._call_mcp_tool("get_account_info")
                                if account_info and isinstance(account_info, dict):
                                    # Use portfolio_value (equity) if available, otherwise cash
                                    equity = account_info.get('portfolio_value') or account_info.get('equity')
                                    if equity is None:
                                        equity = account_info.get('cash', self.initial_cash)
                                    # Convert to float if string
                                    if isinstance(equity, str):
                                        equity = float(equity)
                                    logger.debug(f"📊 Real account equity from Alpaca: ${equity:,.2f}")
                            except Exception as mcp_err:
                                logging.warning(f"⚠️ Could not fetch account info from MCP: {mcp_err}")
                        
                        # Only update equity if we got real data
                        if equity is not None and equity > 0:
                            self.elder_risk_manager.update_equity(equity)
                        else:
                            # Don't update with bad data - just check status
                            logging.warning("⚠️ Skipping equity update - no valid account data from MCP")
                            
                        status = self.elder_risk_manager.get_monthly_status()
                        
                        if status['suspended']:
                            logger.info(f"\n{'='*80}")
                            logger.info(f"🛑 TRADING SUSPENDED - ELDER'S 6% MONTHLY RULE")
                            logger.info(f"{'='*80}")
                            logger.info(f"📉 Current drawdown: {status['drawdown_pct']:.2f}%")
                            logger.info(f"❌ Limit exceeded: 6.00%")
                            logger.info(f"📅 Month: {status['current_month']}")
                            logger.info(f"💰 Starting equity: ${status['month_start_equity']:,.2f}")
                            logger.info(f"💰 Current equity: ${status['current_equity']:,.2f}")
                            logger.info(f"📊 Loss: ${status['month_start_equity'] - status['current_equity']:,.2f}")
                            logger.info(f"")
                            logger.info(f"⏸️  Trading will resume next month")
                            logger.info(f"📚 Use this time to:")
                            logger.info(f"   ├─ Review losing trades")
                            logger.info(f"   ├─ Refine your strategy")
                            logger.info(f"   ├─ Study market conditions")
                            logger.info(f"   └─ Return stronger next month")
                            logger.info(f"{'='*80}\n")
                            
                            logging.warning(f"Trading suspended: 6% rule ({status['drawdown_pct']:.2f}% drawdown)")
                            
                            # Sleep for interval and continue (skip trading cycle)
                            for _ in range(self.interval_minutes * 60):
                                if shutdown_requested:
                                    break
                                await asyncio.sleep(1)
                            continue
                        else:
                            # Log risk status every 10 cycles
                            if self.cycle_number % 10 == 0:
                                logger.info(f"🛡️  Risk Status: {status['drawdown_pct']:.2f}% monthly drawdown (6% limit)")
                                
                    except Exception as e:
                        logging.error(f"Error checking Elder risk status: {e}")
                        # Continue trading on error (fail-safe)
                
                # Run trading cycle
                logger.info(f"🟢 Market is open - REGULAR session")
                logging.info(f"Market open - regular session, starting cycle #{self.cycle_number}")
                
                success = await run_trading_cycle(self.agent, self.cycle_number, session_type)
                
                if success:
                    self.consecutive_failures = 0
                else:
                    self.consecutive_failures += 1
                    logging.warning(f"⚠️  Consecutive failures: {self.consecutive_failures}/{self.max_consecutive_failures}")
                    logger.info(f"⚠️  Consecutive failures: {self.consecutive_failures}/{self.max_consecutive_failures}")
                    
                    # On repeated failures, try to reinitialize agent
                    if self.consecutive_failures >= 3:
                        logging.warning("⚠️  Multiple failures detected, will reinitialize agent")
                        logger.info("⚠️  Multiple failures detected, attempting to reinitialize agent...")
                        self.agent = None  # Force re-initialization
                    
                    if self.consecutive_failures >= self.max_consecutive_failures:
                        logging.error(f"❌ Maximum consecutive failures ({self.max_consecutive_failures}) reached")
                        logger.info(f"❌ Maximum consecutive failures reached. Stopping program.")
                        break
                
                if shutdown_requested:
                    break
                
                # Calculate next check time
                next_check = get_next_check_time(self.interval_minutes)
                wait_seconds = self.interval_minutes * 60
                
                logger.info(f"\n⏳ Next trading cycle at: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"💤 Sleeping for {self.interval_minutes} minutes...")
                logger.info(f"{'─'*80}\n")
                
                # Sleep until next check (with periodic wake-up to check shutdown flag)
                for second in range(wait_seconds):
                    if shutdown_requested:
                        break
                    await asyncio.sleep(1)
            
            except KeyboardInterrupt:
                logging.info("Keyboard interrupt received")
                shutdown_requested = True
                break
            
            except Exception as e:
                logging.error(f"❌ Unexpected error in main loop: {e}")
                logging.error(f"Traceback: {traceback.format_exc()}")
                logger.info(f"❌ Unexpected error in main loop: {e}")
                
                # Try to recover
                self.consecutive_failures += 1
                if self.consecutive_failures >= self.max_consecutive_failures:
                    logging.error("Too many failures, stopping")
                    break
                
                # Force re-initialization
                self.agent = None
                logger.info(f"⚠️  Will attempt recovery in {CONNECTION_RETRY_DELAY}s...")
                await asyncio.sleep(CONNECTION_RETRY_DELAY)
        
        # Cleanup and final summary
        logger.info(f"\n{'='*80}")
        logger.info("🛑 ACTIVE DAY TRADING PROGRAM STOPPED")
        logger.info(f"📊 Total cycles completed: {self.cycle_number}")
        logging.info(f"Program stopped. Total cycles: {self.cycle_number}")
        
        # Final summary
        if self.agent is not None:
            try:
                final_summary = self.agent.get_position_summary()
                logger.info(f"\n📊 FINAL PORTFOLIO SUMMARY:")
                logger.info(f"   ├─ Latest date: {final_summary.get('latest_date')}")
                logger.info(f"   ├─ Total records: {final_summary.get('total_records')}")
                logger.info(f"   ├─ Cash balance: ${final_summary.get('positions', {}).get('CASH', 0):.2f}")
                
                positions = final_summary.get('positions', {})
                if len(positions) > 1:
                    logger.info(f"   └─ Final positions:")
                    for symbol, amount in positions.items():
                        if symbol != 'CASH' and amount != 0:
                            logger.info(f"      ├─ {symbol}: {amount}")
                
                logging.info(f"Final cash: ${final_summary.get('positions', {}).get('CASH', 0):.2f}")
            except Exception as e:
                logging.error(f"Error getting final summary: {e}")
        
        logger.info(f"{'='*80}\n")


async def active_trading_loop(config_path=None, interval_minutes=2):
    """
    Main active day trading loop - runs continuously checking positions and trading every 2 minutes
    
    Designed for high-frequency day trading with robust error handling and auto-recovery.
    
    Args:
        config_path: Configuration file path
        interval_minutes: Minutes between trading cycles (default: 2 for day trading)
    """
    engine = ActiveTraderEngine(config_path, interval_minutes)
    await engine.run()


if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Support command line arguments
    # Usage: python active_trader.py [config_path] [interval_minutes]
    # Example: python active_trader.py configs/default_config.json 2
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    interval_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 2  # Default to 2 minutes for day trading
    
    if config_path:
        logger.info(f"📄 Using configuration file: {config_path}")
        logging.info(f"Using configuration file: {config_path}")
    else:
        logger.info(f"📄 Using default configuration file: configs/default_config.json")
        logging.info("Using default configuration file")
    
    logger.info(f"⏱️  Trading interval: {interval_minutes} minutes")
    logger.info(f"�� Day Trading Mode: High-frequency with robust error handling\n")
    logging.info(f"Trading interval: {interval_minutes} minutes")
    
    # Run the active trading loop
    try:
        asyncio.run(active_trading_loop(config_path, interval_minutes))
    except KeyboardInterrupt:
        logger.info("\n✅ Program terminated by user")
        logging.info("Program terminated by user (KeyboardInterrupt)")
    except Exception as e:
        logger.info(f"\n❌ Fatal error: {e}")
        logging.error(f"Fatal error: {e}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
