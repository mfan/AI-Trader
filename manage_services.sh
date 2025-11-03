#!/bin/bash
# Service Management Script for Active Day Trader + MCP Services
# Manages: alpaca-data.service, alpaca-trade.service, active-trader.service

set -e

ALPACA_DATA_SERVICE="alpaca-data"
ALPACA_TRADE_SERVICE="alpaca-trade"
ACTIVE_TRADER_SERVICE="active-trader"
SYSTEMD_DIR="/etc/systemd/system"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This operation requires root privileges. Please run with sudo."
        exit 1
    fi
}

create_log_directory() {
    print_info "Creating log directory..."
    mkdir -p "${LOG_DIR}"
    chown mfan:mfan "${LOG_DIR}"
    print_success "Log directory created: ${LOG_DIR}"
}

install_all_services() {
    check_root
    
    print_info "Installing all services (Alpaca Data + Trade + Active Trader)..."
    
    # Create log directory
    create_log_directory
    
    # Install Alpaca Data MCP
    if [ -f "${SCRIPT_DIR}/alpaca-data.service" ]; then
        cp "${SCRIPT_DIR}/alpaca-data.service" "${SYSTEMD_DIR}/"
        print_success "Alpaca Data service file installed"
    else
        print_error "alpaca-data.service not found"
        exit 1
    fi
    
    # Install Alpaca Trade MCP
    if [ -f "${SCRIPT_DIR}/alpaca-trade.service" ]; then
        cp "${SCRIPT_DIR}/alpaca-trade.service" "${SYSTEMD_DIR}/"
        print_success "Alpaca Trade service file installed"
    else
        print_error "alpaca-trade.service not found"
        exit 1
    fi
    
    # Install Active Trader
    if [ -f "${SCRIPT_DIR}/active-trader.service" ]; then
        cp "${SCRIPT_DIR}/active-trader.service" "${SYSTEMD_DIR}/"
        print_success "Active Trader service file installed"
    else
        print_error "active-trader.service not found"
        exit 1
    fi
    
    # Reload systemd daemon
    systemctl daemon-reload
    print_success "Systemd daemon reloaded"
    
    # Enable services to start on boot
    systemctl enable "${ALPACA_DATA_SERVICE}"
    systemctl enable "${ALPACA_TRADE_SERVICE}"
    systemctl enable "${ACTIVE_TRADER_SERVICE}"
    print_success "All services enabled to start on boot"
    
    print_success "All services installed successfully!"
    print_info ""
    print_info "Next steps:"
    print_info "  1. Start MCP services: sudo $0 start-mcp"
    print_info "  2. Start trader: sudo $0 start-trader"
    print_info "  Or start all: sudo $0 start-all"
}

uninstall_all_services() {
    check_root
    
    print_info "Uninstalling all services..."
    
    # Stop all services
    systemctl stop "${ACTIVE_TRADER_SERVICE}" 2>/dev/null || true
    systemctl stop "${ALPACA_DATA_SERVICE}" 2>/dev/null || true
    systemctl stop "${ALPACA_TRADE_SERVICE}" 2>/dev/null || true
    
    # Disable services
    systemctl disable "${ACTIVE_TRADER_SERVICE}" 2>/dev/null || true
    systemctl disable "${ALPACA_DATA_SERVICE}" 2>/dev/null || true
    systemctl disable "${ALPACA_TRADE_SERVICE}" 2>/dev/null || true
    
    # Remove service files
    rm -f "${SYSTEMD_DIR}/alpaca-data.service"
    rm -f "${SYSTEMD_DIR}/alpaca-trade.service"
    rm -f "${SYSTEMD_DIR}/active-trader.service"
    
    # Reload systemd daemon
    systemctl daemon-reload
    print_success "All services uninstalled successfully!"
}

start_mcp_services() {
    check_root
    
    print_info "Starting MCP services..."
    systemctl start "${ALPACA_DATA_SERVICE}"
    systemctl start "${ALPACA_TRADE_SERVICE}"
    
    sleep 2
    
    if systemctl is-active --quiet "${ALPACA_DATA_SERVICE}"; then
        print_success "Alpaca Data MCP started"
    else
        print_error "Alpaca Data MCP failed to start"
        return 1
    fi
    
    if systemctl is-active --quiet "${ALPACA_TRADE_SERVICE}"; then
        print_success "Alpaca Trade MCP started"
    else
        print_error "Alpaca Trade MCP failed to start"
        return 1
    fi
}

start_trader() {
    check_root
    
    # Check if MCP services are running
    if ! systemctl is-active --quiet "${ALPACA_DATA_SERVICE}"; then
        print_warning "Alpaca Data MCP not running. Starting it first..."
        systemctl start "${ALPACA_DATA_SERVICE}"
        sleep 2
    fi
    
    if ! systemctl is-active --quiet "${ALPACA_TRADE_SERVICE}"; then
        print_warning "Alpaca Trade MCP not running. Starting it first..."
        systemctl start "${ALPACA_TRADE_SERVICE}"
        sleep 2
    fi
    
    print_info "Starting Active Trader service..."
    systemctl start "${ACTIVE_TRADER_SERVICE}"
    
    sleep 2
    if systemctl is-active --quiet "${ACTIVE_TRADER_SERVICE}"; then
        print_success "Active Trader started successfully!"
        show_status_all
    else
        print_error "Active Trader failed to start"
        print_info "Check logs with: sudo journalctl -u ${ACTIVE_TRADER_SERVICE} -n 50"
        return 1
    fi
}

start_all() {
    check_root
    
    print_info "Starting all services..."
    start_mcp_services
    sleep 2
    start_trader
}

stop_mcp_services() {
    check_root
    
    print_info "Stopping MCP services..."
    systemctl stop "${ALPACA_DATA_SERVICE}"
    systemctl stop "${ALPACA_TRADE_SERVICE}"
    print_success "MCP services stopped"
}

stop_trader() {
    check_root
    
    print_info "Stopping Active Trader..."
    systemctl stop "${ACTIVE_TRADER_SERVICE}"
    print_success "Active Trader stopped"
}

stop_all() {
    check_root
    
    print_info "Stopping all services..."
    stop_trader
    stop_mcp_services
    print_success "All services stopped"
}

restart_mcp_services() {
    check_root
    
    print_info "Restarting MCP services..."
    systemctl restart "${ALPACA_DATA_SERVICE}"
    systemctl restart "${ALPACA_TRADE_SERVICE}"
    
    sleep 2
    if systemctl is-active --quiet "${ALPACA_DATA_SERVICE}" && \
       systemctl is-active --quiet "${ALPACA_TRADE_SERVICE}"; then
        print_success "MCP services restarted successfully!"
    else
        print_error "MCP services failed to restart"
        return 1
    fi
}

restart_trader() {
    check_root
    
    print_info "Restarting Active Trader..."
    systemctl restart "${ACTIVE_TRADER_SERVICE}"
    
    sleep 2
    if systemctl is-active --quiet "${ACTIVE_TRADER_SERVICE}"; then
        print_success "Active Trader restarted successfully!"
    else
        print_error "Active Trader failed to restart"
        return 1
    fi
}

restart_all() {
    check_root
    
    print_info "Restarting all services..."
    restart_mcp_services
    sleep 2
    restart_trader
}

show_status_mcp() {
    print_info "MCP Services Status:"
    echo ""
    systemctl status "${ALPACA_DATA_SERVICE}" --no-pager || true
    echo ""
    systemctl status "${ALPACA_TRADE_SERVICE}" --no-pager || true
}

show_status_trader() {
    print_info "Active Trader Status:"
    echo ""
    systemctl status "${ACTIVE_TRADER_SERVICE}" --no-pager || true
}

show_status_all() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_info "Service Status Summary:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Alpaca Data
    if systemctl is-active --quiet "${ALPACA_DATA_SERVICE}"; then
        print_success "Alpaca Data MCP:  RUNNING"
    else
        print_error "Alpaca Data MCP:  STOPPED"
    fi
    
    # Alpaca Trade
    if systemctl is-active --quiet "${ALPACA_TRADE_SERVICE}"; then
        print_success "Alpaca Trade MCP: RUNNING"
    else
        print_error "Alpaca Trade MCP: STOPPED"
    fi
    
    # Active Trader
    if systemctl is-active --quiet "${ACTIVE_TRADER_SERVICE}"; then
        print_success "Active Trader:    RUNNING"
    else
        print_error "Active Trader:    STOPPED"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

show_logs_mcp() {
    print_info "MCP Services Logs (last 30 lines each):"
    echo ""
    echo "=== Alpaca Data MCP ==="
    journalctl -u "${ALPACA_DATA_SERVICE}" -n 30 --no-pager
    echo ""
    echo "=== Alpaca Trade MCP ==="
    journalctl -u "${ALPACA_TRADE_SERVICE}" -n 30 --no-pager
}

show_logs_trader() {
    print_info "Active Trader Logs (last 50 lines):"
    echo ""
    journalctl -u "${ACTIVE_TRADER_SERVICE}" -n 50 --no-pager
}

show_logs_all() {
    show_logs_mcp
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    show_logs_trader
}

follow_logs_mcp() {
    print_info "Following MCP logs (Ctrl+C to exit)..."
    journalctl -u "${ALPACA_DATA_SERVICE}" -u "${ALPACA_TRADE_SERVICE}" -f
}

follow_logs_trader() {
    print_info "Following Active Trader logs (Ctrl+C to exit)..."
    journalctl -u "${ACTIVE_TRADER_SERVICE}" -f
}

follow_logs_all() {
    print_info "Following all logs (Ctrl+C to exit)..."
    journalctl -u "${ALPACA_DATA_SERVICE}" -u "${ALPACA_TRADE_SERVICE}" -u "${ACTIVE_TRADER_SERVICE}" -f
}

show_help() {
    cat << EOF
Active Day Trader + MCP Services Management

Usage: $0 <command>

Installation Commands:
  install            Install all services (MCP + Trader)
  uninstall          Uninstall all services

Start Commands:
  start-mcp          Start MCP services only
  start-trader       Start Active Trader only  
  start-all          Start all services (recommended)

Stop Commands:
  stop-mcp           Stop MCP services only
  stop-trader        Stop Active Trader only
  stop-all           Stop all services

Restart Commands:
  restart-mcp        Restart MCP services only
  restart-trader     Restart Active Trader only
  restart-all        Restart all services

Status Commands:
  status-mcp         Show MCP services status
  status-trader      Show Active Trader status
  status             Show all services status

Log Commands:
  logs-mcp           Show MCP services logs (last 30 lines)
  logs-trader        Show Active Trader logs (last 50 lines)
  logs               Show all logs
  follow-mcp         Follow MCP services logs in real-time
  follow-trader      Follow Active Trader logs in real-time
  follow             Follow all logs in real-time

Other Commands:
  help               Show this help message

Services:
  - alpaca-data.service    Alpaca Data MCP (port 8004) with TA-Lib
  - alpaca-trade.service   Alpaca Trade MCP (port 8005)
  - active-trader.service  Active Day Trader (2-min cycles)

Log files:
  - /home/mfan/work/aitrader/logs/alpaca_data_mcp.log
  - /home/mfan/work/aitrader/logs/alpaca_trade_mcp.log
  - /home/mfan/work/aitrader/logs/active_trader_stdout.log
  - System logs: sudo journalctl -u <service-name>

EOF
}

# Main script
case "$1" in
    install)
        install_all_services
        ;;
    uninstall)
        uninstall_all_services
        ;;
    start-mcp)
        start_mcp_services
        ;;
    start-trader)
        start_trader
        ;;
    start-all)
        start_all
        ;;
    stop-mcp)
        stop_mcp_services
        ;;
    stop-trader)
        stop_trader
        ;;
    stop-all)
        stop_all
        ;;
    restart-mcp)
        restart_mcp_services
        ;;
    restart-trader)
        restart_trader
        ;;
    restart-all)
        restart_all
        ;;
    status-mcp)
        show_status_mcp
        ;;
    status-trader)
        show_status_trader
        ;;
    status)
        show_status_all
        ;;
    logs-mcp)
        show_logs_mcp
        ;;
    logs-trader)
        show_logs_trader
        ;;
    logs)
        show_logs_all
        ;;
    follow-mcp)
        follow_logs_mcp
        ;;
    follow-trader)
        follow_logs_trader
        ;;
    follow)
        follow_logs_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
