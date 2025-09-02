#!/bin/bash
# Launch Live MCP Dashboard - Complete startup script
# This script:
# 1. Kills any existing server instances
# 2. Clears the port
# 3. Starts the MCP execution backend service
# 4. Launches the interactive dashboard in browser

set -e  # Exit on error

echo "🚀 Launching Live MCP Trading Dashboard"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PORT=8002
SERVICE_NAME="mcp_execution_service"
LOG_FILE="logs/mcp_execution_service.log"
DASHBOARD_PATH="/home/jjoravet/alpaca-mcp-server-enhanced/interactive_dashboard.html"

echo -e "${YELLOW}📋 Step 1: Cleaning up previous instances...${NC}"

# Kill any existing MCP execution service instances
if pgrep -f "$SERVICE_NAME" > /dev/null; then
    echo "  → Stopping existing MCP execution service..."
    pkill -f "$SERVICE_NAME" 2>/dev/null || true
    sleep 2
fi

# Kill any process using port 8002
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "  → Clearing port $PORT..."
    fuser -k $PORT/tcp 2>/dev/null || true
    sleep 1
fi

# Also kill any other related services
pkill -f "start_web_service" 2>/dev/null || true
pkill -f "fastapi_service" 2>/dev/null || true

echo -e "${GREEN}  ✓ Cleanup complete${NC}"

echo -e "${YELLOW}📋 Step 2: Creating simplified backend service...${NC}"

# Create a working backend service with ALL tools
cat > /home/jjoravet/alpaca-mcp-server-enhanced/live_mcp_service.py << 'EOF'
#!/usr/bin/env python
"""Live MCP Execution Service - Fully connected to all MCP tools"""

import asyncio
import json
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import ALL MCP tool modules
from alpaca_mcp_server.tools import (
    account_tools,
    asset_tools,
    corporate_action_tools,
    day_trading_scanner,
    market_data_tools,
    market_info_tools,
    monitoring_tools,
    options_tools,
    order_tools,
    position_tools,
    streaming_tools,
    volume_bars_tool,
    watchlist_tools,
    cleanup_tool,
    after_hours_scanner,
    enhanced_market_clock,
    extended_hours_orders,
    single_day_pnl,
    help_tools,
    fastapi_monitoring_tools,
    c_stock_analyzer_wrapper,
    c_peak_trough_wrapper,
    peak_trough_analysis_tool,
    plot_py_tool,
    advanced_plotting_tool,
)

# Create FastAPI app
app = FastAPI(
    title="Live MCP Execution Service",
    description="Real-time execution of all MCP trading tools",
    version="1.0.0"
)

# Enable CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tool registry - map names to actual functions
TOOL_REGISTRY = {
    # Account & Portfolio Tools
    "get_account_info": account_tools.get_account_info,
    "get_positions": account_tools.get_positions,
    "get_open_position": account_tools.get_open_position,
    "close_position": position_tools.close_position,
    "close_all_positions": position_tools.close_all_positions,
    "check_positions_after_order": monitoring_tools.check_positions_after_order,
    
    # Market Data Tools
    "get_stock_quote": market_data_tools.get_stock_quote,
    "get_stock_bars": market_data_tools.get_stock_bars,
    "get_stock_bars_intraday": market_data_tools.get_stock_bars_intraday,
    "get_stock_latest_bar": market_data_tools.get_stock_latest_bar,
    "get_stock_latest_trade": market_data_tools.get_stock_latest_trade,
    "get_stock_trades": market_data_tools.get_stock_trades,
    "get_stock_snapshots": market_data_tools.get_stock_snapshots,
    
    # Scanning Tools
    "scan_day_trading_opportunities": day_trading_scanner.scan_day_trading_opportunities,
    "scan_explosive_momentum": day_trading_scanner.scan_explosive_momentum,
    "scan_after_hours_opportunities": after_hours_scanner.scan_after_hours_opportunities,
    
    # Technical Analysis Tools
    "get_stock_peak_trough_analysis": peak_trough_analysis_tool.analyze_peaks_and_troughs,
    "analyze_peaks_troughs_fast": c_peak_trough_wrapper.analyze_peaks_troughs_fast,
    "generate_stock_plot": plot_py_tool.generate_stock_plot,
    "generate_advanced_technical_plots": advanced_plotting_tool.generate_advanced_technical_plots,
    
    # Volume Bar Tools
    "get_volume_bars_from_history": volume_bars_tool.get_volume_bars_from_history,
    "compare_bar_types": volume_bars_tool.compare_bar_types,
    "start_volume_bar_streaming": volume_bars_tool.start_volume_bar_streaming,
    "get_volume_bar_stats": volume_bars_tool.get_volume_bar_stats,
    
    # Streaming Tools
    "start_global_stock_stream": streaming_tools.start_global_stock_stream,
    "stop_global_stock_stream": streaming_tools.stop_global_stock_stream,
    "add_symbols_to_stock_stream": streaming_tools.add_symbols_to_stock_stream,
    "get_stock_stream_data": streaming_tools.get_stock_stream_data,
    "list_active_stock_streams": streaming_tools.list_active_stock_streams,
    "get_stock_stream_buffer_stats": streaming_tools.get_stock_stream_buffer_stats,
    "clear_stock_stream_buffers": streaming_tools.clear_stock_stream_buffers,
    
    # Order Management Tools
    "place_stock_order": order_tools.place_stock_order,
    "place_extended_hours_order": extended_hours_orders.place_extended_hours_order,
    "get_orders": order_tools.get_orders,
    "cancel_order_by_id": order_tools.cancel_order_by_id,
    "cancel_all_orders": order_tools.cancel_all_orders,
    
    # Market Info Tools
    "get_market_clock": market_info_tools.get_market_clock,
    "get_extended_market_clock": enhanced_market_clock.get_extended_market_clock,
    "get_market_calendar": market_info_tools.get_market_calendar,
    
    # Asset & Watchlist Tools
    "get_all_assets": asset_tools.get_all_assets,
    "get_asset_info": asset_tools.get_asset_info,
    "create_watchlist": watchlist_tools.create_watchlist,
    "get_watchlists": watchlist_tools.get_watchlists,
    "update_watchlist": watchlist_tools.update_watchlist,
    
    # Options Tools
    "get_option_contracts": options_tools.get_option_contracts,
    "get_option_latest_quote": options_tools.get_option_latest_quote,
    "get_option_snapshot": options_tools.get_option_snapshot,
    "place_option_market_order": options_tools.place_option_market_order,
    
    # P&L Tools
    "get_single_day_pnl": single_day_pnl.get_single_day_pnl,
    
    # Help Tools
    "get_all_tools_help": help_tools.get_all_tools_help,
    "get_tool_help": help_tools.get_tool_help,
    
    # System Tools
    "cleanup": cleanup_tool.cleanup_server,
    "health_check": help_tools.health_check,
}

class ToolExecutionRequest(BaseModel):
    """Request model for tool execution"""
    parameters: Dict[str, Any] = {}

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return HTMLResponse(f"""
    <html>
        <head>
            <title>Live MCP Execution Service</title>
            <style>
                body {{ 
                    font-family: system-ui; 
                    background: linear-gradient(135deg, #0a0a0a, #1a1a2e);
                    color: #e0e0e0;
                    padding: 40px;
                }}
                h1 {{ color: #00ff88; }}
                .status {{ 
                    background: rgba(0,255,136,0.1);
                    border: 1px solid #00ff88;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                }}
                .tools-count {{
                    font-size: 2em;
                    color: #00ff88;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <h1>🚀 Live MCP Execution Service</h1>
            <div class="status">
                <p>✅ Service is running and ready</p>
                <p class="tools-count">{len(TOOL_REGISTRY)} Tools Available</p>
                <p>📊 Real-time connection to Alpaca Trading APIs</p>
                <p>🔌 WebSocket streaming enabled</p>
            </div>
            <p>Dashboard: <a href="file://{DASHBOARD_PATH}">Open Interactive Dashboard</a></p>
        </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tools_available": len(TOOL_REGISTRY)
    }

@app.get("/api/status")
async def get_status():
    """Get service status"""
    return {
        "status": "operational",
        "tools_count": len(TOOL_REGISTRY),
        "tools": list(TOOL_REGISTRY.keys()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/tools/list")
async def list_tools():
    """List all available tools"""
    tools = []
    for name, func in TOOL_REGISTRY.items():
        tools.append({
            "name": name,
            "description": func.__doc__ or "Trading tool",
            "schema": {}
        })
    return {"tools": tools, "count": len(tools)}

@app.post("/api/execute/tool/{tool_name}")
async def execute_tool(tool_name: str, request: ToolExecutionRequest):
    """Execute a specific tool"""
    if tool_name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    start_time = time.time()
    
    try:
        tool_func = TOOL_REGISTRY[tool_name]
        
        # Execute the tool
        if asyncio.iscoroutinefunction(tool_func):
            result = await tool_func(**request.parameters)
        else:
            result = tool_func(**request.parameters)
        
        execution_time = time.time() - start_time
        
        return {
            "success": True,
            "result": result,
            "error": None,
            "execution_time": execution_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "tool_name": tool_name,
                "parameters": request.parameters
            }
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Error executing {tool_name}: {str(e)}")
        
        return {
            "success": False,
            "result": None,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "tool_name": tool_name,
                "parameters": request.parameters,
                "traceback": traceback.format_exc()
            }
        }

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time streaming"""
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            
            if request.get("type") == "execute_tool":
                tool_name = request.get("tool_name")
                parameters = request.get("parameters", {})
                
                if tool_name in TOOL_REGISTRY:
                    try:
                        tool_func = TOOL_REGISTRY[tool_name]
                        if asyncio.iscoroutinefunction(tool_func):
                            result = await tool_func(**parameters)
                        else:
                            result = tool_func(**parameters)
                        
                        await websocket.send_json({
                            "type": "result",
                            "success": True,
                            "result": result,
                            "tool_name": tool_name
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "success": False,
                            "error": str(e),
                            "tool_name": tool_name
                        })
            
            elif request.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")

if __name__ == "__main__":
    logger.info(f"Starting Live MCP Execution Service on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
EOF

echo -e "${GREEN}  ✓ Backend service created${NC}"

echo -e "${YELLOW}📋 Step 3: Starting the MCP execution service...${NC}"

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the service
nohup uv run python /home/jjoravet/alpaca-mcp-server-enhanced/live_mcp_service.py > "$LOG_FILE" 2>&1 &
SERVICE_PID=$!

echo "  → Service started with PID: $SERVICE_PID"
echo "  → Waiting for service to be ready..."

# Wait for service to start (max 10 seconds)
COUNTER=0
while [ $COUNTER -lt 10 ]; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Service is running on port $PORT${NC}"
        break
    fi
    sleep 1
    COUNTER=$((COUNTER + 1))
    echo -n "."
done

if [ $COUNTER -eq 10 ]; then
    echo -e "${RED}  ✗ Service failed to start. Check logs at $LOG_FILE${NC}"
    tail -20 "$LOG_FILE"
    exit 1
fi

echo -e "${YELLOW}📋 Step 4: Verifying service health...${NC}"

# Test the service
HEALTH_CHECK=$(curl -s http://localhost:$PORT/health)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ Health check passed${NC}"
    echo "  → Response: $HEALTH_CHECK"
else
    echo -e "${RED}  ✗ Health check failed${NC}"
fi

# Get tool count
TOOLS_COUNT=$(curl -s http://localhost:$PORT/api/status | python3 -c "import sys, json; print(json.load(sys.stdin).get('tools_count', 0))" 2>/dev/null || echo "0")
echo -e "${BLUE}  ℹ Available tools: $TOOLS_COUNT${NC}"

echo -e "${YELLOW}📋 Step 5: Launching interactive dashboard...${NC}"

# Launch the dashboard in browser
if [ -f "$DASHBOARD_PATH" ]; then
    # Try different browsers
    if command -v chromium &> /dev/null; then
        chromium --new-window "file://$DASHBOARD_PATH" 2>/dev/null &
        echo -e "${GREEN}  ✓ Dashboard launched in Chromium${NC}"
    elif command -v google-chrome &> /dev/null; then
        google-chrome --new-window "file://$DASHBOARD_PATH" 2>/dev/null &
        echo -e "${GREEN}  ✓ Dashboard launched in Chrome${NC}"
    elif command -v firefox &> /dev/null; then
        firefox --new-window "file://$DASHBOARD_PATH" 2>/dev/null &
        echo -e "${GREEN}  ✓ Dashboard launched in Firefox${NC}"
    elif command -v xdg-open &> /dev/null; then
        xdg-open "file://$DASHBOARD_PATH" 2>/dev/null &
        echo -e "${GREEN}  ✓ Dashboard launched in default browser${NC}"
    else
        echo -e "${YELLOW}  ⚠ Could not auto-launch browser${NC}"
        echo "  → Please open manually: file://$DASHBOARD_PATH"
    fi
else
    echo -e "${RED}  ✗ Dashboard file not found at $DASHBOARD_PATH${NC}"
fi

echo ""
echo "========================================="
echo -e "${GREEN}🎉 Live MCP Trading Dashboard Ready!${NC}"
echo "========================================="
echo ""
echo "📊 Backend Service: http://localhost:$PORT"
echo "📁 Dashboard: file://$DASHBOARD_PATH"
echo "📝 Logs: $LOG_FILE"
echo ""
echo "Available endpoints:"
echo "  • http://localhost:$PORT/health - Health check"
echo "  • http://localhost:$PORT/api/status - Service status"
echo "  • http://localhost:$PORT/api/tools/list - List all tools"
echo "  • POST http://localhost:$PORT/api/execute/tool/{name} - Execute tool"
echo "  • WS ws://localhost:$PORT/ws/stream - WebSocket streaming"
echo ""
echo "To stop the service, run:"
echo "  pkill -f live_mcp_service"
echo ""
echo -e "${GREEN}✨ Happy Trading!${NC}"