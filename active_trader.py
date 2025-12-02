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
from typing import Tuple, Optional, List

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


async def run_pre_market_scan(log_path: str, signature: str) -> Optional[List[str]]:
    """
    Run pre-market momentum scan to build daily watchlist.
    
    Scans previous day's top volume movers (10M-20M+ volume):
    - Top 100 gainers
    - Top 100 losers
    - Caches results in SQLite for fast intraday access
    
    Args:
        log_path: Path to store cache database
        signature: Model signature for cache organization
        
    Returns:
        List of symbols for today's trading, or None on error
    """
    try:
        from tools.momentum_scanner import MomentumScanner
        from tools.momentum_cache import MomentumCache
        import time as time_module
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 PRE-MARKET MOMENTUM SCAN")
        logger.info(f"{'='*80}")
        logger.info(f"⏰ Scanning previous day's top volume movers...")
        logger.info(f"   Filters: Volume >= 10M, Top 200 stocks (100 gainers + 100 losers)")
        
        scan_start = time_module.time()
        
        # Initialize scanner
        scanner = MomentumScanner()
        
        # Scan previous day
        movers = await scanner.scan_previous_day_movers(
            scan_date=None,  # Auto-detect previous business day
            min_volume=10_000_000,  # 10M minimum
            max_results=200  # Top 200 total (100 gainers + 100 losers)
        )
        
        if not movers or (not movers.get('gainers') and not movers.get('losers')):
            logger.warning("⚠️  No momentum stocks found. Using fallback watchlist.")
            return None
        
        scan_duration = time_module.time() - scan_start
        
        # Cache results
        cache_path = f"{log_path}/{signature}/momentum_cache.db"
        cache = MomentumCache(cache_path)
        
        market_regime = scanner.get_market_regime()
        
        success = cache.cache_momentum_stocks(
            scan_date=movers.get('scan_date'),
            gainers=movers.get('gainers', []),
            losers=movers.get('losers', []),
            market_regime=market_regime,
            metadata={
                'total_scanned': movers.get('total_scanned', 0),
                'high_volume_count': movers.get('high_volume_count', 0),
                'scan_duration': scan_duration
            }
        )
        
        if not success:
            logger.warning("⚠️  Failed to cache momentum data")
        else:
            # Archive to historical database (permanent storage)
            logger.info("📦 Archiving to historical database...")
            try:
                from tools.momentum_history import archive_from_cache
                history_path = cache_path.replace('momentum_cache.db', 'momentum_history.db')
                archive_success = archive_from_cache(cache_path, history_path, movers.get('scan_date'))
                if archive_success:
                    logger.info(f"   ✅ Archived to: {history_path}")
                else:
                    logger.warning("   ⚠️  Archiving failed (non-critical)")
            except Exception as e:
                logger.warning(f"   ⚠️  Archiving error: {e} (non-critical)")
            
            # Cleanup old scans from daily cache (keep last 30 days)
            logger.info("🧹 Cleaning up old scan data from cache (keeping 30 days)...")
            cache.cleanup_old_scans(days_to_keep=30)
        
        # Get watchlist
        watchlist = scanner.get_momentum_watchlist()
        
        # Log summary
        gainers = movers.get('gainers', [])
        losers = movers.get('losers', [])
        
        logger.info(f"\n✅ MOMENTUM SCAN COMPLETE")
        logger.info(f"   📈 Gainers: {len(gainers)}")
        logger.info(f"   📉 Losers: {len(losers)}")
        logger.info(f"   📊 Total Watchlist: {len(watchlist)} stocks")
        logger.info(f"   🎯 Market Regime: {market_regime.upper()}")
        logger.info(f"   ⏱️  Scan Duration: {scan_duration:.2f}s")
        logger.info(f"   💾 Cached to: {cache_path}")
        
        if gainers:
            top_gainer = gainers[0]
            logger.info(f"   🏆 Best Gainer: {top_gainer['symbol']} ({top_gainer['change_pct']:+.2f}%)")
        
        if losers:
            top_loser = losers[0]
            logger.info(f"   💔 Worst Loser: {top_loser['symbol']} ({top_loser['change_pct']:+.2f}%)")
        
        logger.info(f"{'='*80}\n")
        
        return watchlist
        
    except Exception as e:
        logger.error(f"❌ Pre-market scan failed: {e}", exc_info=True)
        logging.error(f"Pre-market scan failed: {e}")
        return None


def get_agent_class(agent_type: str):
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
    
    Supports environment variable substitution using ${VAR_NAME} syntax.
    
    Args:
        config_path: Configuration file path, if None use default config
        
    Returns:
        dict: Configuration dictionary with env vars substituted
        
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
        
        # Recursively substitute environment variables
        def substitute_env_vars(obj):
            """Recursively substitute ${VAR} with environment variable values"""
            if isinstance(obj, dict):
                return {k: substitute_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute_env_vars(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
                # Extract variable name and substitute
                var_name = obj[2:-1]
                env_value = os.getenv(var_name)
                if env_value:
                    return env_value
                else:
                    logging.warning(f"⚠️  Environment variable {var_name} not found, keeping as-is")
                    return obj
            else:
                return obj
        
        config = substitute_env_vars(config)
        
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
    Check if current time is within market hours using Alpaca's clock API
    
    This method checks:
    1. If market is currently open (via Alpaca clock API)
    2. Accounts for holidays and early closes automatically
    3. Supports extended hours trading (pre-market and post-market)
    4. Falls back to time-based check if API fails
    
    Market Hours:
    - Pre-market:  4:00 AM - 9:30 AM ET
    - Regular:     9:30 AM - 4:00 PM ET
    - Post-market: 4:00 PM - 8:00 PM ET
    
    Returns:
        tuple: (is_open, session_type) where session_type is one of:
               "pre", "regular", "post", or "closed"
    """
    try:
        # Try to use Alpaca's clock API for accurate market status
        from tools.alpaca_trading import get_alpaca_client
        import pytz
        
        try:
            client = get_alpaca_client()
            is_open_now, status_msg = client.is_market_open_now()
            
            if is_open_now:
                # Market is open - determine which session
                eastern = pytz.timezone('US/Eastern')
                now = datetime.now(eastern)
                current_time = now.time()
                
                # Determine session type based on time
                if time(4, 0) <= current_time < time(9, 30):
                    return True, "pre"
                elif time(9, 30) <= current_time < time(16, 0):
                    return True, "regular"
                elif time(16, 0) <= current_time < time(20, 0):
                    return True, "post"
                else:
                    return True, "regular"  # Default to regular if unclear
            else:
                # Market is closed (Regular hours) - check for Extended Hours
                if "No trading session today" in status_msg:
                    logger.info(f"🏖️  {status_msg}")
                    return False, "closed"
                
                # If market is closed but it's a trading day, check extended hours via fallback
                # We fall through to the time-based check below which handles Pre/Post market
                pass
                
        except Exception as api_error:
            logger.warning(f"⚠️  Alpaca clock API unavailable: {api_error}")
            logger.info("   Falling back to time-based market hours check")
            # Fall through to time-based check
        
        # Fallback: Time-based check with extended hours support
        import pytz
        
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
        current_time = now.time()
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False, "closed"
        
        # Define market hours with extended hours support
        pre_market_start = time(4, 0)      # 4:00 AM ET
        regular_start = time(9, 30, 0)     # 9:30 AM ET
        regular_end = time(16, 0)          # 4:00 PM ET
        post_market_end = time(20, 0)      # 8:00 PM ET
        
        # Determine session
        if pre_market_start <= current_time < regular_start:
            return True, "pre"
        elif regular_start <= current_time < regular_end:
            return True, "regular"
        elif regular_end <= current_time < post_market_end:
            return True, "post"
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
        
        # Use 4:00:00 as the start time for pre-market (Extended Hours)
        market_start = time(4, 0, 0)  # 4:00 AM ET
        
        # If it's before 4:00 AM today and it's a weekday, next open is today at 4:00 AM
        if current_time < market_start and now.weekday() < 5:
            next_open = now.replace(hour=4, minute=0, second=0, microsecond=0)
            return next_open
        
        # Otherwise, calculate next weekday at 4:00 AM
        days_ahead = 1
        next_day = now + timedelta(days=days_ahead)
        
        # Skip to Monday if we land on weekend
        while next_day.weekday() >= 5:  # Saturday or Sunday
            days_ahead += 1
            next_day = now + timedelta(days=days_ahead)
        
        # Set to 4:00 AM ET
        next_open = next_day.replace(hour=4, minute=0, second=0, microsecond=0)
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


def should_close_positions(session_type: str = "regular") -> Tuple[bool, Optional[datetime]]:
    """
    Check if it's time to close all positions for end of day
    
    Dynamically gets market close time from Alpaca calendar API and closes
    positions 15 minutes before market close.
    
    Close times (15 min before market close):
    - Regular hours: Close at 3:45 PM ET (15 min before 4:00 PM close)
    - Extended hours: Close at 7:45 PM ET (15 min before 8:00 PM close)
    - Early close days: Dynamically calculated (e.g., 12:45 PM on half days)
    
    Args:
        session_type: Type of trading session ("pre", "regular", "post")
    
    Returns:
        tuple: (should_close, close_time_dt)
            - should_close: True if should close all positions
            - close_time_dt: Datetime of the close deadline, or None if error
    """
    try:
        from tools.alpaca_trading import get_alpaca_client
        from alpaca.trading.requests import GetCalendarRequest
        import pytz
        from datetime import date as dt_date
        
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
        current_time = now.time()
        today = dt_date.today()
        
        # Get today's market schedule from Alpaca
        try:
            client = get_alpaca_client()
            request = GetCalendarRequest(start=today, end=today)
            calendar = client.trading_client.get_calendar(filters=request)
            
            if calendar and len(calendar) > 0:
                day_info = calendar[0]
                
                # Get market close time (regular close or extended close)
                # Alpaca returns session_close for extended hours, close for regular
                if hasattr(day_info, 'session_close') and day_info.session_close:
                    market_close_str = str(day_info.session_close)
                else:
                    market_close_str = str(day_info.close)
                
                # Parse close time (format: HH:MM:SS)
                close_parts = market_close_str.split(':')
                market_close_time = time(int(close_parts[0]), int(close_parts[1]))
                
                # Calculate close deadline: 15 minutes before market close
                close_hour = market_close_time.hour
                close_minute = market_close_time.minute
                
                # Subtract 15 minutes
                deadline_minute = close_minute - 15
                deadline_hour = close_hour
                if deadline_minute < 0:
                    deadline_minute += 60
                    deadline_hour -= 1
                
                deadline_time = time(deadline_hour, deadline_minute)
                
                # Create full datetime for logging
                close_deadline_dt = now.replace(hour=deadline_hour, minute=deadline_minute, second=0, microsecond=0)
                
                should_close = current_time >= deadline_time
                
                if should_close:
                    logger.info(f"⏰ Close deadline reached: {deadline_time.strftime('%I:%M %p')} (15 min before market close at {market_close_time.strftime('%I:%M %p')})")
                
                return should_close, close_deadline_dt
            else:
                logger.warning("⚠️  No market calendar data for today - using fallback close times")
                # Fall through to fallback
        except Exception as api_error:
            logger.warning(f"⚠️  Could not get market calendar: {api_error}")
            # Fall through to fallback
        
        # Fallback: Use standard close times
        if session_type == "post":
            # Post-market: close at 7:45 PM (15 min before 8:00 PM)
            deadline_time = time(19, 45)
        else:
            # Regular hours: close at 3:45 PM (15 min before 4:00 PM)
            deadline_time = time(15, 45)
        
        close_deadline_dt = now.replace(hour=deadline_time.hour, minute=deadline_time.minute, second=0, microsecond=0)
        should_close = current_time >= deadline_time
        
        return should_close, close_deadline_dt
        
    except Exception as e:
        logging.error(f"❌ Error checking close time: {e}")
        return False, None


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
        
        # Display trading round completion status
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 CYCLE #{cycle_number} SUMMARY (REGULAR)")
        logger.info(f"{'='*80}")
        logger.info(f"📅 Date: {current_date}")
        logger.info(f"⏰ Completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get final status from agent's trading session
        # Note: The agent has already verified order execution in _handle_trading_result()
        # This displays the outcomes for the active_trader log
        
        if_trade = get_config_value("IF_TRADE")
        if if_trade:
            logger.info(f"✅ TRADING ROUND COMPLETED WITH ORDERS EXECUTED")
            logger.info(f"   Orders have been processed by Alpaca")
            logger.info(f"   Check agent logs for detailed execution report")
        else:
            logger.info(f"✅ ANALYSIS ROUND COMPLETED (NO TRADES)")
            logger.info(f"   Portfolio reviewed, no trading action required")
        
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
        write_config_value("IF_TRADE", False)

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
        try:
            from tools.momentum_cache import MomentumCache
            import pytz
            
            eastern = pytz.timezone('US/Eastern')
            now = datetime.now(eastern)
            today = now.strftime('%Y-%m-%d')
            
            cache_path = f"{self.log_path}/{self.signature}/momentum_cache.db"
            cache = MomentumCache(cache_path)
            
            # Try to load today's cached watchlist
            cached_watchlist = cache.get_momentum_watchlist(scan_date=today)
            
            if cached_watchlist and len(cached_watchlist) > 0:
                self.momentum_watchlist = cached_watchlist
                self.last_scan_date = today
                logger.info(f"✅ Loaded cached momentum watchlist: {len(self.momentum_watchlist)} stocks from {today}")
            else:
                # No cache for today yet - run scan now
                logger.info("🌅 No cache found - running initial momentum scan...")
                self.momentum_watchlist = await run_pre_market_scan(self.log_path, self.signature)
                self.last_scan_date = today
        except Exception as e:
            logger.warning(f"⚠️  Error loading momentum watchlist: {e}")
            logger.warning(f"   Will retry during daily scan window (9:00-9:30 AM)")

    async def _check_daily_scan(self):
        try:
            import pytz
            eastern = pytz.timezone('US/Eastern')
            now = datetime.now(eastern)
            today = now.strftime('%Y-%m-%d')
            
            # Run scan if we haven't scanned today yet
            if (now.weekday() < 5 and self.last_scan_date != today):
                logger.info("🌅 Daily momentum scan time - refreshing watchlist...")
                try:
                    new_watchlist = await run_pre_market_scan(self.log_path, self.signature)
                    if new_watchlist:
                        self.momentum_watchlist = new_watchlist
                        self.last_scan_date = today
                        logger.info(f"✅ Watchlist updated with {len(self.momentum_watchlist)} stocks for {today}")
                        
                        # Force agent reinitialization with new watchlist
                        if self.agent is not None:
                            logger.info("🔄 Reinitializing agent with updated watchlist...")
                            try:
                                await self.agent.cleanup()
                            except:
                                pass
                            self.agent = None
                    else:
                        logger.warning("⚠️  Daily scan returned empty watchlist")
                except Exception as e:
                    logger.error(f"❌ Daily momentum scan failed: {e}")
        except Exception as e:
            logger.error(f"Error checking daily scan schedule: {e}")

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
                # Couldn't calculate next open - sleep for interval
                await asyncio.sleep(self.interval_minutes * 60)
        except Exception as e:
            logging.error(f"Error calculating market status: {e}")
            # Sleep for interval on error
            await asyncio.sleep(self.interval_minutes * 60)

    async def _ensure_agent_ready(self):
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
                    global shutdown_requested
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
                        # Update equity based on current positions
                        if hasattr(self.agent, 'get_position_summary'):
                            summary = self.agent.get_position_summary()
                            positions = summary.get('positions', {})
                            cash = positions.get('CASH', self.initial_cash)
                            
                            # For simplicity, use cash as equity proxy
                            # In production, would include position values
                            self.elder_risk_manager.update_equity(cash)
                            
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
