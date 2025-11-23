#!/usr/bin/env python3
"""
Check current positions in Alpaca account
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from tools.alpaca_trading import AlpacaTradingClient

def check_positions():
    """Check all current positions"""
    print("=" * 70)
    print("ALPACA ACCOUNT POSITIONS")
    print("=" * 70)
    
    client = AlpacaTradingClient()
    
    # Get account info
    print("\n📊 Account Summary:")
    account = client.get_account()
    print(f"   Account ID: {account.get('id', 'N/A')}")
    print(f"   Equity: ${float(account.get('equity', 0)):,.2f}")
    print(f"   Cash: ${float(account.get('cash', 0)):,.2f}")
    print(f"   Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
    print(f"   Portfolio Value: ${float(account.get('portfolio_value', 0)):,.2f}")
    
    # Get all positions
    print("\n📈 Current Positions:")
    print("-" * 70)
    
    try:
        positions = client.get_positions()
        
        if not positions:
            print("   ✅ No open positions")
        else:
            total_value = 0
            total_pl = 0
            
            for symbol, pos in positions.items():
                qty = pos['qty']
                side = pos['side']
                entry_price = pos['avg_entry_price']
                current_price = pos['current_price']
                market_value = pos['market_value']
                unrealized_pl = pos['unrealized_pl']
                pl_percent = pos['unrealized_plpc'] * 100
                
                total_value += market_value
                total_pl += unrealized_pl
                
                # Show position type
                if qty < 0:
                    position_type = "SHORT"
                    qty_display = abs(qty)
                else:
                    position_type = "LONG"
                    qty_display = qty
                
                pl_sign = "+" if unrealized_pl >= 0 else ""
                
                print(f"\n   {symbol} ({position_type})")
                print(f"      Quantity: {qty_display:,.0f} shares")
                print(f"      Entry Price: ${entry_price:,.2f}")
                print(f"      Current Price: ${current_price:,.2f}")
                print(f"      Market Value: ${abs(market_value):,.2f}")
                print(f"      P&L: {pl_sign}${unrealized_pl:,.2f} ({pl_sign}{pl_percent:.2f}%)")
            
            print("\n" + "-" * 70)
            print(f"   Total Position Value: ${abs(total_value):,.2f}")
            print(f"   Total Unrealized P&L: ${total_pl:+,.2f}")
            
    except Exception as e:
        print(f"   ❌ Error getting positions: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    check_positions()
