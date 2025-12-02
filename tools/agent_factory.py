"""
Agent Factory

Handles dynamic loading and instantiation of trading agents.
"""
import logging
import importlib
from typing import Type, Any

logger = logging.getLogger(__name__)

# Agent class mapping table
AGENT_REGISTRY = {
    "BaseAgent": {
        "module": "agent.base_agent.base_agent",
        "class": "BaseAgent"
    },
}

def get_agent_class(agent_type: str) -> Type[Any]:
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
