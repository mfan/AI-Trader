#!/usr/bin/env python3
"""
Test script for short selling functionality
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

from tools.alpaca_trading import AlpacaTradingClient

def test_short_selling():
    """Test short selling with a small SPY position"""
    print("=" * 60)
    print("SHORT SELLING TEST")
    print("=" * 60)
    
    # Initialize client
    client = AlpacaTradingClient()
    
    # Check account status
    print("\n1. Checking account configuration...")
    account = client.get_account()
    print(f"   Account: {account.get('account_number', account.get('id', 'N/A'))}")
    print(f"   Shorting Enabled: {account.get('shorting_enabled', 'N/A')}")
    print(f"   Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
    print(f"   Multiplier: {account.get('multiplier', 'N/A')}")
    
    # Get SPY price
    print("\n2. Getting SPY price...")
    try:
        spy_price = client.get_latest_price("SPY")
        if spy_price:
            print(f"   SPY Current Price: ${spy_price:.2f}")
        else:
            print("   ⚠️ Could not get SPY price from quote, trying alternative...")
            # Try getting from position or use a default for testing
            spy_price = 595.0  # Approximate SPY price for testing
            print(f"   Using test price: ${spy_price:.2f}")
    except Exception as e:
        print(f"   ⚠️ Price fetch error: {e}")
        spy_price = 595.0  # Approximate SPY price for testing
        print(f"   Using test price: ${spy_price:.2f}")
    
    # Calculate small test size
    test_qty = 10
    estimated_value = spy_price * test_qty
    print(f"\n3. Test short position:")
    print(f"   Symbol: SPY")
    print(f"   Quantity: {test_qty} shares")
    print(f"   Estimated Value: ${estimated_value:,.2f}")
    
    # Check if we have existing SPY position
    print("\n4. Checking existing positions...")
    position = client.get_position("SPY")
    if position:
        print(f"   ⚠️  Existing SPY position: {position['qty']} shares @ ${position['avg_entry_price']:.2f}")
        print(f"   Side: {position['side']}")
        print(f"   Market Value: ${position['market_value']:.2f}")
        print(f"   P&L: ${position['unrealized_pl']:.2f}")
    else:
        print("   ✅ No existing SPY position")
    
    # Ask for confirmation
    print("\n" + "=" * 60)
    response = input(f"Place SHORT order for {test_qty} shares of SPY @ ~${spy_price:.2f}? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Test cancelled.")
        return
    
    # Place short order
    print("\n5. Placing SHORT order...")
    try:
        result = client.sell_market("SPY", test_qty, extended_hours=False)
        
        if result.get('success'):
            print(f"   ✅ Short order placed successfully!")
            print(f"   Order ID: {result['order_id']}")
            print(f"   Status: {result['status']}")
            print(f"   Symbol: {result['symbol']}")
            print(f"   Side: {result['side']}")
            print(f"   Quantity: {result['qty']}")
            
            # Wait a moment and check order status
            import time
            print("\n6. Waiting 3 seconds for order to fill...")
            time.sleep(3)
            
            filled_order = client.get_order(result['order_id'])
            print(f"\n   Order Status: {filled_order['status']}")
            print(f"   Filled Qty: {filled_order['filled_qty']}")
            print(f"   Filled Avg Price: ${filled_order['filled_avg_price']}")
            print(f"   Filled At: {filled_order.get('filled_at', 'N/A')}")
            
            # Check position
            print("\n7. Checking position after short...")
            position = client.get_position("SPY")
            if position:
                print(f"   Position Qty: {position['qty']} (negative = short)")
                print(f"   Side: {position['side']}")
                print(f"   Avg Entry Price: ${position['avg_entry_price']:.2f}")
                print(f"   Market Value: ${position['market_value']:.2f}")
                print(f"   Unrealized P&L: ${position['unrealized_pl']:.2f}")
            
        else:
            print(f"   ❌ Short order failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"   ❌ Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_short_selling()
