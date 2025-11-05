#!/usr/bin/env python3
"""
Active Day Trading Program - High-Frequency Portfolio Management
Runs continuously during market hours, checking positions and making trading decisions every 2 minutes.

Enhanced with Technical Analysis support via TA-Lib.
Robust error handling for 24/7 reliability.
"""

import os
import asyncio
from datetime import datetime, time, timedelta
import json
from pathlib import Path
from dotenv import load_dotenv
import signal
import sys
import traceback
import logging
from typing import Tuple, Optional

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

# Import tools and prompts
from tools.general_tools import get_config_value, write_config_value
from prompts.agent_prompt import all_nasdaq_100_symbols

# Technical Analysis Helper (optional)
TA_ENABLED = False
try:
    from tools.ta_helper import get_trading_decision_helper
    TA_ENABLED = True
    logging.info("✅ Technical Analysis support enabled (TA-Lib)")
except ImportError as e:
    logging.warning(f"ℹ️  Technical Analysis disabled (TA-Lib not available): {e}")
    TA_ENABLED = False


# Agent class mapping table
AGENT_REGISTRY = {
    "BaseAgent": {
        "module": "agent.base_agent.base_agent",
        "class": "BaseAgent"
    },
}

# Global flag for graceful shutdown
shutdown_requested = False

# Connection retry configuration
MAX_CONNECTION_RETRIES = 5
CONNECTION_RETRY_DELAY = 30  # seconds

# MCP service health check configuration
MCP_HEALTH_CHECK_RETRIES = 10
MCP_HEALTH_CHECK_DELAY = 5  # seconds


async def wait_for_mcp_services(timeout=60):
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
    logging.info("\n⚠️  Shutdown signal received. Finishing current cycle...")
    logger.info("\n⚠️  Shutdown signal received. Finishing current cycle...")
    shutdown_requested = True


def get_agent_class(agent_type):
    """
    Dynamically import and return the corresponding class based on agent type name
    
    Args:
        agent_type: Agent type name (e.g., "BaseAgent")
        
    Returns:
        Agent class
        
    Raises:
        ValueError: If agent type not supported
        ImportError: If module cannot be imported
    """
    if agent_type not in AGENT_REGISTRY:
        supported_types = ", ".join(AGENT_REGISTRY.keys())
        error_msg = (
            f"❌ Unsupported agent type: {agent_type}\n"
            f"   Supported types: {supported_types}"
        )
        logging.error(error_msg)
        raise ValueError(error_msg)
    
    agent_info = AGENT_REGISTRY[agent_type]
    module_path = agent_info["module"]
    class_name = agent_info["class"]
    
    try:
        import importlib
        module = importlib.import_module(module_path)
        agent_class = getattr(module, class_name)
        logging.info(f"✅ Successfully loaded Agent class: {agent_type} (from {module_path})")
        logger.info(f"✅ Successfully loaded Agent class: {agent_type} (from {module_path})")
        return agent_class
    except ImportError as e:
        error_msg = f"❌ Unable to import agent module {module_path}: {e}"
        logging.error(error_msg)
        raise ImportError(error_msg)
    except AttributeError as e:
        error_msg = f"❌ Class {class_name} not found in module {module_path}: {e}"
        logging.error(error_msg)
        raise AttributeError(error_msg)


def load_config(config_path=None):
    """
    Load configuration file from configs directory with error handling
    
    Args:
        config_path: Configuration file path, if None use default config
        
    Returns:
        dict: Configuration dictionary
        
    Raises:
        SystemExit: If config cannot be loaded
    """
    if config_path is None:
        config_path = Path(__file__).parent / "configs" / "default_config.json"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        error_msg = f"❌ Configuration file does not exist: {config_path}"
        logging.error(error_msg)
        logger.info(error_msg)
        exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logging.info(f"✅ Successfully loaded configuration file: {config_path}")
        logger.info(f"✅ Successfully loaded configuration file: {config_path}")
        return config
    except json.JSONDecodeError as e:
        error_msg = f"❌ Configuration file JSON format error: {e}"
        logging.error(error_msg)
        logger.info(error_msg)
        exit(1)
    except Exception as e:
        error_msg = f"❌ Failed to load configuration file: {e}"
        logging.error(error_msg)
        logger.info(error_msg)
        exit(1)


def is_market_hours() -> Tuple[bool, str]:
    """
    Check if current time is within regular market hours ONLY
    
    Regular Market Hours:
    - Regular:     9:30 AM - 4:00 PM ET (Monday-Friday)
    
    Pre-market and post-market trading are DISABLED.
    
    Returns:
        tuple: (is_open, session_type) where session_type is one of:
               "regular" or "closed"
    """
    try:
        import pytz
        
        # Get current time in Eastern Time
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
        current_time = now.time()
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False, "closed"
        
        # Define regular market hours ONLY (Eastern Time)
        regular_start = time(9, 30)        # 9:30 AM ET
        regular_end = time(16, 0)          # 4:00 PM ET
        
        # Check if we're in regular market hours
        if regular_start <= current_time < regular_end:
            return True, "regular"
        else:
            return False, "closed"
            
    except Exception as e:
        logging.error(f"❌ Error checking market hours: {e}")
        # Fail safe - assume market is closed on error
        return False, "closed"


def get_next_market_open() -> Optional[datetime]:
    """
    Calculate when the next regular market session opens (9:30 AM ET)
    
    Returns:
        datetime: Next market open time in Eastern Time, or None on error
    """
    try:
        import pytz
        
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
        current_time = now.time()
        
        regular_market_start = time(9, 30)  # 9:30 AM ET
        
        # If it's before 9:30 AM today and it's a weekday, next open is today at 9:30 AM
        if current_time < regular_market_start and now.weekday() < 5:
            next_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            return next_open
        
        # Otherwise, calculate next weekday at 9:30 AM
        days_ahead = 1
        next_day = now + timedelta(days=days_ahead)
        
        # Skip to Monday if we land on weekend
        while next_day.weekday() >= 5:  # Saturday or Sunday
            days_ahead += 1
            next_day = now + timedelta(days=days_ahead)
        
        # Set to 9:30 AM ET
        next_open = next_day.replace(hour=9, minute=30, second=0, microsecond=0)
        return next_open
        
    except Exception as e:
        logging.error(f"❌ Error calculating next market open: {e}")
        return None


def format_time_until(target_time: datetime) -> str:
    """
    Format time remaining until target in human-readable format
    
    Args:
        target_time: Target datetime
        
    Returns:
        str: Formatted time string (e.g., "2h 15m" or "45m" or "5d 3h")
    """
    try:
        import pytz
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
        
        # Ensure target_time is timezone-aware
        if target_time.tzinfo is None:
            target_time = eastern.localize(target_time)
        
        delta = target_time - now
        
        if delta.total_seconds() <= 0:
            return "now"
        
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m {seconds}s"
            
    except Exception:
        return "unknown"


def get_next_check_time(interval_minutes=2):
    """
    Calculate next check time
    
    Args:
        interval_minutes: Interval in minutes between checks (default: 2 for day trading)
        
    Returns:
        datetime: Next check time
    """
    now = datetime.now()
    next_check = now + timedelta(minutes=interval_minutes)
    return next_check


def should_close_positions(session_type: str = "regular") -> bool:
    """
    Check if it's time to close all positions for end of day
    
    Close time:
    - Regular market: Close at 3:55 PM ET (5 min before market close)
    - No extended hours trading (pre-market/post-market disabled)
    
    Args:
        session_type: Type of trading session (always "regular")
    
    Returns:
        bool: True if should close all positions (end of trading day)
    """
    try:
        import pytz
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
        current_time = now.time()
        
        # Close positions at 3:55 PM ET (5 minutes before market close)
        close_time = time(15, 55)  # 3:55 PM ET
        return current_time >= close_time
        
    except Exception as e:
        logging.error(f"❌ Error checking close time: {e}")
        return False


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
        logger.info(f"\n{'='*80}")
        logger.info(f"🔄 TRADING CYCLE #{cycle_number} - REGULAR SESSION")
        logger.info(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*80}\n")
        
        logging.info(f"Starting trading cycle #{cycle_number} (regular)")
        
        # Check if we should close all positions (at 3:55 PM ET)
        if should_close_positions(session_type):
            logging.warning(f"⏰ End of trading day (3:55 PM ET) - closing all positions")
            logger.info(f"⏰ End of trading day (3:55 PM ET) - closing all positions")
            try:
                # Close all positions before end of day
                logger.info("📉 Executing end-of-day position closure...")
                # TODO: Add actual close_all_positions() call here
            except Exception as e:
                logging.error(f"❌ Error closing positions: {e}")
                logger.info(f"❌ Error closing positions: {e}")
        
        # Get current date for trading
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Update runtime configuration
        write_config_value("TODAY_DATE", current_date)
        write_config_value("MARKET_SESSION", session_type)
        write_config_value("TA_ENABLED", "true" if TA_ENABLED else "false")
        
        # Run trading for current date with retry logic
        max_retries = 3
        for attempt in range(max_retries):
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
        
        # Display position summary
        try:
            summary = agent.get_position_summary()
            logger.info(f"\n{'='*80}")
            logger.info(f"📊 CYCLE #{cycle_number} SUMMARY (REGULAR)")
            logger.info(f"{'='*80}")
            logger.info(f"📅 Date: {summary.get('latest_date')}")
            logger.info(f"📝 Total records: {summary.get('total_records')}")
            logger.info(f"💵 Cash balance: ${summary.get('positions', {}).get('CASH', 0):.2f}")
            
            # Show current positions
            positions = summary.get('positions', {})
            if len(positions) > 1:  # More than just CASH
                logger.info(f"\n📈 ACTIVE POSITIONS:")
                total_value = 0
                for symbol, amount in positions.items():
                    if symbol != 'CASH' and amount != 0:
                        logger.info(f"   ├─ {symbol}: {amount} shares")
                        # Note: Would need current price to calculate value
                logger.info(f"\n💼 Total positions: {len([s for s in positions.keys() if s != 'CASH' and positions[s] != 0])}")
            else:
                logger.info(f"\n📊 No active positions (100% cash)")
            
            logger.info(f"{'='*80}")
            logging.info(f"✅ Cycle #{cycle_number} completed successfully")
        except Exception as e:
            logging.warning(f"⚠️  Could not get position summary: {e}")
        
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


async def active_trading_loop(config_path=None, interval_minutes=2):
    """
    Main active day trading loop - runs continuously checking positions and trading every 2 minutes
    
    Designed for high-frequency day trading with robust error handling and auto-recovery.
    
    Args:
        config_path: Configuration file path
        interval_minutes: Minutes between trading cycles (default: 2 for day trading)
    """
    global shutdown_requested
    
    logging.info("🚀 Starting Active Day Trading Program")
    
    # Load configuration
    config = load_config(config_path)
    
    # Get Agent type
    agent_type = config.get("agent_type", "BaseAgent")
    try:
        AgentClass = get_agent_class(agent_type)
    except (ValueError, ImportError, AttributeError) as e:
        logging.error(str(e))
        logger.info(str(e))
        exit(1)
    
    # Get model list (only enabled models)
    enabled_models = [
        model for model in config["models"] 
        if model.get("enabled", True)
    ]
    
    if not enabled_models:
        error_msg = "❌ No enabled models found in configuration"
        logging.error(error_msg)
        logger.info(error_msg)
        exit(1)
    
    # Use first enabled model
    model_config = enabled_models[0]
    model_name = model_config.get("name", "unknown")
    basemodel = model_config.get("basemodel")
    signature = model_config.get("signature")
    openai_base_url = model_config.get("openai_base_url", None)
    openai_api_key = model_config.get("openai_api_key", None)
    
    # Get agent configuration
    agent_config = config.get("agent_config", {})
    log_config = config.get("log_config", {})
    max_steps = agent_config.get("max_steps", 10)
    max_retries = agent_config.get("max_retries", 3)
    base_delay = agent_config.get("base_delay", 0.5)
    initial_cash = agent_config.get("initial_cash", 10000.0)
    log_path = log_config.get("log_path", "./data/agent_data")
    
    # Get current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    logger.info("🚀 ACTIVE DAY TRADING PROGRAM STARTED")
    logger.info(f"{'='*80}")
    logger.info(f"🤖 Agent type: {agent_type}")
    logger.info(f"📅 Start date: {current_date}")
    logger.info(f"🤖 Model: {model_name} ({signature})")
    logger.info(f"⏱️  Check interval: {interval_minutes} minutes (HIGH FREQUENCY)")
    logger.info(f"⚙️  Agent config: max_steps={max_steps}, max_retries={max_retries}")
    logger.info(f"💰 Initial cash: ${initial_cash:.2f}")
    logger.info(f"📊 Regular Market Hours ONLY:")
    logger.info(f"   └─ 🟢 Regular:     9:30 AM - 4:00 PM ET")
    logger.info(f"   📝 Note: Pre-market and post-market trading DISABLED")
    logger.info(f"   � Positions close at 3:55 PM ET (5 min before market close)")
    logger.info(f"🛡️  Error handling: Auto-retry with graceful degradation")
    logger.info(f"{'='*80}\n")
    
    logging.info(f"Agent: {agent_type}, Model: {model_name}, Interval: {interval_minutes}min")
    
    # Initialize runtime configuration
    write_config_value("SIGNATURE", signature)
    write_config_value("TODAY_DATE", current_date)
    write_config_value("IF_TRADE", False)
    
    agent = None
    cycle_number = 0
    consecutive_failures = 0
    max_consecutive_failures = 5  # Increased for robustness
    initialization_retries = 0
    
    while not shutdown_requested:
        try:
            # Initialize or re-initialize agent if needed
            if agent is None:
                # Wait for MCP services to be ready before initializing
                mcp_ready = await wait_for_mcp_services(timeout=60)
                if not mcp_ready:
                    logger.warning("⚠️  MCP services not available, will retry initialization later...")
                    await asyncio.sleep(CONNECTION_RETRY_DELAY)
                    continue
                
                logger.info("🔧 Initializing trading agent...")
                logging.info("Initializing trading agent...")
                
                try:
                    agent = AgentClass(
                        signature=signature,
                        basemodel=basemodel,
                        stock_symbols=all_nasdaq_100_symbols,
                        log_path=log_path,
                        openai_base_url=openai_base_url,
                        openai_api_key=openai_api_key,
                        max_steps=max_steps,
                        max_retries=max_retries,
                        base_delay=base_delay,
                        initial_cash=initial_cash,
                        init_date=current_date
                    )
                    
                    logger.info(f"✅ {agent_type} instance created successfully")
                    logging.info(f"{agent_type} instance created successfully")
                    
                    # Initialize MCP connection and AI model with retry
                    for retry in range(MAX_CONNECTION_RETRIES):
                        try:
                            await agent.initialize()
                            logger.info("✅ Agent initialization complete")
                            logging.info("Agent initialization complete")
                            initialization_retries = 0
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
                    
                except Exception as e:
                    logging.error(f"❌ Fatal error during agent initialization: {e}")
                    logging.error(f"Traceback: {traceback.format_exc()}")
                    initialization_retries += 1
                    
                    if initialization_retries >= MAX_CONNECTION_RETRIES:
                        logger.info(f"❌ Failed to initialize after {MAX_CONNECTION_RETRIES} attempts. Exiting.")
                        break
                    
                    logger.info(f"⚠️  Initialization failed, will retry in {CONNECTION_RETRY_DELAY}s...")
                    await asyncio.sleep(CONNECTION_RETRY_DELAY)
                    continue
            
            cycle_number += 1
            
            # Check if within regular market hours (9:30 AM - 4:00 PM ET)
            is_open, session_type = is_market_hours()
            
            if not is_open:
                try:
                    import pytz
                    eastern = pytz.timezone('US/Eastern')
                    now = datetime.now(eastern)
                    
                    # Calculate next market open
                    next_open = get_next_market_open()
                    
                    if next_open:
                        time_until = format_time_until(next_open)
                        logger.info(f"\n{'='*80}")
                        logger.info(f"💤 MARKET CLOSED - INTELLIGENT SLEEP MODE")
                        logger.info(f"{'='*80}")
                        logger.info(f"⏰ Current time: {now.strftime('%A, %B %d, %Y at %I:%M:%S %p ET')}")
                        logger.info(f"")
                        logger.info(f"📅 Regular Market Hours ONLY:")
                        logger.info(f"   └─ 🟢 Regular: 9:30 AM - 4:00 PM ET")
                        logger.info(f"   📝 Pre-market and post-market trading DISABLED")
                        logger.info(f"")
                        logger.info(f"⏭️  Next market opens: {next_open.strftime('%A, %B %d at %I:%M %p ET')}")
                        logger.info(f"⏳ Time until open: {time_until}")
                        logger.info(f"")
                        logger.info(f"� Entering intelligent sleep mode - CPU usage minimized")
                        logger.info(f"⏰ Will wake up 5 minutes before market open for preparation")
                        logger.info(f"{'='*80}\n")
                        
                        logging.info(f"Market closed. Next open: {next_open.strftime('%Y-%m-%d %H:%M ET')} ({time_until})")
                        
                        # Calculate sleep duration
                        # Wake up 5 minutes before market open for agent preparation
                        wake_up_time = next_open - timedelta(minutes=5)
                        sleep_seconds = (wake_up_time - now).total_seconds()
                        
                        if sleep_seconds > 60:  # More than 1 minute until wake up
                            logger.info(f"😴 Sleeping until {wake_up_time.strftime('%I:%M:%S %p ET')} (wake up 5 min before market)...")
                            
                            # Sleep in 60-second chunks to allow periodic status updates and shutdown checks
                            total_sleep = int(sleep_seconds)
                            sleep_chunk = 60  # Check every minute
                            
                            for elapsed in range(0, total_sleep, sleep_chunk):
                                if shutdown_requested:
                                    logger.info("🛑 Shutdown requested during sleep mode")
                                    break
                                
                                remaining = total_sleep - elapsed
                                
                                # Show countdown every 5 minutes or every minute if < 10 min remaining
                                if remaining <= 600 or elapsed % 300 == 0:
                                    remaining_formatted = format_time_until(wake_up_time)
                                    logger.info(f"💤 Sleep mode active - Wake up in: {remaining_formatted}")
                                
                                # Sleep for up to sleep_chunk seconds or remaining time
                                actual_sleep = min(sleep_chunk, remaining)
                                await asyncio.sleep(actual_sleep)
                            
                            if not shutdown_requested:
                                logger.info(f"\n{'='*80}")
                                logger.info(f"⏰ WAKE UP - Preparing for market open in 5 minutes")
                                logger.info(f"🔄 Agent will start processing when market opens at 9:30 AM ET")
                                logger.info(f"{'='*80}\n")
                        else:
                            # Less than 1 minute - just do a quick sleep
                            if sleep_seconds > 0:
                                await asyncio.sleep(sleep_seconds)
                    else:
                        logger.info(f"⏸️  Market closed. Current time: {now.strftime('%H:%M:%S ET')}")
                        logger.info(f"   Next check in {interval_minutes} minutes...")
                        logging.info(f"Market closed at {now.strftime('%H:%M:%S ET')}")
                        
                        # Sleep for interval
                        for _ in range(interval_minutes * 60):
                            if shutdown_requested:
                                break
                            await asyncio.sleep(1)
                except Exception as e:
                    logger.info(f"⏸️  Market closed. Next check in {interval_minutes} minutes...")
                    logging.error(f"Error calculating market status: {e}")
                    
                    # Sleep for interval on error
                    for _ in range(interval_minutes * 60):
                        if shutdown_requested:
                            break
                        await asyncio.sleep(1)
                continue
            
            # Run trading cycle
            logger.info(f"🟢 Market is open - REGULAR session")
            logging.info(f"Market open - regular session, starting cycle #{cycle_number}")
            
            success = await run_trading_cycle(agent, cycle_number, session_type)
            
            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                logging.warning(f"⚠️  Consecutive failures: {consecutive_failures}/{max_consecutive_failures}")
                logger.info(f"⚠️  Consecutive failures: {consecutive_failures}/{max_consecutive_failures}")
                
                # On repeated failures, try to reinitialize agent
                if consecutive_failures >= 3:
                    logging.warning("⚠️  Multiple failures detected, will reinitialize agent")
                    logger.info("⚠️  Multiple failures detected, attempting to reinitialize agent...")
                    agent = None  # Force re-initialization
                
                if consecutive_failures >= max_consecutive_failures:
                    logging.error(f"❌ Maximum consecutive failures ({max_consecutive_failures}) reached")
                    logger.info(f"❌ Maximum consecutive failures reached. Stopping program.")
                    break
            
            if shutdown_requested:
                break
            
            # Calculate next check time
            next_check = get_next_check_time(interval_minutes)
            wait_seconds = interval_minutes * 60
            
            logger.info(f"\n⏳ Next trading cycle at: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"💤 Sleeping for {interval_minutes} minutes...")
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
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                logging.error("Too many failures, stopping")
                break
            
            # Force re-initialization
            agent = None
            logger.info(f"⚠️  Will attempt recovery in {CONNECTION_RETRY_DELAY}s...")
            await asyncio.sleep(CONNECTION_RETRY_DELAY)
    
    # Cleanup and final summary
    logger.info(f"\n{'='*80}")
    logger.info("🛑 ACTIVE DAY TRADING PROGRAM STOPPED")
    logger.info(f"📊 Total cycles completed: {cycle_number}")
    logging.info(f"Program stopped. Total cycles: {cycle_number}")
    
    # Final summary
    if agent is not None:
        try:
            final_summary = agent.get_position_summary()
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
    logger.info(f"🎯 Day Trading Mode: High-frequency with robust error handling\n")
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
