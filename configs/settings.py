"""
Centralized Configuration for AI Trader
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Base Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

class TradingConfig:
    """Trading Strategy Parameters"""
    # Momentum Scanner Filters
    MIN_PRICE = 5.0
    MIN_VOLUME = 10_000_000
    IDEAL_VOLUME = 20_000_000
    MIN_MARKET_CAP = 2_000_000_000
    
    # Watchlist Size
    TOP_GAINERS_COUNT = 100
    TOP_LOSERS_COUNT = 100
    TOTAL_WATCHLIST_SIZE = 200
    
    # Risk Management (Elder's Rules)
    MAX_RISK_PER_TRADE = 0.02  # 2%
    MAX_DRAWDOWN_LIMIT = 0.06  # 6%
    MAX_POSITION_SIZE = 0.20   # 20%

class SystemConfig:
    """System Operational Parameters"""
    # Connection Retries
    MAX_CONNECTION_RETRIES = 5
    CONNECTION_RETRY_DELAY = 30
    
    # MCP Services
    MCP_HEALTH_CHECK_RETRIES = 10
    MCP_HEALTH_CHECK_DELAY = 5
    MCP_WAIT_TIMEOUT = 60
    
    # API Retries
    API_MAX_RETRIES = 3
    API_RETRY_DELAY = 1.0
    API_BACKOFF_FACTOR = 2.0

class AgentConfig:
    """Agent Runtime Configuration"""
    MAX_STEPS = 30
    MAX_RETRIES = 3
    BASE_DELAY = 1.0
    INITIAL_CASH = 10000.0

def load_config_from_json(json_path: Path = PROJECT_ROOT / "configs" / "default_config.json") -> Dict[str, Any]:
    """Load configuration overrides from JSON file"""
    if not json_path.exists():
        return {}
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load config from {json_path}: {e}")
        return {}

# Load overrides
_json_config = load_config_from_json()

# Apply overrides if they exist (simple mapping for now)
if "agent_config" in _json_config:
    ac = _json_config["agent_config"]
    AgentConfig.MAX_STEPS = ac.get("max_steps", AgentConfig.MAX_STEPS)
    AgentConfig.MAX_RETRIES = ac.get("max_retries", AgentConfig.MAX_RETRIES)
    AgentConfig.BASE_DELAY = ac.get("base_delay", AgentConfig.BASE_DELAY)
    AgentConfig.INITIAL_CASH = ac.get("initial_cash", AgentConfig.INITIAL_CASH)
