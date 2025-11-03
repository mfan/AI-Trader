# Active Trader Service - Pre-Installation Checklist

## Quick Verification Before Installation

Run these commands to verify everything is ready:

```bash
cd /home/mfan/work/aitrader

# 1. Virtual Environment
echo "1️⃣  Checking Virtual Environment..."
source /home/mfan/work/bin/activate && echo "✅ venv OK" || echo "❌ venv FAILED"

# 2. TA-Lib
echo "2️⃣  Checking TA-Lib..."
python -c "import talib; print('✅ TA-Lib OK')" 2>/dev/null || echo "❌ TA-Lib FAILED"

# 3. Configuration
echo "3️⃣  Checking Configuration..."
[ -f configs/default_config.json ] && echo "✅ Config OK" || echo "❌ Config MISSING"

# 4. Service Files
echo "4️⃣  Checking Service Files..."
[ -f active-trader.service ] && echo "✅ Service file OK" || echo "❌ Service file MISSING"
[ -x manage_service.sh ] && echo "✅ Management script OK" || echo "❌ Script not executable"

# 5. Logs Directory
echo "5️⃣  Checking Logs Directory..."
[ -d logs ] && echo "✅ Logs dir OK" || echo "❌ Logs dir MISSING"

# 6. MCP Services
echo "6️⃣  Checking MCP Services..."
lsof -i :8004 >/dev/null 2>&1 && echo "✅ Alpaca Data (8004) running" || echo "⚠️  Alpaca Data not running (will start later)"
lsof -i :8005 >/dev/null 2>&1 && echo "✅ Alpaca Trade (8005) running" || echo "⚠️  Alpaca Trade not running (will start later)"

echo ""
echo "✅ Pre-installation check complete!"
```

## Installation Steps (Copy-Paste Ready)

```bash
# Step 1: Install the systemd service
sudo ./manage_service.sh install

# Step 2: Start MCP services (if not already running)
./manage_service.sh start-mcp

# Step 3: Start the active trader service
sudo ./manage_service.sh start

# Step 4: Verify service is running
sudo ./manage_service.sh status

# Step 5: Watch logs
sudo ./manage_service.sh follow
# Press Ctrl+C to exit
```

## Post-Installation Verification

```bash
# 1. Check service is active
sudo systemctl is-active active-trader && echo "✅ Service RUNNING" || echo "❌ Service NOT RUNNING"

# 2. Check service is enabled (starts on boot)
sudo systemctl is-enabled active-trader && echo "✅ Auto-start ENABLED" || echo "❌ Auto-start DISABLED"

# 3. View recent logs
sudo journalctl -u active-trader -n 20 --no-pager

# 4. Check for errors
sudo journalctl -u active-trader -p err --since today --no-pager
```

## Common Issues & Quick Fixes

### Issue: Service won't start
```bash
# Check detailed error
sudo journalctl -u active-trader -n 50 --no-pager

# Common fix: MCP services not running
./manage_service.sh start-mcp
sudo systemctl restart active-trader
```

### Issue: Service keeps restarting
```bash
# View restart history
sudo journalctl -u active-trader | grep -i restart

# Check Python errors
tail -50 active_trader.log
```

### Issue: Permission denied
```bash
# Fix ownership
sudo chown -R mfan:mfan /home/mfan/work/aitrader
sudo systemctl restart active-trader
```

## Daily Monitoring Commands

```bash
# Quick health check
sudo systemctl status active-trader

# Check logs for errors
sudo journalctl -u active-trader --since today -p err

# View trading activity
tail -20 logs/active_trader_stdout.log

# Check MCP services
./manage_service.sh check-mcp
```

## Emergency Commands

```bash
# Stop everything
sudo systemctl stop active-trader

# Restart everything
sudo systemctl restart active-trader

# Complete reset
sudo systemctl stop active-trader
./manage_service.sh start-mcp
sudo systemctl start active-trader
```

---

**Ready to install? Start with the pre-installation check above!**
