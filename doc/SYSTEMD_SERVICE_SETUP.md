# Active Trader Systemd Service Installation Guide

## Overview
This guide will help you install the Active Day Trader as a systemd service for maximum reliability and automatic restarts.

**Benefits:**
- ✅ Automatic startup on system boot
- ✅ Automatic restart on failures
- ✅ Centralized logging via systemd journal
- ✅ Easy service management (start/stop/restart)
- ✅ Resource limits and monitoring
- ✅ Runs in background as daemon

---

## Quick Start (Recommended)

### 1. Install the Service
```bash
cd /home/mfan/work/aitrader
sudo ./manage_service.sh install
```

### 2. Start MCP Services (Required)
```bash
./manage_service.sh start-mcp
```

### 3. Start the Active Trader Service
```bash
sudo ./manage_service.sh start
```

### 4. Check Status
```bash
sudo ./manage_service.sh status
```

That's it! The service is now running and will automatically restart on failures.

---

## Detailed Installation Steps

### Prerequisites
1. **Python Virtual Environment**: `/home/mfan/work/aitrader/.venv/`
2. **MCP Services**: Alpaca Data (8004) and Alpaca Trade (8005)
3. **Configuration**: `configs/default_config.json` properly configured
4. **Dependencies**: All Python packages installed in venv

### Step-by-Step Installation

#### Step 1: Verify Prerequisites
```bash
cd /home/mfan/work/aitrader

# Activate virtual environment
source .venv/bin/activate

# Verify TA-Lib is installed
python -c "import talib; print('TA-Lib OK')"

# Verify configuration exists
ls -la configs/default_config.json

# Test active trader manually (optional)
python active_trader.py
# Press Ctrl+C to stop
```

#### Step 2: Install the Systemd Service
```bash
# Install service (requires sudo)
sudo ./manage_service.sh install

# Output should show:
# ✅ Service file copied to /etc/systemd/system
# ✅ Systemd daemon reloaded
# ✅ Service enabled to start on boot
# ✅ Active Trader service installed successfully!
```

#### Step 3: Start MCP Services
The active trader requires MCP services to be running first.

```bash
# Check if MCP services are already running
./manage_service.sh check-mcp

# If not running, start them
./manage_service.sh start-mcp

# Verify they're running
./manage_service.sh check-mcp
# Should show:
# ✅ Alpaca Data MCP running on port 8004
# ✅ Alpaca Trade MCP running on port 8005
```

#### Step 4: Start the Active Trader Service
```bash
# Start the service
sudo ./manage_service.sh start

# Check status
sudo ./manage_service.sh status
```

#### Step 5: Verify Service is Running
```bash
# Check service status
sudo systemctl status active-trader

# Follow logs in real-time
sudo ./manage_service.sh follow
# Press Ctrl+C to exit

# Check last 50 log lines
sudo ./manage_service.sh logs
```

---

## Service Management Commands

### Using the Helper Script (Recommended)

```bash
# Install service
sudo ./manage_service.sh install

# Uninstall service
sudo ./manage_service.sh uninstall

# Start service
sudo ./manage_service.sh start

# Stop service
sudo ./manage_service.sh stop

# Restart service
sudo ./manage_service.sh restart

# Check status
sudo ./manage_service.sh status

# View logs (last 50 lines)
sudo ./manage_service.sh logs

# Follow logs in real-time
sudo ./manage_service.sh follow

# Check MCP services
./manage_service.sh check-mcp

# Start MCP services
./manage_service.sh start-mcp

# Show help
./manage_service.sh help
```

### Using Systemctl Directly

```bash
# Start service
sudo systemctl start active-trader

# Stop service
sudo systemctl stop active-trader

# Restart service
sudo systemctl restart active-trader

# Check status
sudo systemctl status active-trader

# Enable service (start on boot)
sudo systemctl enable active-trader

# Disable service (don't start on boot)
sudo systemctl disable active-trader

# View logs
sudo journalctl -u active-trader -f

# View last 100 lines
sudo journalctl -u active-trader -n 100

# View logs from today
sudo journalctl -u active-trader --since today

# View logs with priority
sudo journalctl -u active-trader -p err
```

---

## Log Files

The service creates multiple log files:

### 1. Systemd Journal (Recommended)
```bash
# Follow logs in real-time
sudo journalctl -u active-trader -f

# Last 50 lines
sudo journalctl -u active-trader -n 50

# Logs from today
sudo journalctl -u active-trader --since today

# Logs with timestamps
sudo journalctl -u active-trader -o short-iso
```

### 2. Service Output Logs
```bash
# Standard output (trading activity)
tail -f /home/mfan/work/aitrader/logs/active_trader_stdout.log

# Standard error (errors and warnings)
tail -f /home/mfan/work/aitrader/logs/active_trader_stderr.log
```

### 3. Python Application Log
```bash
# Application-level logging
tail -f /home/mfan/work/aitrader/active_trader.log
```

### 4. Agent Trading Logs (Detailed Decision History)
```bash
# View today's trading decisions
tail -f /home/mfan/work/aitrader/data/agent_data/xai-grok-4.1-fast/log/$(date +%Y-%m-%d)/log.jsonl

# Pretty-print last entry
tail -1 /home/mfan/work/aitrader/data/agent_data/xai-grok-4.1-fast/log/$(date +%Y-%m-%d)/log.jsonl | jq '.'
```

### 4. View All Logs Together
```bash
# Watch all logs in separate terminals
# Terminal 1: System logs
sudo journalctl -u active-trader -f

# Terminal 2: Python logs
tail -f /home/mfan/work/aitrader/active_trader.log

# Terminal 3: Service output
tail -f /home/mfan/work/aitrader/logs/active_trader_stdout.log
```

---

## Service Configuration

The service file is located at: `/etc/systemd/system/active-trader.service`

### Key Configuration Options

```ini
[Unit]
Description=Active Day Trading Program - AI Trader
After=network-online.target      # Wait for network
Wants=network-online.target

[Service]
Type=simple                      # Simple service type
User=mfan                        # Run as user mfan
WorkingDirectory=/home/mfan/work/aitrader

# IMPORTANT: Use the virtual environment Python!
ExecStart=/home/mfan/work/aitrader/.venv/bin/python /home/mfan/work/aitrader/active_trader.py

# Auto-restart configuration
Restart=always                   # Always restart on failure
RestartSec=30                    # Wait 30s before restart

# Logging
StandardOutput=append:/home/mfan/work/aitrader/logs/active_trader_stdout.log
StandardError=append:/home/mfan/work/aitrader/logs/active_trader_stderr.log

[Install]
WantedBy=multi-user.target      # Start on boot
```

### Modify Service Configuration

1. Edit the service file:
```bash
sudo nano /etc/systemd/system/active-trader.service
```

2. Reload systemd after changes:
```bash
sudo systemctl daemon-reload
```

3. Restart service:
```bash
sudo systemctl restart active-trader
```

### Change Trading Interval

To change the 2-minute interval, edit the service file:

```bash
sudo nano /etc/systemd/system/active-trader.service
```

Change the `ExecStart` line:
```ini
# For 2 minutes (default)
ExecStart=/home/mfan/work/aitrader/.venv/bin/python /home/mfan/work/aitrader/active_trader.py

# For 5 minutes
ExecStart=/home/mfan/work/aitrader/.venv/bin/python /home/mfan/work/aitrader/active_trader.py /home/mfan/work/aitrader/configs/default_config.json 5

# For 1 minute (very high frequency)
ExecStart=/home/mfan/work/aitrader/.venv/bin/python /home/mfan/work/aitrader/active_trader.py /home/mfan/work/aitrader/configs/default_config.json 1
```

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart active-trader
```

---

## Troubleshooting

### Service Won't Start

**1. Check service status:**
```bash
sudo systemctl status active-trader
```

**2. Check logs for errors:**
```bash
sudo journalctl -u active-trader -n 100
```

**3. Common issues:**

**MCP services not running:**
```bash
./manage_service.sh check-mcp
./manage_service.sh start-mcp
```

**Configuration file missing:**
```bash
ls -la configs/default_config.json
```

**Virtual environment issues:**
```bash
source /home/mfan/work/bin/activate
python -c "import talib; print('OK')"
```

**Permission issues:**
```bash
ls -la /home/mfan/work/aitrader/
# Should be owned by mfan:mfan
```

### Service Keeps Restarting

**Check what's causing restarts:**
```bash
sudo journalctl -u active-trader | grep -i restart
```

**View error logs:**
```bash
tail -50 /home/mfan/work/aitrader/logs/active_trader_stderr.log
```

**Check Python errors:**
```bash
tail -50 /home/mfan/work/aitrader/active_trader.log
```

### High CPU Usage

**Check current process:**
```bash
top -u mfan
```

**Reduce trading frequency:**
Edit service to use longer interval (e.g., 5 minutes instead of 2)

### Service Not Auto-Starting on Boot

**Enable the service:**
```bash
sudo systemctl enable active-trader
```

**Verify it's enabled:**
```bash
sudo systemctl is-enabled active-trader
```

---

## Monitoring and Alerts

### Check Service Health
```bash
# Is service running?
sudo systemctl is-active active-trader

# Get service status
sudo systemctl status active-trader

# Check for failures
sudo systemctl is-failed active-trader
```

### Monitor Performance
```bash
# CPU and memory usage
top -p $(pgrep -f "active_trader.py")

# Detailed process info
ps aux | grep active_trader

# Resource limits
systemctl show active-trader | grep -i limit
```

### Set Up Email Alerts (Optional)

Install monitoring tools:
```bash
sudo apt-get install mailutils
```

Create alert script at `/usr/local/bin/trader-alert.sh`:
```bash
#!/bin/bash
if ! systemctl is-active --quiet active-trader; then
    echo "Active Trader service is down!" | mail -s "ALERT: Trader Down" your@email.com
fi
```

Add to crontab:
```bash
# Check every 5 minutes
*/5 * * * * /usr/local/bin/trader-alert.sh
```

---

## Maintenance

### Update the Service

**1. Stop the service:**
```bash
sudo systemctl stop active-trader
```

**2. Update code:**
```bash
cd /home/mfan/work/aitrader
git pull  # or make your changes
```

**3. Restart service:**
```bash
sudo systemctl start active-trader
```

### Clean Log Files

```bash
# Clean old logs (keep last 7 days)
find /home/mfan/work/aitrader/logs -name "*.log" -mtime +7 -delete

# Rotate systemd journal
sudo journalctl --vacuum-time=7d
```

### Backup Configuration

```bash
# Backup service file
sudo cp /etc/systemd/system/active-trader.service ~/backup/

# Backup configuration
cp configs/default_config.json ~/backup/

# Backup logs
tar -czf ~/backup/logs_$(date +%Y%m%d).tar.gz logs/

# Backup agent data and momentum cache
tar -czf ~/backup/agent_data_$(date +%Y%m%d).tar.gz data/agent_data/
```

---

## Uninstall

To completely remove the service:

```bash
# Stop and uninstall
sudo ./manage_services.sh uninstall

# Remove logs (optional)
rm -rf /home/mfan/work/aitrader/logs/

# Remove service files (already removed by uninstall)
# Service files are automatically removed from /etc/systemd/system/
```

---

## Best Practices

### 1. Always Check MCP Services First
Before starting the trader service, ensure MCP services are running:
```bash
./manage_services.sh check-mcp
```

### 2. Monitor Logs Regularly
```bash
# Daily log check
sudo ./manage_services.sh logs

# Watch for errors
sudo journalctl -u active-trader -p err --since today
```

### 3. Test Changes Before Deployment
```bash
# Test manually first
source .venv/bin/activate
python active_trader.py
# Ctrl+C to stop

# Then deploy to service
sudo systemctl restart active-trader
```

### 4. Keep Service Updated
```bash
# After code changes
sudo systemctl restart active-trader

# After configuration changes
sudo systemctl daemon-reload
sudo systemctl restart active-trader
```

### 5. Regular Health Checks
Create a daily check script:
```bash
#!/bin/bash
# daily_check.sh

echo "=== Active Trader Health Check ==="
echo "Date: $(date)"
echo ""

# Service status
echo "Service Status:"
sudo systemctl is-active active-trader && echo "✅ Running" || echo "❌ Not Running"
echo ""

# MCP services
echo "MCP Services:"
lsof -i :8004 >/dev/null 2>&1 && echo "✅ Alpaca Data (8004)" || echo "❌ Alpaca Data"
lsof -i :8005 >/dev/null 2>&1 && echo "✅ Alpaca Trade (8005)" || echo "❌ Alpaca Trade"
echo ""

# Recent errors
echo "Recent Errors (last hour):"
sudo journalctl -u active-trader --since "1 hour ago" -p err --no-pager
```

---

## Production Deployment Checklist

- [ ] Virtual environment activated and tested
- [ ] TA-Lib installed and working
- [ ] MCP services running on ports 8004 & 8005
- [ ] Configuration file validated
- [ ] Log directory created
- [ ] Service installed with `sudo ./manage_service.sh install`
- [ ] Service started with `sudo ./manage_service.sh start`
- [ ] Service status verified with `sudo ./manage_service.sh status`
- [ ] Logs checked with `sudo ./manage_service.sh follow`
- [ ] Auto-restart tested (kill process and watch it restart)
- [ ] Monitoring/alerts configured (optional)

---

## Support

For issues:
1. Check logs: `sudo ./manage_service.sh logs`
2. Check status: `sudo ./manage_service.sh status`
3. Check MCP: `./manage_service.sh check-mcp`
4. Review error logs: `tail -50 logs/active_trader_stderr.log`

**Service runs reliably 24/7 with automatic recovery!** 🚀
