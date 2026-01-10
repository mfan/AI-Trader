"""
Market Schedule Utilities

Handles market hours detection, session management, and time calculations.
"""
import logging
from datetime import datetime, time, timedelta, date as dt_date
from typing import Tuple, Optional
import pytz

from tools.alpaca_trading import get_alpaca_client
from alpaca.trading.requests import GetCalendarRequest

logger = logging.getLogger(__name__)

def is_market_hours() -> Tuple[bool, str]:
    """
    Check if current time is within market hours using Alpaca's clock API
    
    Returns:
        tuple: (is_open, session_type) where session_type is one of:
               "pre", "regular", "post", or "closed"
    """
    try:
        # Try to use Alpaca's clock API for accurate market status
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
                pass
                
        except Exception as api_error:
            logger.warning(f"⚠️  Alpaca clock API unavailable: {api_error}")
            logger.info("   Falling back to time-based market hours check")
            # Fall through to time-based check
        
        # Fallback: Time-based check with extended hours support
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
    
    Returns:
        tuple: (should_close, close_time_dt)
    """
    try:
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
                    close_value = day_info.session_close
                else:
                    close_value = day_info.close
                
                # Parse close time - handle both datetime objects and time strings
                # Alpaca may return datetime (e.g., "2026-01-05 16:00:00") or time ("16:00:00")
                if hasattr(close_value, 'hour') and hasattr(close_value, 'minute'):
                    # It's a datetime or time object
                    market_close_time = time(close_value.hour, close_value.minute)
                else:
                    # It's a string - extract time portion
                    market_close_str = str(close_value)
                    # Handle "YYYY-MM-DD HH:MM:SS" format by splitting on space first
                    if ' ' in market_close_str:
                        market_close_str = market_close_str.split(' ')[1]
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
        elif session_type == "regular":
             # Regular hours: close at 3:45 PM (15 min before 4:00 PM)
            deadline_time = time(15, 45)
        else:
            # Pre-market: No forced close, transition to regular
            return False, None
        
        close_deadline_dt = now.replace(hour=deadline_time.hour, minute=deadline_time.minute, second=0, microsecond=0)
        should_close = current_time >= deadline_time
        
        return should_close, close_deadline_dt
        
    except Exception as e:
        logging.error(f"❌ Error checking close time: {e}")
        return False, None
