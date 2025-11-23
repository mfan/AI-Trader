#!/usr/bin/env python3
"""
Analyze trading performance for Nov 18, 2025
"""
import json
import sys
from datetime import datetime
from collections import defaultdict

def analyze_trading_log(date="2025-11-18"):
    """Analyze trading performance"""
    
    log_file = f"/home/mfan/work/aitrader/data/agent_data/xai-grok-4-fast/trades/{date}_trades.jsonl"
    
    print("=" * 80)
    print(f"TRADING ANALYSIS FOR {date}")
    print("=" * 80)
    
    trades = []
    try:
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    trades.append(json.loads(line))
    except FileNotFoundError:
        print(f"❌ No trading log found for {date}")
        return
    
    print(f"\n📊 Total Trade Records: {len(trades)}")
    
    # Analyze by action type
    actions = defaultdict(int)
    symbols = defaultdict(int)
    
    successful_trades = 0
    failed_trades = 0
    
    buy_orders = []
    sell_orders = []
    short_orders = []
    close_orders = []
    
    total_buy_value = 0
    total_sell_value = 0
    
    # Enhanced logging check
    has_filled_details = 0
    missing_filled_details = 0
    
    for trade in trades:
        action = trade.get('action', 'unknown')
        symbol = trade.get('symbol', 'N/A')
        result = trade.get('result', {})
        
        actions[action] += 1
        symbols[symbol] += 1
        
        if result.get('success'):
            successful_trades += 1
        else:
            failed_trades += 1
        
        # Check for filled details (our fix)
        filled_details = trade.get('filled_details')
        if filled_details:
            has_filled_details += 1
        else:
            missing_filled_details += 1
        
        # Extract execution details
        qty = trade.get('qty') or result.get('filled_qty', 0)
        price = trade.get('price') or result.get('filled_avg_price')
        
        if action == 'buy':
            buy_orders.append({
                'symbol': symbol,
                'qty': qty,
                'price': price,
                'status': result.get('status'),
                'filled_details': filled_details
            })
            if price:
                total_buy_value += qty * price
                
        elif action == 'sell':
            sell_orders.append({
                'symbol': symbol,
                'qty': qty,
                'price': price,
                'status': result.get('status'),
                'filled_details': filled_details
            })
            if price:
                total_sell_value += qty * price
                
        elif action == 'short':
            short_orders.append({
                'symbol': symbol,
                'qty': qty,
                'price': price,
                'status': result.get('status'),
                'filled_details': filled_details
            })
            if price:
                total_sell_value += qty * price
                
        elif action == 'close':
            close_orders.append({
                'symbol': symbol,
                'qty': qty,
                'price': price,
                'status': result.get('status'),
                'filled_details': filled_details
            })
    
    print(f"\n✅ Successful Orders: {successful_trades}")
    print(f"❌ Failed Orders: {failed_trades}")
    
    print(f"\n📈 Trade Actions Breakdown:")
    for action, count in sorted(actions.items()):
        print(f"   {action.upper()}: {count}")
    
    print(f"\n🎯 Most Active Symbols:")
    top_symbols = sorted(symbols.items(), key=lambda x: x[1], reverse=True)[:10]
    for symbol, count in top_symbols:
        print(f"   {symbol}: {count} trades")
    
    # Check enhanced logging
    print(f"\n🔍 Enhanced Logging Status (Post-Fix):")
    print(f"   ✅ Trades with filled details: {has_filled_details}")
    print(f"   ⚠️  Trades missing filled details: {missing_filled_details}")
    if has_filled_details > 0:
        print(f"   🎉 ENHANCED LOGGING IS WORKING! ({has_filled_details}/{len(trades)} trades)")
    else:
        print(f"   ⚠️  No filled details captured yet")
    
    # Show sample trades with filled details
    if has_filled_details > 0:
        print(f"\n📝 Sample Trades with Filled Details:")
        samples = [t for t in trades if t.get('filled_details')][:3]
        for i, trade in enumerate(samples, 1):
            print(f"\n   Sample {i}:")
            print(f"      Action: {trade['action']}")
            print(f"      Symbol: {trade['symbol']}")
            print(f"      Quantity: {trade.get('qty', 'N/A')}")
            print(f"      Price: ${trade.get('price', 0):.2f}" if trade.get('price') else "      Price: N/A")
            print(f"      Status: {trade.get('status', 'N/A')}")
            filled = trade.get('filled_details', {})
            if filled:
                print(f"      Filled Qty: {filled.get('filled_qty', 'N/A')}")
                print(f"      Filled Price: ${filled.get('filled_avg_price', 0):.2f}" if filled.get('filled_avg_price') else "      Filled Price: N/A")
    
    # Short selling check
    print(f"\n🔻 Short Selling Status:")
    if short_orders:
        print(f"   ✅ SHORT POSITIONS EXECUTED: {len(short_orders)}")
        print(f"   🎉 SHORT SELLING FIX IS WORKING!")
        for order in short_orders[:5]:
            print(f"\n      Symbol: {order['symbol']}")
            print(f"      Quantity: {order['qty']}")
            if order['price']:
                print(f"      Price: ${order['price']:.2f}")
            print(f"      Status: {order['status']}")
    else:
        print(f"   ℹ️  No short positions attempted on {date}")
        print(f"   (Agent may not have identified overbought opportunities)")
    
    print(f"\n💰 Trading Volume:")
    print(f"   Total Buy Value: ${total_buy_value:,.2f}")
    print(f"   Total Sell Value: ${total_sell_value:,.2f}")
    
    # Get current P&L from position file
    try:
        position_file = "/home/mfan/work/aitrader/data/agent_data/xai-grok-4-fast/position/position.jsonl"
        with open(position_file, 'r') as f:
            lines = f.readlines()
            if lines:
                latest = json.loads(lines[-1])
                print(f"\n📊 End of Day Status ({latest.get('date', 'N/A')}):")
                print(f"   Portfolio Value: ${latest.get('total_assets', 0):,.2f}")
                print(f"   Total P&L: ${latest.get('total_profit', 0):,.2f}")
                print(f"   Day P&L: ${latest.get('day_profit', 0):,.2f}")
    except Exception as e:
        print(f"\n⚠️ Could not read position data: {e}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    analyze_trading_log()
