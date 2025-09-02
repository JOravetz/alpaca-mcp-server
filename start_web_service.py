#!/usr/bin/env python
"""Simple web service to execute MCP tools via HTTP"""

import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import all the actual MCP tools
from alpaca_mcp_server.tools.help_tools import get_all_tools_help
from alpaca_mcp_server.tools.market_data_tools import get_stock_quote, get_stock_bars
from alpaca_mcp_server.tools.account_tools import get_account_info, get_positions
from alpaca_mcp_server.tools.day_trading_scanner import scan_day_trading_opportunities

app = FastAPI(title="MCP Live Execution Service")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExecuteRequest(BaseModel):
    tool_name: str
    parameters: dict = {}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/tools/list")
async def list_tools():
    """List available tools"""
    return {
        "tools": [
            {"name": "get_stock_quote", "description": "Get stock quote"},
            {"name": "get_stock_bars", "description": "Get historical bars"},
            {"name": "get_account_info", "description": "Get account info"},
            {"name": "get_positions", "description": "Get positions"},
            {"name": "scan_day_trading_opportunities", "description": "Scan for opportunities"},
            {"name": "get_all_tools_help", "description": "Get help for all tools"}
        ]
    }

@app.post("/api/execute")
async def execute_tool(request: ExecuteRequest):
    """Execute a tool with parameters"""
    
    # Map of tool names to functions
    tools = {
        "get_stock_quote": get_stock_quote,
        "get_stock_bars": get_stock_bars,
        "get_account_info": get_account_info,
        "get_positions": get_positions,
        "scan_day_trading_opportunities": scan_day_trading_opportunities,
        "get_all_tools_help": get_all_tools_help,
    }
    
    if request.tool_name not in tools:
        raise HTTPException(status_code=404, detail=f"Tool {request.tool_name} not found")
    
    try:
        tool_func = tools[request.tool_name]
        
        # Execute the tool
        if asyncio.iscoroutinefunction(tool_func):
            result = await tool_func(**request.parameters)
        else:
            result = tool_func(**request.parameters)
        
        return {
            "success": True,
            "result": result,
            "tool": request.tool_name,
            "parameters": request.parameters
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tool": request.tool_name,
            "parameters": request.parameters
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
