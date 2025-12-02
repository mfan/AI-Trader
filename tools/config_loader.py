"""
Configuration Loader

Handles loading and parsing of JSON configuration files with environment variable substitution.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
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
        # Assuming this is run from project root or similar structure
        # Adjust path resolution as needed
        base_path = Path(os.getcwd())
        config_path = base_path / "configs" / "default_config.json"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        # Try relative to project root if absolute path fails
        base_path = Path(os.getcwd())
        alt_path = base_path / config_path
        if alt_path.exists():
            config_path = alt_path
        else:
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
