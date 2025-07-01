#!/bin/bash

# Trading Signal Monitoring Startup Script
# Launches all monitoring services for real-time signal visibility

echo "🚀 Starting Trading Signal Monitoring System"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if service is running
check_service() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${GREEN}✓ Port $1 is active${NC}"
        return 0
    else
        echo -e "${RED}✗ Port $1 is not active${NC}"
        return 1
    fi
}

# 1. Check if FastAPI service is running
echo -e "\n${YELLOW}Checking FastAPI service...${NC}"
if check_service 8001; then
    echo "FastAPI monitoring service already running"
else
    echo "Starting FastAPI service..."
    cd /home/jjoravet/alpaca-mcp-server-enhanced
    python -m alpaca_mcp_server.monitoring.fastapi_service &
    FASTAPI_PID=$!
    sleep 3
    check_service 8001
fi

# 2. Start signal monitor in new terminal
echo -e "\n${YELLOW}Starting Signal Monitor...${NC}"
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal --title="Trading Signal Monitor" -- python3 /home/jjoravet/alpaca-mcp-server-enhanced/signal_monitor.py
elif command -v xterm &> /dev/null; then
    xterm -title "Trading Signal Monitor" -e python3 /home/jjoravet/alpaca-mcp-server-enhanced/signal_monitor.py &
else
    echo "Starting signal monitor in background..."
    python3 /home/jjoravet/alpaca-mcp-server-enhanced/signal_monitor.py &
    MONITOR_PID=$!
fi

# 3. Start WebSocket client in new terminal
echo -e "\n${YELLOW}Starting WebSocket Client...${NC}"
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal --title="WebSocket Signal Stream" -- python3 /home/jjoravet/alpaca-mcp-server-enhanced/websocket_client.py
elif command -v xterm &> /dev/null; then
    xterm -title "WebSocket Signal Stream" -e python3 /home/jjoravet/alpaca-mcp-server-enhanced/websocket_client.py &
else
    echo "Starting WebSocket client in background..."
    python3 /home/jjoravet/alpaca-mcp-server-enhanced/websocket_client.py &
    WS_PID=$!
fi

# 4. Enable desktop notifications
echo -e "\n${YELLOW}Desktop notifications enabled${NC}"
echo "You will receive popup notifications for:"
echo "  - Buy signals (fresh troughs)"
echo "  - Profit spike alerts"
echo "  - Order fill confirmations"

# 5. Display monitoring dashboard URL
echo -e "\n${GREEN}✅ All monitoring services started!${NC}"
echo -e "\n📊 Monitoring Dashboard: http://localhost:8001"
echo -e "📡 API Status: http://localhost:8001/status"
echo -e "📈 Positions: http://localhost:8001/positions"
echo -e "\n${YELLOW}Signal monitoring is now active!${NC}"
echo "Signals will appear in:"
echo "  1. Terminal windows (if supported)"
echo "  2. Desktop notifications"
echo "  3. Console output"
echo "  4. WebSocket stream"
echo -e "\nPress Ctrl+C to stop all services"

# Keep script running
trap "echo -e '\n${RED}Stopping monitoring services...${NC}'; kill $FASTAPI_PID $MONITOR_PID $WS_PID 2>/dev/null; exit" INT

# Wait for interrupt
while true; do
    sleep 1
done