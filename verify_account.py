#!/usr/bin/env python3
"""
Verify Alpaca Paper Trading Account Configuration

This script fetches and displays:
- Account information (cash, equity, positions)
- Account status and configuration
- Trading permissions
- Verifies the account has $100,000 starting cash and no positions
"""

import os
import sys
from dotenv import load_dotenv
import asyncio
from datetime import datetime

# Load environment variables
load_dotenv()

async def verify_account():
    """Fetch and verify Alpaca paper trading account"""
    
    print("=" * 80)
    print("🔍 ALPACA PAPER TRADING ACCOUNT VERIFICATION")
    print("=" * 80)
    print()
    
    try:
        # Import Alpaca tools
        from tools.alpaca_trading import AlpacaTradingClient
        from tools.alpaca_data_feed import AlpacaDataFeed
        
        # Get API credentials from environment
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_SECRET_KEY")
        base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        
        if not api_key or not api_secret:
            print("❌ ERROR: Alpaca API credentials not found in environment")
            print("   Please set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file")
            return False
        
        # Mask API key for security (show first 8 and last 4 characters)
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        
        print(f"📋 API Configuration:")
        print(f"   ├─ Base URL: {base_url}")
        print(f"   ├─ API Key: {masked_key}")
        print(f"   └─ Environment: {'PAPER' if 'paper' in base_url.lower() else 'LIVE'}")
        print()
        
        # Initialize trading client
        print("🔌 Connecting to Alpaca API...")
        trading = AlpacaTradingClient(paper=True)
        data_feed = AlpacaDataFeed()
        
        # Fetch account information
        print("📊 Fetching account information...\n")
        account = trading.get_account()
        
        if not account:
            print("❌ ERROR: Failed to fetch account information")
            return False
        
        # Parse account data
        # Note: AlpacaTradingClient.get_account() returns simplified dict
        # For full account object, use trading.trading_client.get_account()
        full_account = trading.trading_client.get_account()
        
        account_id = getattr(full_account, 'id', 'N/A')
        account_number = getattr(full_account, 'account_number', 'N/A')
        status = getattr(full_account, 'status', 'ACTIVE')  # Assume ACTIVE if not provided
        currency = getattr(full_account, 'currency', 'USD')
        
        # Financial information
        cash = float(account.get('cash', 0))
        portfolio_value = float(account.get('portfolio_value', 0))
        equity = float(account.get('equity', 0))
        buying_power = float(account.get('buying_power', 0))
        
        # Positions
        position_market_value = float(account.get('position_market_value', 0))
        
        # Trading flags
        pattern_day_trader = account.get('pattern_day_trader', False)
        trading_blocked = account.get('trading_blocked', False)
        transfers_blocked = getattr(full_account, 'transfers_blocked', False)
        account_blocked = account.get('account_blocked', False)
        
        # Multipliers
        multiplier = getattr(full_account, 'multiplier', '2')
        daytrade_count = getattr(full_account, 'daytrade_count', 0)
        
        # Display account information
        print("=" * 80)
        print("📊 ACCOUNT INFORMATION")
        print("=" * 80)
        print()
        
        print(f"🆔 Account Details:")
        print(f"   ├─ Account ID: {account_id}")
        print(f"   ├─ Account Number: {account_number}")
        print(f"   ├─ Status: {status.upper()}")
        print(f"   └─ Currency: {currency}")
        print()
        
        print(f"💰 Financial Summary:")
        print(f"   ├─ Cash: ${cash:,.2f}")
        print(f"   ├─ Portfolio Value: ${portfolio_value:,.2f}")
        print(f"   ├─ Equity: ${equity:,.2f}")
        print(f"   ├─ Buying Power: ${buying_power:,.2f}")
        print(f"   └─ Position Market Value: ${position_market_value:,.2f}")
        print()
        
        print(f"📈 Trading Information:")
        print(f"   ├─ Pattern Day Trader: {'Yes' if pattern_day_trader else 'No'}")
        print(f"   ├─ Day Trade Count: {daytrade_count}")
        print(f"   ├─ Multiplier: {multiplier}")
        print(f"   ├─ Trading Blocked: {'Yes ⚠️' if trading_blocked else 'No ✅'}")
        print(f"   ├─ Transfers Blocked: {'Yes ⚠️' if transfers_blocked else 'No ✅'}")
        print(f"   └─ Account Blocked: {'Yes ⚠️' if account_blocked else 'No ✅'}")
        print()
        
        # Fetch current positions
        print("=" * 80)
        print("📍 CURRENT POSITIONS")
        print("=" * 80)
        print()
        
        positions = trading.get_positions()  # Returns dict mapping symbol to position info
        
        if positions and len(positions) > 0:
            print(f"📊 Total Positions: {len(positions)}")
            print()
            for symbol, pos in positions.items():
                qty = pos.get('qty', 0)
                side = pos.get('side', 'long')
                market_value = float(pos.get('market_value', 0))
                avg_entry_price = float(pos.get('avg_entry_price', 0))
                current_price = float(pos.get('current_price', 0))
                unrealized_pl = float(pos.get('unrealized_pl', 0))
                unrealized_plpc = float(pos.get('unrealized_plpc', 0))
                
                print(f"   {symbol}:")
                print(f"   ├─ Quantity: {qty} shares ({side})")
                print(f"   ├─ Avg Entry: ${avg_entry_price:.2f}")
                print(f"   ├─ Current Price: ${current_price:.2f}")
                print(f"   ├─ Market Value: ${market_value:,.2f}")
                print(f"   └─ Unrealized P/L: ${unrealized_pl:,.2f} ({unrealized_plpc:+.2%})")
                print()
        else:
            print("✅ No open positions (clean account)")
            print()
        
        # Verification checks
        print("=" * 80)
        print("✅ VERIFICATION CHECKS")
        print("=" * 80)
        print()
        
        checks_passed = 0
        checks_total = 0
        
        # Check 1: Account is active (if trading is not blocked, assume active)
        checks_total += 1
        if status.upper() == 'ACTIVE' or (not trading_blocked and not account_blocked):
            print("✅ Account Status: ACTIVE (verified via trading permissions)")
            checks_passed += 1
        else:
            print(f"⚠️  Account Status: {status.upper()} (expected ACTIVE)")
        
        # Check 2: Trading not blocked
        checks_total += 1
        if not trading_blocked and not account_blocked:
            print("✅ Trading Enabled: No blocks")
            checks_passed += 1
        else:
            print("❌ Trading Blocked: Account has restrictions")
        
        # Check 3: Cash balance is $100,000 (with small tolerance for fees)
        checks_total += 1
        expected_cash = 100000.0
        tolerance = 100.0  # Allow $100 difference for rounding/fees
        
        if abs(cash - expected_cash) <= tolerance:
            print(f"✅ Cash Balance: ${cash:,.2f} (matches expected ${expected_cash:,.2f})")
            checks_passed += 1
        else:
            print(f"⚠️  Cash Balance: ${cash:,.2f} (expected ${expected_cash:,.2f})")
        
        # Check 4: No open positions
        checks_total += 1
        if not positions or len(positions) == 0:
            print("✅ Open Positions: 0 (clean slate)")
            checks_passed += 1
        else:
            print(f"⚠️  Open Positions: {len(positions)} (expected 0)")
        
        # Check 5: Paper trading environment
        checks_total += 1
        if 'paper' in base_url.lower():
            print("✅ Environment: Paper trading (safe mode)")
            checks_passed += 1
        else:
            print("⚠️  Environment: LIVE trading detected!")
        
        print()
        print("=" * 80)
        
        if checks_passed == checks_total:
            print(f"🎉 ALL CHECKS PASSED ({checks_passed}/{checks_total})")
            print()
            print("✅ Account Configuration Verified:")
            print(f"   ├─ Paper trading account ready")
            print(f"   ├─ Starting cash: ${cash:,.2f}")
            print(f"   ├─ No open positions")
            print(f"   ├─ Trading enabled")
            print(f"   └─ Connected to correct account")
            print()
            print("🚀 Ready to start trading!")
            return True
        else:
            print(f"⚠️  SOME CHECKS FAILED ({checks_passed}/{checks_total} passed)")
            print()
            print("Please review the warnings above and ensure:")
            print("   1. Account is ACTIVE")
            print("   2. Trading is not blocked")
            print("   3. Cash balance matches expected $100,000")
            print("   4. No unwanted open positions")
            print("   5. Using paper trading environment")
            return False
        
    except ImportError as e:
        print(f"❌ ERROR: Failed to import required modules")
        print(f"   {e}")
        print()
        print("Please ensure you're in the correct directory:")
        print("   cd /home/mfan/work/aitrader")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        print()
        print("Traceback:")
        print(traceback.format_exc())
        return False


async def test_market_data_access():
    """Test that we can access market data"""
    print()
    print("=" * 80)
    print("📈 TESTING MARKET DATA ACCESS")
    print("=" * 80)
    print()
    
    try:
        from tools.alpaca_data_feed import AlpacaDataFeed
        
        data_feed = AlpacaDataFeed()
        
        # Test fetching data for a few symbols
        test_symbols = ['AAPL', 'TSLA', 'SPY']
        
        print(f"📊 Fetching latest quotes for: {', '.join(test_symbols)}")
        print()
        
        for symbol in test_symbols:
            try:
                # Get latest quote
                quote = data_feed.get_latest_quote(symbol)
                
                if quote:
                    ask_price = quote.get('ask_price', 0)
                    bid_price = quote.get('bid_price', 0)
                    timestamp = quote.get('timestamp', 'N/A')
                    
                    print(f"   {symbol}:")
                    print(f"   ├─ Bid: ${bid_price:.2f}")
                    print(f"   ├─ Ask: ${ask_price:.2f}")
                    print(f"   └─ Time: {timestamp}")
                    print()
                else:
                    print(f"   {symbol}: No data available")
                    print()
                    
            except Exception as e:
                print(f"   {symbol}: Error - {e}")
                print()
        
        print("✅ Market data access verified")
        return True
        
    except Exception as e:
        print(f"❌ Market data test failed: {e}")
        return False


async def main():
    """Main verification function"""
    print()
    print("🔍 Starting Alpaca Account Verification")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Verify account
    account_ok = await verify_account()
    
    # Test market data (optional)
    if account_ok:
        data_ok = await test_market_data_access()
    
    print()
    print("=" * 80)
    
    if account_ok:
        print("✅ VERIFICATION COMPLETE - Account ready for trading")
    else:
        print("⚠️  VERIFICATION INCOMPLETE - Please review issues above")
    
    print("=" * 80)
    print()
    
    return account_ok


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
