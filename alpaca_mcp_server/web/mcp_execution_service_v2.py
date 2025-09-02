"""MCP Execution Service V2 - Direct integration with MCP server tools

This service provides REST API endpoints for executing all MCP tools, resources, and prompts
by directly using the MCP server's registered functions.
"""

import asyncio
import inspect
import json
import logging
import sys
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from rich.console import Console
from rich.logging import RichHandler

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the actual MCP server to get registered tools
from alpaca_mcp_server.server import get_server
from alpaca_mcp_server.server_components.tool_registrations import register_all_tools
from alpaca_mcp_server.server_components.resource_registrations import register_all_resources
from alpaca_mcp_server.server_components.prompt_registrations import register_all_prompts

# Import tool modules
from alpaca_mcp_server.tools import (
    account_tools, asset_tools, corporate_action_tools,
    day_trading_scanner, market_data_tools, market_info_tools,
    monitoring_tools, options_tools, order_tools, position_tools,
    streaming_tools, volume_bars_tool, watchlist_tools,
    cleanup_tool, after_hours_scanner, enhanced_market_clock,
    extended_hours_orders, single_day_pnl, help_tools
)

# Setup logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)

# Create global MCP server instance
mcp_server = None
tool_registry = {}
resource_registry = {}
prompt_registry = {}

class ToolExecutionRequest(BaseModel):
    """Request model for tool execution"""
    parameters: Dict[str, Any] = Field(default_factory=dict)

class PromptExecutionRequest(BaseModel):
    """Request model for prompt execution"""
    arguments: Dict[str, Any] = Field(default_factory=dict)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app"""
    global mcp_server, tool_registry, resource_registry, prompt_registry
    
    logger.info("🚀 Starting MCP Execution Service V2...")
    
    # Create MCP server instance
    mcp_server = get_server()
    
    # Extract tools from the server
    if hasattr(mcp_server, '_tool_manager') and hasattr(mcp_server._tool_manager, 'tools'):
        tools = mcp_server._tool_manager.tools
    else:
        # Fallback: get tools from the global help system
        from ..tools.help_tools import get_all_tools_help
        tools_help = get_all_tools_help()
        tools = {}
        # Parse the help text to extract tool names
        lines = tools_help.split('\n')
        for line in lines:
            if line.strip().startswith('• **'):
                tool_name = line.split('**')[1]
                tools[tool_name] = None
    
    logger.info(f"📦 Found {len(tools)} tools in MCP server")
    
    # Import all tool functions directly
    from ..tools import (
        account_tools, asset_tools, corporate_action_tools,
        day_trading_scanner, market_data_tools, market_info_tools,
        monitoring_tools, options_tools, order_tools, position_tools,
        streaming_tools, volume_bars_tool, watchlist_tools,
        cleanup_tool, after_hours_scanner, enhanced_market_clock,
        extended_hours_orders, single_day_pnl, help_tools
    )
    
    # Map tool names to actual functions
    tool_modules = {
        'account': account_tools,
        'asset': asset_tools,
        'corporate': corporate_action_tools,
        'scan': day_trading_scanner,
        'market': market_data_tools,
        'order': order_tools,
        'position': position_tools,
        'stream': streaming_tools,
        'volume': volume_bars_tool,
        'watchlist': watchlist_tools,
        'cleanup': cleanup_tool,
        'help': help_tools,
    }
    
    # Register all tools with their actual functions
    for tool_name in tools:
        # Find the module that contains this tool
        tool_func = None
        for prefix, module in tool_modules.items():
            if hasattr(module, tool_name):
                tool_func = getattr(module, tool_name)
                break
        
        if tool_func:
            tool_registry[tool_name] = {
                "function": tool_func,
                "description": tool_func.__doc__ or "No description",
                "schema": {}
            }
    
    # Extract resources from the server
    if hasattr(mcp_server, '_resource_manager') and hasattr(mcp_server._resource_manager, 'resources'):
        resources = mcp_server._resource_manager.resources
    else:
        resources = {}
    
    logger.info(f"📚 Found {len(resources)} resources in MCP server")
    for resource_uri, resource_func in resources.items():
        resource_registry[resource_uri] = {
            "function": resource_func,
            "description": resource_func.description if hasattr(resource_func, 'description') else "No description",
            "uri": resource_uri
        }
    
    # Extract prompts from the server
    if hasattr(mcp_server, '_prompt_manager') and hasattr(mcp_server._prompt_manager, 'prompts'):
        prompts = mcp_server._prompt_manager.prompts
    else:
        prompts = {}
    
    logger.info(f"🎯 Found {len(prompts)} prompts in MCP server")
    for prompt_name, prompt_func in prompts.items():
        prompt_registry[prompt_name] = {
            "function": prompt_func,
            "description": prompt_func.description if hasattr(prompt_func, 'description') else "No description",
            "arguments": prompt_func.arguments if hasattr(prompt_func, 'arguments') else []
        }
    
    logger.info(f"✅ MCP Execution Service V2 ready with {len(tool_registry)} tools, {len(resource_registry)} resources, {len(prompt_registry)} prompts")
    
    yield
    
    logger.info("🛑 Shutting down MCP Execution Service V2...")

# Create FastAPI app
app = FastAPI(
    title="MCP Execution Service V2",
    description="Live execution service for all MCP tools, resources, and prompts",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return HTMLResponse(content="""
    <html>
        <head>
            <title>MCP Execution Service V2</title>
            <style>
                body { 
                    font-family: 'Segoe UI', system-ui, sans-serif; 
                    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
                    color: #e0e0e0;
                    padding: 40px;
                    margin: 0;
                }
                h1 { 
                    color: #00ff88;
                    text-shadow: 0 0 20px rgba(0,255,136,0.5);
                }
                .stats {
                    display: flex;
                    gap: 30px;
                    margin: 30px 0;
                }
                .stat-card {
                    background: rgba(255,255,255,0.05);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 10px;
                    padding: 20px;
                    min-width: 150px;
                }
                .stat-number {
                    font-size: 2em;
                    font-weight: bold;
                    color: #00ff88;
                }
                a { color: #00aaff; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .endpoint {
                    background: rgba(0,170,255,0.1);
                    border-left: 3px solid #00aaff;
                    padding: 10px;
                    margin: 10px 0;
                    border-radius: 5px;
                }
                code {
                    background: rgba(0,0,0,0.3);
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Consolas', monospace;
                }
            </style>
        </head>
        <body>
            <h1>🚀 MCP Execution Service V2</h1>
            <p>Live execution service for all MCP trading tools, resources, and prompts</p>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">""" + str(len(tool_registry)) + """</div>
                    <div>Tools Available</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">""" + str(len(resource_registry)) + """</div>
                    <div>Resources Available</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">""" + str(len(prompt_registry)) + """</div>
                    <div>Prompts Available</div>
                </div>
            </div>
            
            <h2>📍 API Endpoints</h2>
            
            <div class="endpoint">
                <strong>GET</strong> <code>/api/tools/list</code> - List all available tools with schemas
            </div>
            
            <div class="endpoint">
                <strong>POST</strong> <code>/api/execute/tool/{tool_name}</code> - Execute a specific tool
            </div>
            
            <div class="endpoint">
                <strong>GET</strong> <code>/api/resources/list</code> - List all available resources
            </div>
            
            <div class="endpoint">
                <strong>GET</strong> <code>/api/execute/resource/{resource_uri}</code> - Get resource data
            </div>
            
            <div class="endpoint">
                <strong>GET</strong> <code>/api/prompts/list</code> - List all available prompts
            </div>
            
            <div class="endpoint">
                <strong>POST</strong> <code>/api/execute/prompt/{prompt_name}</code> - Execute a prompt
            </div>
            
            <div class="endpoint">
                <strong>WS</strong> <code>/ws/stream</code> - WebSocket for real-time streaming
            </div>
            
            <h2>📊 Interactive Dashboard</h2>
            <p>Open the <a href="file:///home/jjoravet/alpaca-mcp-server-enhanced/interactive_dashboard.html" target="_blank">Interactive Dashboard</a> to execute tools with a GUI</p>
            
            <h2>📚 Documentation</h2>
            <p>Visit <a href="/docs">/docs</a> for interactive API documentation</p>
        </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/status")
async def get_status():
    """Get service status and statistics"""
    return {
        "status": "operational",
        "tools_count": len(tool_registry),
        "resources_count": len(resource_registry),
        "prompts_count": len(prompt_registry),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/tools/list")
async def list_all_tools():
    """List all available tools with their schemas"""
    tools = []
    for name, info in tool_registry.items():
        tools.append({
            "name": name,
            "description": info["description"],
            "schema": info["schema"]
        })
    return {"tools": tools, "count": len(tools)}

@app.post("/api/execute/tool/{tool_name}")
async def execute_tool(tool_name: str, request: ToolExecutionRequest):
    """Execute a specific tool with provided parameters"""
    if tool_name not in tool_registry:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    start_time = time.time()
    
    try:
        tool_info = tool_registry[tool_name]
        tool_func = tool_info["function"]
        
        # Call the tool function with parameters
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
        logger.error(f"Error executing tool {tool_name}: {str(e)}")
        
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

@app.get("/api/resources/list")
async def list_all_resources():
    """List all available resources"""
    resources = []
    for uri, info in resource_registry.items():
        resources.append({
            "uri": uri,
            "description": info["description"]
        })
    return {"resources": resources, "count": len(resources)}

@app.get("/api/execute/resource/{resource_uri:path}")
async def execute_resource(resource_uri: str):
    """Get data from a specific resource"""
    if resource_uri not in resource_registry:
        # Try with :// format
        resource_uri_alt = resource_uri.replace("_", "://")
        if resource_uri_alt not in resource_registry:
            raise HTTPException(status_code=404, detail=f"Resource '{resource_uri}' not found")
        resource_uri = resource_uri_alt
    
    start_time = time.time()
    
    try:
        resource_info = resource_registry[resource_uri]
        resource_func = resource_info["function"]
        
        # Call the resource function
        if asyncio.iscoroutinefunction(resource_func.read):
            result = await resource_func.read()
        else:
            result = resource_func.read()
        
        execution_time = time.time() - start_time
        
        return {
            "success": True,
            "result": result.text if hasattr(result, 'text') else str(result),
            "error": None,
            "execution_time": execution_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "resource_uri": resource_uri
            }
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Error executing resource {resource_uri}: {str(e)}")
        
        return {
            "success": False,
            "result": None,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "resource_uri": resource_uri,
                "traceback": traceback.format_exc()
            }
        }

@app.get("/api/prompts/list")
async def list_all_prompts():
    """List all available prompts"""
    prompts = []
    for name, info in prompt_registry.items():
        prompts.append({
            "name": name,
            "description": info["description"],
            "arguments": [{"name": arg.name, "description": getattr(arg, 'description', ''), "required": getattr(arg, 'required', False)} for arg in info["arguments"]]
        })
    return {"prompts": prompts, "count": len(prompts)}

@app.post("/api/execute/prompt/{prompt_name}")
async def execute_prompt(prompt_name: str, request: PromptExecutionRequest):
    """Execute a specific prompt with provided arguments"""
    if prompt_name not in prompt_registry:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_name}' not found")
    
    start_time = time.time()
    
    try:
        prompt_info = prompt_registry[prompt_name]
        prompt_func = prompt_info["function"]
        
        # Call the prompt function with arguments
        if asyncio.iscoroutinefunction(prompt_func):
            result = await prompt_func(**request.arguments)
        else:
            result = prompt_func(**request.arguments)
        
        execution_time = time.time() - start_time
        
        return {
            "success": True,
            "result": result.messages[0].content if hasattr(result, 'messages') else str(result),
            "error": None,
            "execution_time": execution_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "prompt_name": prompt_name,
                "arguments": request.arguments
            }
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Error executing prompt {prompt_name}: {str(e)}")
        
        return {
            "success": False,
            "result": None,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "prompt_name": prompt_name,
                "arguments": request.arguments,
                "traceback": traceback.format_exc()
            }
        }

# WebSocket endpoint for streaming
@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time streaming"""
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            request = json.loads(data)
            
            # Process the request
            if request.get("type") == "execute_tool":
                tool_name = request.get("tool_name")
                parameters = request.get("parameters", {})
                
                if tool_name in tool_registry:
                    try:
                        tool_func = tool_registry[tool_name]["function"]
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
                else:
                    await websocket.send_json({
                        "type": "error",
                        "success": False,
                        "error": f"Tool '{tool_name}' not found"
                    })
            
            elif request.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()

def main():
    """Main entry point"""
    uvicorn.run(
        "alpaca_mcp_server.web.mcp_execution_service_v2:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()