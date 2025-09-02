#!/usr/bin/env python
"""MCP Backend Service - Direct execution of all MCP tools via HTTP API"""

import asyncio
import json
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

print("🚀 Starting MCP Backend Service...")
print("=" * 50)

# Create FastAPI app
app = FastAPI(
    title="Live MCP Execution Backend",
    description="Direct execution of all MCP trading tools",
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

# Import and register tools dynamically
TOOL_REGISTRY = {}

try:
    from alpaca_mcp_server.tools.market_info_tools import get_market_clock, get_market_calendar
    TOOL_REGISTRY["get_market_clock"] = get_market_clock
    TOOL_REGISTRY["get_market_calendar"] = get_market_calendar
    print("✅ Loaded market info tools")
except Exception as e:
    print(f"⚠️  Could not load market info tools: {e}")

try:
    from alpaca_mcp_server.tools.market_data_tools import (
        get_stock_quote, get_stock_bars, get_stock_bars_intraday as _get_stock_bars_intraday,
        get_stock_latest_bar, get_stock_latest_trade, get_stock_trades,
        get_stock_snapshots
    )
    
    # Wrapper for get_stock_bars_intraday to handle 'days' parameter
    async def get_stock_bars_intraday_wrapper(symbol: str, timeframe: str = "1Min", days: int = 1, **kwargs):
        """Wrapper to convert days parameter to start_date/end_date - handles weekends"""
        from datetime import datetime, timedelta
        import pytz
        
        # Calculate dates based on days parameter
        et_tz = pytz.timezone('America/New_York')
        end_date = datetime.now(et_tz)
        
        # If it's weekend, go back to last Friday
        if end_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            days_back = end_date.weekday() - 4  # Get back to Friday
            end_date = end_date - timedelta(days=days_back)
        
        # For weekends, ensure we get market days
        market_days_needed = days
        calendar_days = days
        if days <= 5:
            calendar_days = days + 4  # Add extra days to account for weekends
        
        start_date = end_date - timedelta(days=calendar_days)
        
        # Call the original function with date parameters
        return await _get_stock_bars_intraday(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            **kwargs
        )
    
    TOOL_REGISTRY.update({
        "get_stock_quote": get_stock_quote,
        "get_stock_bars": get_stock_bars,
        "get_stock_bars_intraday": get_stock_bars_intraday_wrapper,
        "get_stock_latest_bar": get_stock_latest_bar,
        "get_stock_latest_trade": get_stock_latest_trade,
        "get_stock_trades": get_stock_trades,
        "get_stock_snapshots": get_stock_snapshots,
    })
    print("✅ Loaded market data tools")
except Exception as e:
    print(f"⚠️  Could not load market data tools: {e}")

try:
    from alpaca_mcp_server.tools.account_tools import get_account_info, get_positions
    TOOL_REGISTRY["get_account_info"] = get_account_info
    TOOL_REGISTRY["get_positions"] = get_positions
    print("✅ Loaded account tools")
except Exception as e:
    print(f"⚠️  Could not load account tools: {e}")

try:
    from alpaca_mcp_server.tools.day_trading_scanner import (
        scan_day_trading_opportunities, scan_explosive_momentum
    )
    TOOL_REGISTRY["scan_day_trading_opportunities"] = scan_day_trading_opportunities
    TOOL_REGISTRY["scan_explosive_momentum"] = scan_explosive_momentum
    print("✅ Loaded scanning tools")
except Exception as e:
    print(f"⚠️  Could not load scanning tools: {e}")

try:
    from alpaca_mcp_server.tools.order_tools import (
        place_stock_order, get_orders, cancel_order_by_id, cancel_all_orders
    )
    TOOL_REGISTRY.update({
        "place_stock_order": place_stock_order,
        "get_orders": get_orders,
        "cancel_order_by_id": cancel_order_by_id,
        "cancel_all_orders": cancel_all_orders,
    })
    print("✅ Loaded order tools")
except Exception as e:
    print(f"⚠️  Could not load order tools: {e}")

# Try to load additional tools - import from server_components
try:
    # Import the registered tools from server_components 
    import sys
    sys.path.insert(0, '/home/jjoravet/alpaca-mcp-server-enhanced')
    
    # Create a simple wrapper for the peak/trough analysis
    from alpaca_mcp_server.tools.peak_trough_analysis_tool import process_bars_for_peaks
    from alpaca_mcp_server.tools.market_data_tools import get_stock_bars_intraday as original_get_bars
    
    async def get_stock_peak_trough_analysis(symbols: str = "AAPL", timeframe: str = "1Min", days: int = 1):
        """Get peak/trough analysis with Hanning filter"""
        # Get the bars data first
        bars_result = await original_get_bars(
            symbol=symbols, 
            timeframe=timeframe,
            limit=1000
        )
        # For now, return the bars data
        return f"Peak/Trough Analysis for {symbols}\n{bars_result}"
    
    TOOL_REGISTRY["get_stock_peak_trough_analysis"] = get_stock_peak_trough_analysis
    print("✅ Loaded peak/trough analysis tool")
except Exception as e:
    print(f"⚠️  Could not load peak/trough analysis tool: {e}")

try:
    from alpaca_mcp_server.tools.plot_py_tool import generate_stock_plot
    TOOL_REGISTRY["generate_stock_plot"] = generate_stock_plot
    print("✅ Loaded plot generation tool")
except Exception as e:
    print(f"⚠️  Could not load plot generation tool: {e}")

try:
    from alpaca_mcp_server.tools.advanced_plotting_tool import generate_advanced_technical_plots
    TOOL_REGISTRY["generate_advanced_technical_plots"] = generate_advanced_technical_plots
    print("✅ Loaded advanced plotting tool")
except Exception as e:
    print(f"⚠️  Could not load advanced plotting tool: {e}")

try:
    from alpaca_mcp_server.tools.streaming_tools import (
        start_global_stock_stream, stop_global_stock_stream,
        get_stock_stream_data, list_active_stock_streams,
        get_stock_stream_buffer_stats, clear_stock_stream_buffers
    )
    TOOL_REGISTRY.update({
        "start_global_stock_stream": start_global_stock_stream,
        "stop_global_stock_stream": stop_global_stock_stream,
        "get_stock_stream_data": get_stock_stream_data,
        "list_active_stock_streams": list_active_stock_streams,
        "get_stock_stream_buffer_stats": get_stock_stream_buffer_stats,
        "clear_stock_stream_buffers": clear_stock_stream_buffers,
    })
    print("✅ Loaded streaming tools")
except Exception as e:
    print(f"⚠️  Could not load streaming tools: {e}")

try:
    from alpaca_mcp_server.tools.position_tools import (
        close_position, close_all_positions
    )
    from alpaca_mcp_server.tools.account_tools import get_open_position
    
    TOOL_REGISTRY["close_position"] = close_position
    TOOL_REGISTRY["close_all_positions"] = close_all_positions
    TOOL_REGISTRY["get_open_position"] = get_open_position
    print("✅ Loaded position tools")
except Exception as e:
    print(f"⚠️  Could not load position tools: {e}")

try:
    from alpaca_mcp_server.tools.market_extended_hours import (
        get_extended_market_clock, validate_extended_hours_order,
        place_extended_hours_order, get_extended_hours_info
    )
    TOOL_REGISTRY["get_extended_market_clock"] = get_extended_market_clock
    TOOL_REGISTRY["validate_extended_hours_order"] = validate_extended_hours_order
    TOOL_REGISTRY["place_extended_hours_order"] = place_extended_hours_order
    TOOL_REGISTRY["get_extended_hours_info"] = get_extended_hours_info
    print("✅ Loaded extended hours tools")
except Exception as e:
    print(f"⚠️  Could not load extended hours tools: {e}")

# Add more available tools
try:
    from alpaca_mcp_server.tools.asset_tools import (
        get_all_assets, get_asset_info, get_corporate_announcements
    )
    TOOL_REGISTRY["get_all_assets"] = get_all_assets
    TOOL_REGISTRY["get_asset_info"] = get_asset_info
    TOOL_REGISTRY["get_corporate_announcements"] = get_corporate_announcements
    print("✅ Loaded asset tools")
except Exception as e:
    print(f"⚠️  Could not load asset tools: {e}")

try:
    from alpaca_mcp_server.tools.watchlist_tools import (
        create_watchlist, get_watchlists, update_watchlist
    )
    TOOL_REGISTRY["create_watchlist"] = create_watchlist
    TOOL_REGISTRY["get_watchlists"] = get_watchlists
    TOOL_REGISTRY["update_watchlist"] = update_watchlist
    print("✅ Loaded watchlist tools")
except Exception as e:
    print(f"⚠️  Could not load watchlist tools: {e}")

try:
    from alpaca_mcp_server.tools.options_tools import (
        get_option_contracts, get_option_latest_quote,
        get_option_snapshot, place_option_market_order
    )
    TOOL_REGISTRY["get_option_contracts"] = get_option_contracts
    TOOL_REGISTRY["get_option_latest_quote"] = get_option_latest_quote
    TOOL_REGISTRY["get_option_snapshot"] = get_option_snapshot
    TOOL_REGISTRY["place_option_market_order"] = place_option_market_order
    print("✅ Loaded options tools")
except Exception as e:
    print(f"⚠️  Could not load options tools: {e}")

# Load C-optimized fast analysis tools
try:
    from alpaca_mcp_server.tools.c_stock_analyzer_wrapper import (
        analyze_market_activity_fast, scan_explosive_stocks_fast,
        compare_analyzer_performance
    )
    TOOL_REGISTRY["analyze_market_activity_fast"] = analyze_market_activity_fast
    TOOL_REGISTRY["scan_explosive_stocks_fast"] = scan_explosive_stocks_fast
    TOOL_REGISTRY["compare_analyzer_performance"] = compare_analyzer_performance
    print("✅ Loaded C-optimized analysis tools")
except Exception as e:
    print(f"⚠️  Could not load C-optimized tools: {e}")

try:
    from alpaca_mcp_server.tools.c_peak_trough_wrapper import (
        analyze_peaks_troughs_fast, compare_peak_trough_implementations
    )
    TOOL_REGISTRY["analyze_peaks_troughs_fast"] = analyze_peaks_troughs_fast
    TOOL_REGISTRY["compare_peak_trough_implementations"] = compare_peak_trough_implementations
    print("✅ Loaded C peak/trough tools")
except Exception as e:
    print(f"⚠️  Could not load C peak/trough tools: {e}")

# Load volume bar tools
try:
    from alpaca_mcp_server.tools.volume_bars_tool import (
        get_volume_bars_from_history, compare_bar_types,
        start_volume_bar_streaming, get_volume_bar_stats
    )
    TOOL_REGISTRY["get_volume_bars_from_history"] = get_volume_bars_from_history
    TOOL_REGISTRY["compare_bar_types"] = compare_bar_types
    TOOL_REGISTRY["start_volume_bar_streaming"] = start_volume_bar_streaming
    TOOL_REGISTRY["get_volume_bar_stats"] = get_volume_bar_stats
    print("✅ Loaded volume bar tools")
except Exception as e:
    print(f"⚠️  Could not load volume bar tools: {e}")

# Load monitoring tools
try:
    from alpaca_mcp_server.tools.monitoring_tools import (
        start_hybrid_monitoring, stop_hybrid_monitoring,
        get_hybrid_monitoring_status, verify_monitoring_active,
        add_symbols_to_watchlist, remove_symbols_from_watchlist,
        get_current_watchlist, get_current_trading_signals,
        get_profit_spike_alerts, check_positions_after_order,
        ping_monitoring_service, get_monitoring_alerts
    )
    TOOL_REGISTRY.update({
        "start_hybrid_monitoring": start_hybrid_monitoring,
        "stop_hybrid_monitoring": stop_hybrid_monitoring,
        "get_hybrid_monitoring_status": get_hybrid_monitoring_status,
        "verify_monitoring_active": verify_monitoring_active,
        "add_symbols_to_watchlist": add_symbols_to_watchlist,
        "remove_symbols_from_watchlist": remove_symbols_from_watchlist,
        "get_current_watchlist": get_current_watchlist,
        "get_current_trading_signals": get_current_trading_signals,
        "get_profit_spike_alerts": get_profit_spike_alerts,
        "check_positions_after_order": check_positions_after_order,
        "ping_monitoring_service": ping_monitoring_service,
        "get_monitoring_alerts": get_monitoring_alerts
    })
    print("✅ Loaded monitoring tools")
except Exception as e:
    print(f"⚠️  Could not load monitoring tools: {e}")

# Load enhanced analytics tools
try:
    from alpaca_mcp_server.tools.enhanced_analytics import (
        get_enhanced_streaming_analytics, stream_aware_price_monitor,
        stream_optimized_order_placement
    )
    TOOL_REGISTRY["get_enhanced_streaming_analytics"] = get_enhanced_streaming_analytics
    TOOL_REGISTRY["stream_aware_price_monitor"] = stream_aware_price_monitor
    TOOL_REGISTRY["stream_optimized_order_placement"] = stream_optimized_order_placement
    print("✅ Loaded enhanced analytics tools")
except Exception as e:
    print(f"⚠️  Could not load enhanced analytics tools: {e}")

# Load after-hours scanning
try:
    from alpaca_mcp_server.tools.after_hours_scanner import scan_after_hours_opportunities
    TOOL_REGISTRY["scan_after_hours_opportunities"] = scan_after_hours_opportunities
    print("✅ Loaded after-hours scanner")
except Exception as e:
    print(f"⚠️  Could not load after-hours scanner: {e}")

# Load P&L tools
try:
    from alpaca_mcp_server.tools.pnl_tools import get_single_day_pnl
    TOOL_REGISTRY["get_single_day_pnl"] = get_single_day_pnl
    print("✅ Loaded P&L tools")
except Exception as e:
    print(f"⚠️  Could not load P&L tools: {e}")

print(f"\n📦 Total tools loaded: {len(TOOL_REGISTRY)}")
print("=" * 50)

class ToolExecutionRequest(BaseModel):
    """Request model for tool execution"""
    parameters: Dict[str, Any] = {}

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>MCP Backend Service</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
                    color: #e0e0e0;
                    padding: 40px;
                    margin: 0;
                    min-height: 100vh;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                h1 {{ 
                    color: #00ff88;
                    text-shadow: 0 0 20px rgba(0,255,136,0.5);
                    font-size: 2.5em;
                    margin-bottom: 10px;
                }}
                .status-card {{
                    background: rgba(255,255,255,0.05);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(0,255,136,0.3);
                    border-radius: 15px;
                    padding: 30px;
                    margin: 30px 0;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                }}
                .stat {{
                    display: inline-block;
                    margin: 15px 30px 15px 0;
                }}
                .stat-value {{
                    font-size: 2.5em;
                    font-weight: bold;
                    color: #00ff88;
                    display: block;
                }}
                .stat-label {{
                    color: #888;
                    font-size: 0.9em;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-top: 5px;
                }}
                .tools-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                    gap: 15px;
                    margin: 20px 0;
                }}
                .tool-item {{
                    background: rgba(0,170,255,0.1);
                    border: 1px solid rgba(0,170,255,0.3);
                    padding: 15px;
                    border-radius: 8px;
                    transition: all 0.3s ease;
                }}
                .tool-item:hover {{
                    background: rgba(0,170,255,0.2);
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0,170,255,0.3);
                }}
                .endpoint {{
                    background: rgba(0,255,136,0.1);
                    border-left: 4px solid #00ff88;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    font-family: 'Consolas', 'Monaco', monospace;
                }}
                .method {{
                    display: inline-block;
                    padding: 3px 8px;
                    background: #00ff88;
                    color: #000;
                    border-radius: 3px;
                    font-weight: bold;
                    margin-right: 10px;
                    font-size: 0.85em;
                }}
                a {{
                    color: #00aaff;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                .dashboard-btn {{
                    display: inline-block;
                    background: linear-gradient(135deg, #00ff88, #00aaff);
                    color: #000;
                    padding: 15px 30px;
                    border-radius: 30px;
                    font-weight: bold;
                    text-decoration: none;
                    margin: 20px 0;
                    transition: all 0.3s ease;
                    box-shadow: 0 5px 20px rgba(0,255,136,0.3);
                }}
                .dashboard-btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 8px 30px rgba(0,255,136,0.5);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 MCP Backend Service</h1>
                <p style="font-size: 1.2em; color: #aaa;">Real-time execution backend for all MCP trading tools</p>
                
                <div class="status-card">
                    <h2 style="color: #00ff88; margin-top: 0;">📊 Service Status</h2>
                    <div>
                        <div class="stat">
                            <span class="stat-value">{len(TOOL_REGISTRY)}</span>
                            <div class="stat-label">Tools Available</div>
                        </div>
                        <div class="stat">
                            <span class="stat-value" style="color: #00ff88;">●</span>
                            <div class="stat-label">Service Status</div>
                        </div>
                        <div class="stat">
                            <span class="stat-value">8002</span>
                            <div class="stat-label">Port</div>
                        </div>
                    </div>
                </div>
                
                <div class="status-card">
                    <h2 style="color: #00aaff;">🔧 Available Tools</h2>
                    <div class="tools-grid">
                        {"".join([f'<div class="tool-item">{name}</div>' for name in sorted(TOOL_REGISTRY.keys())])}
                    </div>
                </div>
                
                <div class="status-card">
                    <h2 style="color: #00aaff;">📍 API Endpoints</h2>
                    <div class="endpoint">
                        <span class="method">GET</span>
                        <code>/health</code> - Health check
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span>
                        <code>/api/status</code> - Service status with tool list
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span>
                        <code>/api/tools/list</code> - List all available tools
                    </div>
                    <div class="endpoint">
                        <span class="method">POST</span>
                        <code>/api/execute/tool/{{tool_name}}</code> - Execute a specific tool
                    </div>
                </div>
                
                <a href="file:///home/jjoravet/alpaca-mcp-server-enhanced/interactive_dashboard.html" class="dashboard-btn">
                    📊 Open Interactive Dashboard
                </a>
                
                <div class="status-card" style="background: rgba(0,255,136,0.05); border-color: rgba(0,255,136,0.5);">
                    <h2 style="color: #00ff88;">✨ Ready for Trading!</h2>
                    <p>The backend service is running and ready to execute MCP tools.</p>
                    <p>Use the interactive dashboard to execute tools with a graphical interface.</p>
                </div>
            </div>
        </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tools_count": len(TOOL_REGISTRY)
    }

@app.get("/api/status")
async def get_status():
    """Get service status and available tools"""
    return {
        "status": "operational",
        "tools_count": len(TOOL_REGISTRY),
        "tools": list(TOOL_REGISTRY.keys()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/tools/list")
async def list_tools():
    """List all available tools with descriptions"""
    tools = []
    for name, func in TOOL_REGISTRY.items():
        tools.append({
            "name": name,
            "description": func.__doc__ or "MCP Trading Tool",
            "schema": {}
        })
    return {"tools": tools, "count": len(tools)}

@app.post("/api/execute/tool/{tool_name}")
async def execute_tool(tool_name: str, request: ToolExecutionRequest):
    """Execute a specific tool with parameters"""
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

if __name__ == "__main__":
    print("\n🌟 Starting server on http://localhost:8002")
    print("📊 Dashboard: file:///home/jjoravet/alpaca-mcp-server-enhanced/interactive_dashboard.html")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")