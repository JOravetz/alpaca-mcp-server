#!/bin/bash
# Launch Live MCP Trading Dashboard - Complete Solution
# This script starts everything needed for the interactive dashboard

set -e

echo "🚀 LAUNCHING LIVE MCP TRADING DASHBOARD"
echo "========================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step 1: Clean up any existing processes
echo -e "${YELLOW}📋 Cleaning up previous instances...${NC}"
pkill -f "mcp_execution" 2>/dev/null || true
pkill -f "live_mcp" 2>/dev/null || true
pkill -f "port 8002" 2>/dev/null || true
fuser -k 8002/tcp 2>/dev/null || true
sleep 2
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Step 2: Create working backend service
echo -e "${YELLOW}📋 Creating backend service...${NC}"
cat > /tmp/mcp_live_backend.py << 'BACKEND'
#!/usr/bin/env python
"""Minimal working MCP backend service"""

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import actual MCP tools directly
from alpaca_mcp_server.tools.market_info_tools import get_market_clock
from alpaca_mcp_server.tools.market_data_tools import get_stock_quote
from alpaca_mcp_server.tools.account_tools import get_account_info
from alpaca_mcp_server.tools.day_trading_scanner import scan_day_trading_opportunities

app = FastAPI(title="Live MCP Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple tool registry for demo
TOOLS = {
    "get_market_clock": get_market_clock,
    "get_stock_quote": get_stock_quote,
    "get_account_info": get_account_info,
    "scan_day_trading_opportunities": scan_day_trading_opportunities,
}

@app.get("/health")
async def health():
    return {"status": "healthy", "tools": len(TOOLS)}

@app.get("/api/tools/list")
async def list_tools():
    return {
        "tools": [
            {"name": name, "description": func.__doc__ or "MCP Tool"} 
            for name, func in TOOLS.items()
        ]
    }

@app.post("/api/execute/tool/{tool_name}")
async def execute_tool(tool_name: str, params: dict = {}):
    if tool_name in TOOLS:
        try:
            result = await TOOLS[tool_name](**params.get("parameters", {}))
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "Tool not found"}

if __name__ == "__main__":
    print("Starting Live MCP Backend on port 8002...")
    uvicorn.run(app, host="0.0.0.0", port=8002)
BACKEND

echo -e "${GREEN}✓ Backend service created${NC}"

# Step 3: Start the backend
echo -e "${YELLOW}📋 Starting backend service...${NC}"
nohup uv run python /tmp/mcp_live_backend.py > /tmp/mcp_backend.log 2>&1 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 3
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend service running on port 8002${NC}"
else
    echo -e "${YELLOW}⚠ Backend may not be fully ready yet${NC}"
fi

# Step 4: Launch the dashboard
echo -e "${YELLOW}📋 Launching interactive dashboard...${NC}"
DASHBOARD="/home/jjoravet/alpaca-mcp-server-enhanced/interactive_dashboard.html"

if [ -f "$DASHBOARD" ]; then
    chromium --new-window "file://$DASHBOARD" 2>/dev/null &
    echo -e "${GREEN}✓ Dashboard launched in browser${NC}"
else
    echo "Dashboard file: $DASHBOARD"
fi

echo ""
echo "========================================"
echo -e "${GREEN}🎉 LIVE MCP TRADING DASHBOARD READY!${NC}"
echo "========================================"
echo ""
echo "📊 Backend API: http://localhost:8002"
echo "📁 Dashboard: file://$DASHBOARD"
echo "📝 Logs: /tmp/mcp_backend.log"
echo ""
echo "Available for testing:"
echo "  • Market Clock - Get market status"
echo "  • Stock Quote - Get real-time quotes"
echo "  • Account Info - View account details"
echo "  • Day Trading Scanner - Find opportunities"
echo ""
echo "The dashboard provides modals for each tool with:"
echo "  ✓ Parameter input forms"
echo "  ✓ Execute buttons"
echo "  ✓ Real-time results"
echo "  ✓ Error handling"
echo ""
echo "To stop the service:"
echo "  kill $BACKEND_PID"
echo ""