# Automatic API URL Selection

## Summary
Implemented automatic Alpaca API URL selection based on the `ALPACA_PAPER_TRADING` environment variable. No need to manually configure `ALPACA_BASE_URL` anymore!

## How It Works

The system now automatically selects the correct Alpaca API endpoint based on your trading mode:

### Paper Trading Mode (Default)
```bash
ALPACA_PAPER_TRADING="true"
```
**Auto-selects:** `https://paper-api.alpaca.markets`

### Live Trading Mode
```bash
ALPACA_PAPER_TRADING="false"
```
**Auto-selects:** `https://api.alpaca.markets`

## Configuration Priority

The URL selection follows this priority order:

1. **Explicit parameter**: If `base_url` is provided to `AlpacaTradingClient()`, use that
2. **Environment variable**: If `ALPACA_BASE_URL` is set in `.env`, use that
3. **Automatic selection**: Auto-select based on `ALPACA_PAPER_TRADING` value

## Updated .env Configuration

```bash
# Alpaca Trading API Configuration
ALPACA_API_KEY="your_api_key"
ALPACA_SECRET_KEY="your_secret_key"
ALPACA_PAPER_TRADING="true"  # Set to "false" for live trading

# ALPACA_BASE_URL is optional - will auto-select based on ALPACA_PAPER_TRADING:
#   - "true"  → https://paper-api.alpaca.markets (paper trading)
#   - "false" → https://api.alpaca.markets (live trading)
# Uncomment below only if you need to override the default URLs:
# ALPACA_BASE_URL="https://paper-api.alpaca.markets"
```

## Switching Between Paper and Live Trading

### To Use Paper Trading (Testing)
```bash
# In .env file
ALPACA_PAPER_TRADING="true"
# No need to set ALPACA_BASE_URL
```

### To Use Live Trading (Real Money)
```bash
# In .env file
ALPACA_PAPER_TRADING="false"
# No need to set ALPACA_BASE_URL
```

After changing the setting, restart the services:
```bash
sudo systemctl restart alpaca-trade.service
sudo systemctl restart active-trader.service
```

## Verification

The system logs show which mode and URL are being used:
```
✅ Alpaca client initialized (PAPER trading)
   API URL: https://paper-api.alpaca.markets
```

or

```
✅ Alpaca client initialized (LIVE trading)
   API URL: https://api.alpaca.markets
```

## Benefits

1. **Safer**: No risk of accidentally using wrong API URL
2. **Simpler**: Just toggle one environment variable
3. **Clearer**: Explicit paper vs live mode selection
4. **Flexible**: Can still override with custom URL if needed

## Implementation Details

Modified `tools/alpaca_trading.py`:
- Added automatic URL selection logic in `AlpacaTradingClient.__init__()`
- Respects explicit URLs when provided
- Falls back to environment variable if set
- Auto-selects appropriate URL based on trading mode
- Enhanced logging to show selected mode and URL

## Testing

Tested automatic URL selection:
```bash
✅ Paper mode: Correctly selects https://paper-api.alpaca.markets
✅ Live mode: Correctly selects https://api.alpaca.markets
✅ No manual URL configuration needed
```

## Date
November 3, 2025
