#!/bin/bash
# Stop FastAPI Monitoring Service
# Gracefully shutdown the trading signal monitoring service

set -e

# Configuration
PID_FILE="monitoring_service.pid"
LOG_DIR="logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping FastAPI Monitoring Service${NC}"
echo "=================================================="

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}⚠️  No PID file found - service may not be running${NC}"
    
    # Check for any uvicorn processes
    UVICORN_PIDS=$(pgrep -f "uvicorn.*fastapi_service" 2>/dev/null || true)
    if [ -n "$UVICORN_PIDS" ]; then
        echo -e "${YELLOW}🔍 Found uvicorn processes running:${NC}"
        echo "$UVICORN_PIDS"
        echo -e "${BLUE}💡 Attempting to stop them...${NC}"
        
        for pid in $UVICORN_PIDS; do
            echo "Killing process $pid..."
            kill -TERM "$pid" 2>/dev/null || true
        done
        
        # Wait for graceful shutdown
        sleep 3
        
        # Force kill if still running
        for pid in $UVICORN_PIDS; do
            if ps -p "$pid" > /dev/null 2>&1; then
                echo "Force killing process $pid..."
                kill -KILL "$pid" 2>/dev/null || true
            fi
        done
        
        echo -e "${GREEN}✅ Orphaned processes cleaned up${NC}"
    else
        echo -e "${GREEN}✅ No monitoring service processes found${NC}"
    fi
    
    exit 0
fi

# Read PID
PID=$(cat "$PID_FILE")
echo "Found PID: $PID"

# Check if process is running
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Process $PID is not running${NC}"
    echo "Removing stale PID file..."
    rm -f "$PID_FILE"
    exit 0
fi

echo -e "${BLUE}🔍 Process $PID is running, attempting graceful shutdown...${NC}"

# Send SIGTERM for graceful shutdown
kill -TERM "$PID"

# Wait for graceful shutdown (max 10 seconds)
echo -e "${BLUE}⏳ Waiting for graceful shutdown...${NC}"
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Service stopped gracefully${NC}"
        rm -f "$PID_FILE"
        
        # Show final logs
        if [ -f "$LOG_DIR/monitoring_service.log" ]; then
            echo -e "${BLUE}📄 Final log entries:${NC}"
            tail -5 "$LOG_DIR/monitoring_service.log" 2>/dev/null || echo "Could not read logs"
        fi
        
        echo -e "${GREEN}🎉 FastAPI Monitoring Service stopped successfully!${NC}"
        exit 0
    fi
    
    echo -n "."
    sleep 1
done

echo ""
echo -e "${YELLOW}⚠️  Graceful shutdown timed out, forcing termination...${NC}"

# Force kill
kill -KILL "$PID" 2>/dev/null || true

# Wait a moment
sleep 2

# Verify it's stopped
if ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${RED}❌ Failed to stop process $PID${NC}"
    echo "You may need to manually kill it: kill -9 $PID"
    exit 1
else
    echo -e "${GREEN}✅ Service force-stopped${NC}"
    rm -f "$PID_FILE"
fi

# Clean up any remaining uvicorn processes
REMAINING_PIDS=$(pgrep -f "uvicorn.*fastapi_service" 2>/dev/null || true)
if [ -n "$REMAINING_PIDS" ]; then
    echo -e "${BLUE}🧹 Cleaning up remaining processes...${NC}"
    for pid in $REMAINING_PIDS; do
        kill -KILL "$pid" 2>/dev/null || true
    done
fi

echo -e "${GREEN}🎉 FastAPI Monitoring Service stopped successfully!${NC}"

# Show service status
echo ""
echo -e "${BLUE}📊 Port status (should be free):${NC}"
lsof -Pi :8001 -sTCP:LISTEN 2>/dev/null || echo "Port 8001 is now available"