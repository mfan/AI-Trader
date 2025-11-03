#!/bin/bash
# Service Management Script for Active Day Trader and Alpaca MCP Services
# This script helps install, start, stop, and monitor both systemd services

set -e

TRADER_SERVICE="active-trader"
TRADER_SERVICE_FILE="active-trader.service"
MCP_SERVICE="alpaca-mcp"
MCP_SERVICE_FILE="alpaca-mcp.service"
SYSTEMD_DIR="/etc/systemd/system"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
VENV_PATH="/home/mfan/work/bin/activate"

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

install_service() {
    check_root
    
    print_info "Installing Alpaca MCP and Active Trader services..."
    
    # Create log directory
    create_log_directory
    
    # Install MCP service
    if [ -f "${SCRIPT_DIR}/${MCP_SERVICE_FILE}" ]; then
        cp "${SCRIPT_DIR}/${MCP_SERVICE_FILE}" "${SYSTEMD_DIR}/${MCP_SERVICE_FILE}"
        print_success "MCP service file copied to ${SYSTEMD_DIR}"
    else
        print_error "MCP service file not found: ${SCRIPT_DIR}/${MCP_SERVICE_FILE}"
        exit 1
    fi
    
    # Install Trader service
    if [ -f "${SCRIPT_DIR}/${TRADER_SERVICE_FILE}" ]; then
        cp "${SCRIPT_DIR}/${TRADER_SERVICE_FILE}" "${SYSTEMD_DIR}/${TRADER_SERVICE_FILE}"
        print_success "Trader service file copied to ${SYSTEMD_DIR}"
    else
        print_error "Trader service file not found: ${SCRIPT_DIR}/${TRADER_SERVICE_FILE}"
        exit 1
    fi
    
    # Reload systemd daemon
    systemctl daemon-reload
    print_success "Systemd daemon reloaded"
    
    # Enable both services to start on boot
    systemctl enable "${MCP_SERVICE}"
    systemctl enable "${TRADER_SERVICE}"
    print_success "Both services enabled to start on boot"
    
    print_success "Alpaca MCP and Active Trader services installed successfully!"
    print_info "Use './manage_service.sh start' to start both services"
}

uninstall_service() {
    check_root
    
    print_info "Uninstalling Alpaca MCP and Active Trader services..."
    
    # Stop both services if running
    if systemctl is-active --quiet "${TRADER_SERVICE}"; then
        systemctl stop "${TRADER_SERVICE}"
        print_success "Trader service stopped"
    fi
    
    if systemctl is-active --quiet "${MCP_SERVICE}"; then
        systemctl stop "${MCP_SERVICE}"
        print_success "MCP service stopped"
    fi
    
    # Disable both services
    systemctl disable "${TRADER_SERVICE}" 2>/dev/null || true
    systemctl disable "${MCP_SERVICE}" 2>/dev/null || true
    print_success "Services disabled"
    
    # Remove service files
    if [ -f "${SYSTEMD_DIR}/${TRADER_SERVICE_FILE}" ]; then
        rm "${SYSTEMD_DIR}/${TRADER_SERVICE_FILE}"
        print_success "Trader service file removed"
    fi
    
    if [ -f "${SYSTEMD_DIR}/${MCP_SERVICE_FILE}" ]; then
        rm "${SYSTEMD_DIR}/${MCP_SERVICE_FILE}"
        print_success "MCP service file removed"
    fi
    
    # Reload systemd daemon
    systemctl daemon-reload
    print_success "Systemd daemon reloaded"
    
    print_success "Both services uninstalled successfully!"
}

start_service() {
    check_root
    
    print_info "Starting Alpaca MCP service first..."
    systemctl start "${MCP_SERVICE}"
    sleep 3
    
    if systemctl is-active --quiet "${MCP_SERVICE}"; then
        print_success "MCP service started successfully!"
    else
        print_error "MCP service failed to start"
        exit 1
    fi
    
    print_info "Starting Active Trader service..."
    systemctl start "${TRADER_SERVICE}"
    sleep 2
    
    if systemctl is-active --quiet "${TRADER_SERVICE}"; then
        print_success "Trader service started successfully!"
        show_status
    else
        print_error "Trader service failed to start"
        print_info "Check logs with: sudo journalctl -u ${TRADER_SERVICE} -n 50"
        exit 1
    fi
}

stop_service() {
    check_root
    
    print_info "Stopping Active Trader service..."
    systemctl stop "${TRADER_SERVICE}"
    print_success "Trader service stopped!"
    
    print_info "Stopping Alpaca MCP service..."
    systemctl stop "${MCP_SERVICE}"
    print_success "MCP service stopped!"
}

restart_service() {
    check_root
    
    print_info "Restarting Alpaca MCP service..."
    systemctl restart "${MCP_SERVICE}"
    sleep 3
    
    print_info "Restarting Active Trader service..."
    systemctl restart "${TRADER_SERVICE}"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet "${TRADER_SERVICE}"; then
        print_success "Services restarted successfully!"
        show_status
    else
        print_error "Service failed to restart. Check logs with: sudo journalctl -u ${TRADER_SERVICE} -n 50"
        exit 1
    fi
}

show_status() {
    print_info "Service Status:"
    echo ""
    echo "=== Alpaca MCP Service ==="
    systemctl status "${MCP_SERVICE}" --no-pager || true
    echo ""
    echo "=== Active Trader Service ==="
    systemctl status "${TRADER_SERVICE}" --no-pager || true
}

show_logs() {
    print_info "Showing last 50 lines of service logs..."
    echo ""
    echo "=== Alpaca MCP Logs ==="
    journalctl -u "${MCP_SERVICE}" -n 25 --no-pager
    echo ""
    echo "=== Active Trader Logs ==="
    journalctl -u "${TRADER_SERVICE}" -n 25 --no-pager
}

follow_logs() {
    SERVICE="${1:-${TRADER_SERVICE}}"
    print_info "Following ${SERVICE} logs (Ctrl+C to exit)..."
    echo ""
    journalctl -u "${SERVICE}" -f
}

check_mcp_services() {
    print_info "Checking MCP services..."
    echo ""
    
    # Check Alpaca Data (port 8004)
    if lsof -i :8004 >/dev/null 2>&1; then
        print_success "Alpaca Data MCP running on port 8004"
    else
        print_warning "Alpaca Data MCP not running on port 8004"
    fi
    
    # Check Alpaca Trade (port 8005)
    if lsof -i :8005 >/dev/null 2>&1; then
        print_success "Alpaca Trade MCP running on port 8005"
    else
        print_warning "Alpaca Trade MCP not running on port 8005"
    fi
}

start_mcp_services() {
    print_info "Starting MCP services..."
    
    # Activate virtual environment and start MCP services
    source "${VENV_PATH}"
    cd "${SCRIPT_DIR}"
    
    # Check if already running
    if lsof -i :8004 >/dev/null 2>&1 && lsof -i :8005 >/dev/null 2>&1; then
        print_warning "MCP services already running"
        check_mcp_services
        return
    fi
    
    # Start MCP services in background
    nohup python agent_tools/start_mcp_services.py > logs/mcp_services.log 2>&1 &
    MCP_PID=$!
    
    print_info "Waiting for MCP services to start..."
    sleep 5
    
    check_mcp_services
    print_success "MCP services started (PID: ${MCP_PID})"
}

show_help() {
    echo "Active Day Trader Service Management"
    echo ""
    echo "Usage: $0 {install|uninstall|start|stop|restart|status|logs|follow|check-mcp|start-mcp|help}"
    echo ""
    echo "Commands:"
    echo "  install      Install the service (requires sudo)"
    echo "  uninstall    Uninstall the service (requires sudo)"
    echo "  start        Start the service (requires sudo)"
    echo "  stop         Stop the service (requires sudo)"
    echo "  restart      Restart the service (requires sudo)"
    echo "  status       Show service status"
    echo "  logs         Show last 50 lines of logs"
    echo "  follow       Follow logs in real-time (Ctrl+C to exit)"
    echo "  check-mcp    Check if MCP services are running"
    echo "  start-mcp    Start MCP services"
    echo "  help         Show this help message"
    echo ""
    echo "Log files:"
    echo "  Service logs:  /home/mfan/work/aitrader/logs/active_trader_stdout.log"
    echo "  Error logs:    /home/mfan/work/aitrader/logs/active_trader_stderr.log"
    echo "  Python logs:   /home/mfan/work/aitrader/active_trader.log"
    echo "  System logs:   sudo journalctl -u ${SERVICE_NAME}"
    echo ""
}

# Main script
case "$1" in
    install)
        install_service
        ;;
    uninstall)
        uninstall_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    follow)
        follow_logs
        ;;
    check-mcp)
        check_mcp_services
        ;;
    start-mcp)
        start_mcp_services
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
