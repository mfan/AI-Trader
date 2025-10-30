#!/usr/bin/env python3
"""
Test MCP Service Connection
Quick test to verify MCP services are accessible
"""

import os
import asyncio
import traceback
from dotenv import load_dotenv
load_dotenv()

async def test_mcp_connection():
    """Test connection to MCP services"""
    print("🔍 Testing MCP Service Connection")
    print("=" * 60)
    
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        
        # MCP configuration
        mcp_config = {
            "alpaca_data": {
                "transport": "sse",
                "url": f"http://localhost:{os.getenv('ALPACA_DATA_HTTP_PORT', '8004')}/sse",
            },
            "alpaca_trade": {
                "transport": "sse",
                "url": f"http://localhost:{os.getenv('ALPACA_TRADE_HTTP_PORT', '8005')}/sse",
            },
        }
        
        print("📋 MCP Configuration:")
        for name, config in mcp_config.items():
            print(f"   {name}: {config['url']} ({config['transport']})")
        
        print("\n🔄 Creating MCP client...")
        client = MultiServerMCPClient(mcp_config)
        
        print("✅ MCP client created")
        
        print("\n🔄 Getting tools from MCP servers...")
        tools = await client.get_tools()
        
        print(f"✅ Successfully loaded {len(tools)} tools")
        
        print("\n📋 Available tools:")
        for i, tool in enumerate(tools[:10], 1):  # Show first 10 tools
            print(f"   {i}. {tool.name}")
        
        if len(tools) > 10:
            print(f"   ... and {len(tools) - 10} more tools")
        
        print("\n✅ MCP connection test successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ MCP connection test failed!")
        print(f"Error: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_mcp_connection())
    exit(0 if result else 1)
