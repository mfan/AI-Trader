#!/usr/bin/env python3
"""
Active Trading Program - Continuous Portfolio Management
Runs continuously during market hours, checking positions and making trading decisions every 10 minutes.
"""

import os
import asyncio
from datetime import datetime, time, timedelta
import json
from pathlib import Path
from dotenv import load_dotenv
import signal
import sys

load_dotenv()

# Import tools and prompts
from tools.general_tools import get_config_value, write_config_value
from prompts.agent_prompt import all_nasdaq_100_symbols


# Agent class mapping table
AGENT_REGISTRY = {
    "BaseAgent": {
        "module": "agent.base_agent.base_agent",
        "class": "BaseAgent"
    },
}

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global shutdown_requested
    print("\n⚠️  Shutdown signal received. Finishing current cycle...")
    shutdown_requested = True


def get_agent_class(agent_type):
    """
    Dynamically import and return the corresponding class based on agent type name
    
    Args:
        agent_type: Agent type name (e.g., "BaseAgent")
        
    Returns:
        Agent class
    """
    if agent_type not in AGENT_REGISTRY:
        supported_types = ", ".join(AGENT_REGISTRY.keys())
        raise ValueError(
            f"❌ Unsupported agent type: {agent_type}\n"
            f"   Supported types: {supported_types}"
        )
    
    agent_info = AGENT_REGISTRY[agent_type]
    module_path = agent_info["module"]
    class_name = agent_info["class"]
    
    try:
        import importlib
        module = importlib.import_module(module_path)
        agent_class = getattr(module, class_name)
        print(f"✅ Successfully loaded Agent class: {agent_type} (from {module_path})")
        return agent_class
    except ImportError as e:
        raise ImportError(f"❌ Unable to import agent module {module_path}: {e}")
    except AttributeError as e:
        raise AttributeError(f"❌ Class {class_name} not found in module {module_path}: {e}")


def load_config(config_path=None):
    """
    Load configuration file from configs directory
    
    Args:
        config_path: Configuration file path, if None use default config
        
    Returns:
        dict: Configuration dictionary
    """
    if config_path is None:
        config_path = Path(__file__).parent / "configs" / "default_config.json"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        print(f"❌ Configuration file does not exist: {config_path}")
        exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"✅ Successfully loaded configuration file: {config_path}")
        return config
    except json.JSONDecodeError as e:
        print(f"❌ Configuration file JSON format error: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ Failed to load configuration file: {e}")
        exit(1)


def is_market_hours():
    """
    Check if current time is within market hours (including extended hours)
    
    Market hours (Eastern Time):
    - Pre-market: 4:00 AM - 9:30 AM ET
    - Regular: 9:30 AM - 4:00 PM ET
    - Post-market: 4:00 PM - 8:00 PM ET
    
    Returns:
        tuple: (is_open, session_type) where session_type is one of:
               "pre-market", "regular", "post-market", or "closed"
    """
    import pytz
    
    # Get current time in Eastern Time
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    current_time = now.time()
    
    # Check if it's a weekday (Monday=0, Sunday=6)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False, "closed"
    
    # Define market hours (Eastern Time)
    pre_market_start = time(4, 0)     # 4:00 AM ET
    regular_start = time(9, 30)       # 9:30 AM ET
    regular_end = time(16, 0)         # 4:00 PM ET
    post_market_end = time(20, 0)     # 8:00 PM ET
    
    # Check which session we're in
    if pre_market_start <= current_time < regular_start:
        return True, "pre-market"
    elif regular_start <= current_time < regular_end:
        return True, "regular"
    elif regular_end <= current_time < post_market_end:
        return True, "post-market"
    else:
        return False, "closed"


def get_next_check_time(interval_minutes=10):
    """
    Calculate next check time
    
    Args:
        interval_minutes: Interval in minutes between checks
        
    Returns:
        datetime: Next check time
    """
    now = datetime.now()
    next_check = now + timedelta(minutes=interval_minutes)
    return next_check


async def run_trading_cycle(agent, cycle_number, session_type="regular"):
    """
    Run a single trading cycle
    
    Args:
        agent: Initialized agent instance
        cycle_number: Current cycle number
        session_type: Type of market session ("pre-market", "regular", or "post-market")
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"\n{'='*80}")
        print(f"🔄 TRADING CYCLE #{cycle_number} - {session_type.upper()} SESSION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        # Get current date for trading
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Update runtime configuration
        write_config_value("TODAY_DATE", current_date)
        write_config_value("MARKET_SESSION", session_type)
        
        # Run trading for current date
        await agent.run_date_range(current_date, current_date)
        
        # Display position summary
        summary = agent.get_position_summary()
        print(f"\n📊 CYCLE #{cycle_number} SUMMARY ({session_type}):")
        print(f"   ├─ Date: {summary.get('latest_date')}")
        print(f"   ├─ Total records: {summary.get('total_records')}")
        print(f"   ├─ Cash balance: ${summary.get('positions', {}).get('CASH', 0):.2f}")
        
        # Show current positions
        positions = summary.get('positions', {})
        if len(positions) > 1:  # More than just CASH
            print(f"   └─ Positions:")
            for symbol, amount in positions.items():
                if symbol != 'CASH' and amount != 0:
                    print(f"      ├─ {symbol}: {amount}")
        
        print(f"\n✅ Cycle #{cycle_number} completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error in trading cycle #{cycle_number}: {str(e)}")
        print(f"📋 Error details: {e}")
        return False


async def active_trading_loop(config_path=None, interval_minutes=10):
    """
    Main active trading loop - runs continuously checking positions and trading
    
    Args:
        config_path: Configuration file path
        interval_minutes: Minutes between trading cycles (default: 10)
    """
    global shutdown_requested
    
    # Load configuration
    config = load_config(config_path)
    
    # Get Agent type
    agent_type = config.get("agent_type", "BaseAgent")
    try:
        AgentClass = get_agent_class(agent_type)
    except (ValueError, ImportError, AttributeError) as e:
        print(str(e))
        exit(1)
    
    # Get model list (only enabled models)
    enabled_models = [
        model for model in config["models"] 
        if model.get("enabled", True)
    ]
    
    if not enabled_models:
        print("❌ No enabled models found in configuration")
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
    
    print("🚀 ACTIVE TRADING PROGRAM STARTED")
    print(f"{'='*80}")
    print(f"🤖 Agent type: {agent_type}")
    print(f"📅 Start date: {current_date}")
    print(f"🤖 Model: {model_name} ({signature})")
    print(f"⏱️  Check interval: {interval_minutes} minutes")
    print(f"⚙️  Agent config: max_steps={max_steps}, max_retries={max_retries}")
    print(f"💰 Initial cash: ${initial_cash:.2f}")
    print(f"{'='*80}\n")
    
    # Initialize runtime configuration
    write_config_value("SIGNATURE", signature)
    write_config_value("TODAY_DATE", current_date)
    write_config_value("IF_TRADE", False)
    
    try:
        # Create and initialize agent (only once)
        print("🔧 Initializing trading agent...")
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
        
        print(f"✅ {agent_type} instance created successfully")
        
        # Initialize MCP connection and AI model
        await agent.initialize()
        print("✅ Agent initialization complete")
        print("🎯 Starting continuous trading loop...\n")
        
        cycle_number = 0
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while not shutdown_requested:
            cycle_number += 1
            
            # Check if within market hours (including pre-market and post-market)
            is_open, session_type = is_market_hours()
            
            if not is_open:
                import pytz
                eastern = pytz.timezone('US/Eastern')
                now = datetime.now(eastern)
                print(f"⏸️  Market closed. Current time: {now.strftime('%H:%M:%S ET')}")
                print(f"   Market hours:")
                print(f"   ├─ Pre-market:  4:00 AM - 9:30 AM ET")
                print(f"   ├─ Regular:     9:30 AM - 4:00 PM ET")
                print(f"   └─ Post-market: 4:00 PM - 8:00 PM ET")
                print(f"   Next check in {interval_minutes} minutes...")
                await asyncio.sleep(interval_minutes * 60)
                continue
            
            # Run trading cycle with session type
            print(f"🟢 Market is open - {session_type.upper()} session")
            success = await run_trading_cycle(agent, cycle_number, session_type)
            
            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                print(f"⚠️  Consecutive failures: {consecutive_failures}/{max_consecutive_failures}")
                
                if consecutive_failures >= max_consecutive_failures:
                    print(f"❌ Maximum consecutive failures reached. Stopping program.")
                    break
            
            if shutdown_requested:
                break
            
            # Calculate next check time
            next_check = get_next_check_time(interval_minutes)
            wait_seconds = interval_minutes * 60
            
            print(f"\n⏳ Next trading cycle at: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"💤 Sleeping for {interval_minutes} minutes...")
            print(f"{'─'*80}\n")
            
            # Sleep until next check (with periodic wake-up to check shutdown flag)
            for _ in range(wait_seconds):
                if shutdown_requested:
                    break
                await asyncio.sleep(1)
        
        print(f"\n{'='*80}")
        print("🛑 ACTIVE TRADING PROGRAM STOPPED")
        print(f"📊 Total cycles completed: {cycle_number}")
        
        # Final summary
        final_summary = agent.get_position_summary()
        print(f"\n📊 FINAL PORTFOLIO SUMMARY:")
        print(f"   ├─ Latest date: {final_summary.get('latest_date')}")
        print(f"   ├─ Total records: {final_summary.get('total_records')}")
        print(f"   ├─ Cash balance: ${final_summary.get('positions', {}).get('CASH', 0):.2f}")
        
        positions = final_summary.get('positions', {})
        if len(positions) > 1:
            print(f"   └─ Final positions:")
            for symbol, amount in positions.items():
                if symbol != 'CASH' and amount != 0:
                    print(f"      ├─ {symbol}: {amount}")
        
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n❌ Fatal error in active trading loop: {str(e)}")
        print(f"📋 Error details: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Support command line arguments
    # Usage: python active_trader.py [config_path] [interval_minutes]
    # Example: python active_trader.py configs/default_config.json 10
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    interval_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    if config_path:
        print(f"📄 Using configuration file: {config_path}")
    else:
        print(f"📄 Using default configuration file: configs/default_config.json")
    
    print(f"⏱️  Trading interval: {interval_minutes} minutes\n")
    
    # Run the active trading loop
    asyncio.run(active_trading_loop(config_path, interval_minutes))
