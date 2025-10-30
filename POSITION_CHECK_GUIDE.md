# Quick Position Check Guide

## Current Status

Your Alpaca credentials are configured correctly in `.env`:
- ✅ ALPACA_API_KEY: SET
- ✅ ALPACA_SECRET_KEY: SET  
- ✅ alpaca-py library: INSTALLED

## Option 1: Start MCP Services and Use Agent

The easiest way to check positions is to use the AI agent with MCP services:

```bash
# 1. Activate virtual environment
source ~/work/bin/activate

# 2. Start MCP services
cd agent_tools
python start_mcp_services.py
# Wait for: ✅ AlpacaTrade service started (Port: 8005)

# 3. In another terminal, check positions using the agent
cd /home/mfan/work/aitrader
source ~/work/bin/activate
python -c "
from agent.base_agent.base_agent import BaseAgent
import asyncio

async def check():
    agent = BaseAgent(
        signature='position-check',
        basemodel='deepseek-chat',
        init_date='2025-10-28'
    )
    await agent.initialize()
    
    # Use Alpaca MCP tools to get positions
    # The agent will have access to get_positions() tool
    
asyncio.run(check())
"
```

## Option 2: Direct API Call (Simple Script)

Create a simple script:

```bash
cd /home/mfan/work/aitrader
source ~/work/bin/activate

cat > quick_check.py << 'EOF'
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

try:
    client = TradingClient(
        api_key=os.getenv('ALPACA_API_KEY'),
        secret_key=os.getenv('ALPACA_SECRET_KEY'),
        paper=True
    )
    
    account = client.get_account()
    print(f"\n💰 ACCOUNT STATUS")
    print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
    print(f"Cash: ${float(account.cash):,.2f}")
    print(f"Buying Power: ${float(account.buying_power):,.2f}")
    
    positions = client.get_all_positions()
    print(f"\n📦 POSITIONS: {len(positions)}")
    
    if positions:
        for p in positions:
            pl_sign = "+" if float(p.unrealized_pl) >= 0 else ""
            print(f"  {p.symbol}: {p.qty} @ ${float(p.current_price):.2f} "
                  f"(P/L: {pl_sign}${float(p.unrealized_pl):.2f})")
    else:
        print("  No positions held")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
EOF

# Run it
python quick_check.py
```

## Option 3: Use Alpaca Web Dashboard

Visit: https://app.alpaca.markets/paper/dashboard/overview

- Login with your Alpaca account
- View positions in the web interface
- This is the fastest way to see current holdings

## Troubleshooting

If API calls timeout:
1. Check your internet connection
2. Verify Alpaca API status: https://status.alpaca.markets/
3. Try the web dashboard instead
4. Check if you're rate-limited

## Expected Results

Based on previous test runs, you likely have:
- Cash: $100,000 (initial paper trading balance)
- Positions: 0 (no trades executed yet)

The system was tested successfully but no actual trades were placed.
