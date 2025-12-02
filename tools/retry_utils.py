"""
Retry Utilities for Robust API Calls
"""
import time
import asyncio
import logging
import functools
from typing import Type, Tuple, Union, Callable, Any

logger = logging.getLogger(__name__)

def retry_with_backoff(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    Supports both sync and async functions.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == retries:
                        logger.error(f"❌ {func.__name__} failed after {retries} retries: {e}")
                        raise last_exception
                    
                    logger.warning(f"⚠️ {func.__name__} failed (Attempt {attempt + 1}/{retries}): {e}. Retrying in {current_delay}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == retries:
                        logger.error(f"❌ {func.__name__} failed after {retries} retries: {e}")
                        raise last_exception
                    
                    logger.warning(f"⚠️ {func.__name__} failed (Attempt {attempt + 1}/{retries}): {e}. Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
