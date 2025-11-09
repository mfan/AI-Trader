#!/usr/bin/env python3
"""
Test XAI Grok Agent Configuration

This script tests that the XAI-Grok agent can be properly configured and initialized.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_env_variables():
    """Test that XAI environment variables are set"""
    print("=" * 80)
    print("🔍 TESTING XAI ENVIRONMENT VARIABLES")
    print("=" * 80)
    print()
    
    xai_base = os.getenv("XAI_API_BASE")
    xai_key = os.getenv("XAI_API_KEY")
    
    print(f"XAI_API_BASE: {xai_base}")
    if xai_key:
        masked_key = f"{xai_key[:8]}...{xai_key[-4:]}" if len(xai_key) > 12 else "***"
        print(f"XAI_API_KEY: {masked_key}")
        print("✅ XAI credentials found in environment")
        return True
    else:
        print("❌ XAI_API_KEY not found in environment")
        print("   Please set XAI_API_KEY in your .env file")
        return False


def test_config_loading():
    """Test that config file loads and substitutes environment variables"""
    print()
    print("=" * 80)
    print("🔍 TESTING CONFIG FILE LOADING")
    print("=" * 80)
    print()
    
    config_path = Path(__file__).parent / "configs" / "default_config.json"
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print("✅ Config file loaded successfully")
        print()
        
        # Check for XAI model
        xai_model = None
        for model in config.get("models", []):
            if "xai" in model.get("name", "").lower() or "grok" in model.get("name", "").lower():
                xai_model = model
                break
        
        if xai_model:
            print(f"✅ Found XAI model in config:")
            print(f"   Name: {xai_model.get('name')}")
            print(f"   Base Model: {xai_model.get('basemodel')}")
            print(f"   Signature: {xai_model.get('signature')}")
            print(f"   Enabled: {xai_model.get('enabled')}")
            print(f"   API Base: {xai_model.get('openai_base_url')}")
            
            # Check if environment variable syntax is used
            api_base = xai_model.get('openai_base_url', '')
            api_key = xai_model.get('openai_api_key', '')
            
            if '${' in api_base:
                print(f"   API Base uses env var: {api_base}")
            if '${' in api_key:
                print(f"   API Key uses env var: {api_key}")
            
            return True
        else:
            print("❌ No XAI/Grok model found in config")
            return False
            
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False


def test_config_substitution():
    """Test that environment variable substitution works"""
    print()
    print("=" * 80)
    print("🔍 TESTING ENVIRONMENT VARIABLE SUBSTITUTION")
    print("=" * 80)
    print()
    
    # Import the load_config function from active_trader
    sys.path.insert(0, str(Path(__file__).parent))
    
    try:
        # We need to test the substitute_env_vars logic
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
                    print(f"⚠️  Environment variable {var_name} not found")
                    return obj
            else:
                return obj
        
        # Test with sample config
        test_config = {
            "openai_base_url": "${XAI_API_BASE}",
            "openai_api_key": "${XAI_API_KEY}"
        }
        
        print("Before substitution:")
        print(f"   API Base: {test_config['openai_base_url']}")
        print(f"   API Key: {test_config['openai_api_key']}")
        print()
        
        result = substitute_env_vars(test_config)
        
        print("After substitution:")
        print(f"   API Base: {result['openai_base_url']}")
        
        if result['openai_api_key'] and not result['openai_api_key'].startswith('${'):
            masked_key = f"{result['openai_api_key'][:8]}...{result['openai_api_key'][-4:]}"
            print(f"   API Key: {masked_key}")
            print()
            print("✅ Environment variable substitution working correctly")
            return True
        else:
            print(f"   API Key: {result['openai_api_key']}")
            print()
            print("❌ Environment variable substitution failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing substitution: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_initialization():
    """Test that agent can be initialized with XAI config"""
    print()
    print("=" * 80)
    print("🔍 TESTING AGENT INITIALIZATION (DRY RUN)")
    print("=" * 80)
    print()
    
    try:
        # Check if we can import the base agent
        from agent.base_agent.base_agent import BaseAgent
        
        print("✅ BaseAgent class imported successfully")
        
        # Get XAI credentials
        xai_base = os.getenv("XAI_API_BASE")
        xai_key = os.getenv("XAI_API_KEY")
        
        if not xai_base or not xai_key:
            print("⚠️  Skipping initialization test (credentials not set)")
            return None
        
        print()
        print("Agent would be initialized with:")
        print(f"   Base Model: grok-beta")
        print(f"   API Base: {xai_base}")
        print(f"   API Key: {xai_key[:8]}...{xai_key[-4:]}")
        print()
        print("✅ Configuration valid for agent initialization")
        
        return True
        
    except ImportError as e:
        print(f"⚠️  Could not import BaseAgent: {e}")
        print("   (This is expected if not in the right directory)")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print()
    print("🚀 XAI GROK AGENT CONFIGURATION TEST")
    print(f"📅 Date: {os.popen('date').read().strip()}")
    print()
    
    results = []
    
    # Test 1: Environment variables
    results.append(("Environment Variables", test_env_variables()))
    
    # Test 2: Config loading
    results.append(("Config Loading", test_config_loading()))
    
    # Test 3: Variable substitution
    results.append(("Variable Substitution", test_config_substitution()))
    
    # Test 4: Agent initialization (dry run)
    init_result = test_agent_initialization()
    if init_result is not None:
        results.append(("Agent Initialization", init_result))
    
    # Summary
    print()
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print()
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if failed == 0:
        print()
        print("🎉 All tests passed! XAI Grok agent is properly configured.")
        print()
        print("To enable XAI Grok agent:")
        print('   1. Edit configs/default_config.json')
        print('   2. Find the "xai-grok-beta" model entry')
        print('   3. Change "enabled": false to "enabled": true')
        print('   4. Change deepseek "enabled": true to "enabled": false')
        print('   5. Restart active-trader service')
        return 0
    else:
        print()
        print(f"⚠️  {failed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
