#!/usr/bin/env python3
"""
Check Current Alpaca Positions
Displays current portfolio holdings and account information
"""

import os
import sys
import signal
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass

# Load environment variables
load_dotenv()

# Timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError("API call timed out after 10 seconds")

# Set timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)  # 10 second timeout

def check_positions():
    """Check current positions in Alpaca account"""
    
    # Get API credentials
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    paper_trading = os.getenv("ALPACA_PAPER_TRADING", "true").lower() == "true"
    
    if not api_key or not secret_key:
        print("❌ Error: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env")
        return
    
    # Create trading client
    client = TradingClient(
        api_key=api_key,
        secret_key=secret_key,
        paper=paper_trading
    )
    
    print("=" * 80)
    print(f"📊 ALPACA {'PAPER' if paper_trading else 'LIVE'} TRADING ACCOUNT STATUS")
    print("=" * 80)
    
    # Get account information
    try:
        account = client.get_account()
        
        print(f"\n💰 Account Information:")
        print(f"   Portfolio Value:  ${float(account.portfolio_value):,.2f}")
        print(f"   Cash Available:   ${float(account.cash):,.2f}")
        print(f"   Buying Power:     ${float(account.buying_power):,.2f}")
        print(f"   Equity:           ${float(account.equity):,.2f}")
        
        # Calculate P&L
        total_pl = float(account.equity) - float(account.last_equity)
        pl_percent = (total_pl / float(account.last_equity) * 100) if float(account.last_equity) > 0 else 0
        
        pl_symbol = "📈" if total_pl >= 0 else "📉"
        print(f"   Today's P&L:      {pl_symbol} ${total_pl:,.2f} ({pl_percent:+.2f}%)")
        
    except Exception as e:
        print(f"❌ Error fetching account info: {e}")
        return
    
    # Get current positions
    print(f"\n📦 Current Positions:")
    print("=" * 80)
    
    try:
        positions = client.get_all_positions()
        
        if not positions:
            print("   ℹ️  No positions currently held")
        else:
            # Print header
            print(f"{'Symbol':<8} {'Qty':<8} {'Entry':<12} {'Current':<12} {'P&L':<12} {'P&L %':<10} {'Value':<12}")
            print("-" * 80)
            
            total_position_value = 0
            total_pl = 0
            
            for position in positions:
                symbol = position.symbol
                qty = float(position.qty)
                entry_price = float(position.avg_entry_price)
                current_price = float(position.current_price)
                unrealized_pl = float(position.unrealized_pl)
                unrealized_plpc = float(position.unrealized_plpc) * 100
                market_value = float(position.market_value)
                
                total_position_value += market_value
                total_pl += unrealized_pl
                
                # Format P&L with color indicator
                pl_indicator = "🟢" if unrealized_pl >= 0 else "🔴"
                
                print(f"{symbol:<8} {qty:<8.2f} ${entry_price:<11.2f} ${current_price:<11.2f} "
                      f"{pl_indicator}${unrealized_pl:<10.2f} {unrealized_plpc:>+8.2f}% ${market_value:<11.2f}")
            
            print("-" * 80)
            print(f"{'TOTAL':<8} {'':<8} {'':<12} {'':<12} "
                  f"${total_pl:<11.2f} {'':<10} ${total_position_value:<11.2f}")
            
            # Summary
            print(f"\n📊 Portfolio Summary:")
            print(f"   Number of Positions: {len(positions)}")
            print(f"   Total Position Value: ${total_position_value:,.2f}")
            print(f"   Total Unrealized P&L: ${total_pl:,.2f}")
            print(f"   Cash: ${float(account.cash):,.2f}")
            print(f"   Total Portfolio: ${float(account.portfolio_value):,.2f}")
            
    except Exception as e:
        print(f"❌ Error fetching positions: {e}")
        return
    
    # Get recent orders
    print(f"\n📋 Recent Orders (Last 10):")
    print("=" * 80)
    
    try:
        orders = client.get_orders(limit=10)
        
        if not orders:
            print("   ℹ️  No recent orders")
        else:
            print(f"{'Symbol':<8} {'Side':<6} {'Qty':<8} {'Type':<10} {'Status':<12} {'Submitted':<20}")
            print("-" * 80)
            
            for order in orders:
                symbol = order.symbol
                side = order.side.value
                qty = order.qty
                order_type = order.type.value
                status = order.status.value
                submitted = order.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if order.submitted_at else "N/A"
                
                # Status indicator
                status_symbol = {
                    'filled': '✅',
                    'partially_filled': '🟡',
                    'pending_new': '🔵',
                    'accepted': '🔵',
                    'canceled': '❌',
                    'rejected': '❌'
                }.get(status, '⚪')
                
                print(f"{symbol:<8} {side:<6} {qty:<8} {order_type:<10} {status_symbol}{status:<11} {submitted:<20}")
                
    except Exception as e:
        print(f"❌ Error fetching orders: {e}")
    
    print("=" * 80)


if __name__ == "__main__":
    check_positions()
