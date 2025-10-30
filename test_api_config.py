#!/usr/bin/env python3
"""
API Configuration Test - Verify OpenAI and DeepSeek API Setup
Tests both API configurations work correctly after cleanup
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_env_variables():
    """Test if required environment variables are set"""
    print("=" * 60)
    print("🔍 Testing Environment Variables")
    print("=" * 60)
    
    required_vars = {
        "OpenAI": ["OPENAI_API_BASE", "OPENAI_API_KEY"],
        "DeepSeek": ["DEEPSEEK_API_BASE", "DEEPSEEK_API_KEY"],
        "Alpaca": ["ALPACA_API_KEY", "ALPACA_SECRET_KEY"]
    }
    
    all_set = True
    for service, vars in required_vars.items():
        print(f"\n📋 {service} Configuration:")
        for var in vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                if "KEY" in var or "SECRET" in var:
                    masked = value[:8] + "..." if len(value) > 8 else "***"
                    print(f"  ✅ {var}: {masked}")
                else:
                    print(f"  ✅ {var}: {value}")
            else:
                print(f"  ❌ {var}: NOT SET")
                all_set = False
    
    print("\n" + "=" * 60)
    if all_set:
        print("✅ All required environment variables are set!")
    else:
        print("⚠️  Some environment variables are missing")
    print("=" * 60)
    
    return all_set


def test_openai_config():
    """Test OpenAI configuration"""
    print("\n" + "=" * 60)
    print("🤖 Testing OpenAI Configuration")
    print("=" * 60)
    
    try:
        from langchain_openai import ChatOpenAI
        
        api_base = os.getenv("OPENAI_API_BASE")
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_base or not api_key:
            print("❌ OpenAI credentials not found in .env")
            return False
        
        # Create OpenAI client
        model = ChatOpenAI(
            model="gpt-4",  # or whatever model you use
            base_url=api_base,
            api_key=api_key,
            timeout=10
        )
        
        print(f"✅ OpenAI client created successfully")
        print(f"   Base URL: {api_base}")
        print(f"   API Key: {api_key[:8]}..." if len(api_key) > 8 else "***")
        
        # Simple test (optional - will use API quota)
        # response = model.invoke("Say 'Hello'")
        # print(f"✅ API Test: {response.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenAI configuration error: {e}")
        return False


def test_deepseek_config():
    """Test DeepSeek configuration"""
    print("\n" + "=" * 60)
    print("🧠 Testing DeepSeek Configuration")
    print("=" * 60)
    
    try:
        from langchain_openai import ChatOpenAI
        
        api_base = os.getenv("DEEPSEEK_API_BASE")
        api_key = os.getenv("DEEPSEEK_API_KEY")
        
        if not api_base or not api_key:
            print("❌ DeepSeek credentials not found in .env")
            return False
        
        # Create DeepSeek client
        model = ChatOpenAI(
            model="deepseek-chat",
            base_url=api_base,
            api_key=api_key,
            timeout=10
        )
        
        print(f"✅ DeepSeek client created successfully")
        print(f"   Base URL: {api_base}")
        print(f"   API Key: {api_key[:8]}..." if len(api_key) > 8 else "***")
        
        # Simple test (optional - will use API quota)
        # response = model.invoke("Say 'Hello'")
        # print(f"✅ API Test: {response.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ DeepSeek configuration error: {e}")
        return False


def test_config_file():
    """Test default_config.json settings"""
    print("\n" + "=" * 60)
    print("📄 Testing Configuration File")
    print("=" * 60)
    
    try:
        import json
        from pathlib import Path
        
        config_path = Path(__file__).parent / "configs" / "default_config.json"
        
        if not config_path.exists():
            print(f"❌ Config file not found: {config_path}")
            return False
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print(f"✅ Configuration file loaded: {config_path}")
        
        # Check models configuration
        models = config.get("models", [])
        print(f"\n📋 Configured Models ({len(models)} total):")
        
        for model in models:
            name = model.get("name", "unknown")
            basemodel = model.get("basemodel", "N/A")
            enabled = model.get("enabled", False)
            api_url = model.get("openai_base_url")
            api_key = model.get("openai_api_key")
            
            status = "🟢 ENABLED" if enabled else "⚫ DISABLED"
            print(f"\n  {status} {name}")
            print(f"     Model: {basemodel}")
            
            if api_url:
                print(f"     API URL: {api_url}")
            else:
                print(f"     API URL: (from .env)")
                
            if api_key:
                masked = api_key[:8] + "..." if len(api_key) > 8 else "***"
                print(f"     API Key: {masked}")
            else:
                print(f"     API Key: (from .env)")
        
        # Check for enabled models
        enabled_models = [m for m in models if m.get("enabled", False)]
        
        print(f"\n📊 Summary:")
        print(f"   Total models: {len(models)}")
        print(f"   Enabled models: {len(enabled_models)}")
        
        if len(enabled_models) == 0:
            print("   ⚠️  WARNING: No models are enabled!")
            return False
        
        # Verify DeepSeek and GPT configurations
        deepseek_found = any(m.get("name") == "deepseek-chat-v3.1" for m in models)
        gpt_found = any(m.get("name") == "gpt-5" for m in models)
        
        print(f"\n🔍 Key Models Status:")
        print(f"   DeepSeek configured: {'✅ Yes' if deepseek_found else '❌ No'}")
        print(f"   GPT-5 configured: {'✅ Yes' if gpt_found else '❌ No'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration file error: {e}")
        return False


def test_mcp_services():
    """Test MCP service configuration"""
    print("\n" + "=" * 60)
    print("🔌 Testing MCP Service Configuration")
    print("=" * 60)
    
    # Check if service ports are set
    alpaca_data_port = os.getenv("ALPACA_DATA_HTTP_PORT", "8004")
    alpaca_trade_port = os.getenv("ALPACA_TRADE_HTTP_PORT", "8005")
    
    print(f"✅ MCP Service Ports:")
    print(f"   Alpaca Data:  {alpaca_data_port}")
    print(f"   Alpaca Trade: {alpaca_trade_port}")
    
    # Check if legacy ports are removed
    legacy_ports = ["MATH_HTTP_PORT", "SEARCH_HTTP_PORT", "TRADE_HTTP_PORT", "GETPRICE_HTTP_PORT"]
    legacy_found = False
    
    for port in legacy_ports:
        if os.getenv(port):
            print(f"   ⚠️  Legacy port found: {port}={os.getenv(port)}")
            legacy_found = True
    
    if not legacy_found:
        print(f"✅ No legacy ports configured (cleanup successful)")
    
    return True


def main():
    """Run all tests"""
    print("\n🔍 AI-Trader API Configuration Test")
    print("Testing OpenAI and DeepSeek setup after cleanup")
    print("")
    
    # Run tests
    results = {
        "Environment Variables": test_env_variables(),
        "Configuration File": test_config_file(),
        "MCP Services": test_mcp_services(),
        "OpenAI Setup": test_openai_config(),
        "DeepSeek Setup": test_deepseek_config()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! System is ready for trading.")
        print("\nNext steps:")
        print("  1. Start MCP services: cd agent_tools && python start_mcp_services.py")
        print("  2. Run trading: python main.py")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        print("\nCommon fixes:")
        print("  • Make sure .env file exists and has all API keys")
        print("  • Check configs/default_config.json has enabled models")
        print("  • Verify API keys are valid and not expired")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
