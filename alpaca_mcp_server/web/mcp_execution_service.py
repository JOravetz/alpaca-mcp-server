"""Comprehensive FastAPI MCP Execution Service

This service provides REST API endpoints for executing all MCP tools, resources, and prompts
with live connections to the actual MCP server implementation. It runs on port 8002 and provides
both REST and WebSocket interfaces for real-time execution and streaming results.

Features:
- Execute all 101+ MCP tools with parameter validation
- Access all 16+ MCP resources
- Run all 14+ MCP prompts with arguments
- Real-time execution using actual MCP server functions
- WebSocket support for streaming results
- Comprehensive error handling and result formatting
- Performance metrics and analysis
- CORS enabled for browser access
"""

import inspect
import json
import logging
import sys
import time
import traceback
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Import prompt modules
from ..prompts import (
    account_analysis_prompt,
    day_trading_workflow,
    list_trading_capabilities,
    market_analysis_prompt,
    market_session_workflow,
    master_scanning_workflow,
    options_strategy_prompt,
    order_strategy_prompt,
    portfolio_review_prompt,
    position_management_prompt,
    pro_technical_workflow,
    risk_management_prompt,
    startup_prompt,
    stock_news_prompt,
    stream_centric_trading_prompt,
    tools_reference_prompt,
)

# Import resource modules
from ..resources import (
    account_resources,
    api_monitor,
    data_quality,
    help_system,
    intraday_pnl,
    market_momentum,
    market_resources,
    portfolio_resources,
    position_resources,
    server_health,
    session_status,
    streaming_resources,
)

# Import MCP server components
from ..server import get_server

# Import all tool modules for direct execution
from ..tools import (
    account_tools,
    advanced_plotting_tool,
    after_hours_scanner,
    asset_tools,
    c_peak_trough_wrapper,
    c_stock_analyzer_wrapper,
    cleanup_tool,
    corporate_action_tools,
    day_trading_scanner,
    enhanced_market_clock,
    extended_hours_orders,
    fastapi_monitoring_tools,
    market_data_tools,
    market_info_tools,
    monitoring_tools,
    options_tools,
    order_tools,
    peak_trough_analysis_tool,
    plot_py_tool,
    position_tools,
    single_day_pnl,
    streaming_tools,
    volume_bars_tool,
    watchlist_tools,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state for active connections and MCP server
active_connections: list[WebSocket] = []
mcp_server = None


# Request/Response Models
class ToolExecutionRequest(BaseModel):
    parameters: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class ResourceRequest(BaseModel):
    parameters: dict[str, Any] = Field(default_factory=dict, description="Resource parameters")


class PromptExecutionRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict, description="Prompt arguments")


class ExecutionResponse(BaseModel):
    success: bool
    result: Any = None
    error: str | None = None
    execution_time: float
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]
    module: str
    function_name: str


class ResourceSchema(BaseModel):
    uri: str
    name: str
    description: str
    parameters: dict[str, Any]
    module: str
    function_name: str


class PromptSchema(BaseModel):
    name: str
    description: str
    arguments: dict[str, Any]
    module: str
    function_name: str


class ServiceStatus(BaseModel):
    status: str
    uptime: float
    total_executions: int
    active_connections: int
    server_info: dict[str, Any]
    timestamp: str


@asynccontextmanager  # type: ignore[arg-type]
async def lifespan(app: FastAPI) -> None:  # type: ignore[misc]
    """Manage application lifecycle - startup and shutdown."""
    global mcp_server

    # Startup
    logger.info("🚀 Starting MCP Execution Service...")
    try:
        # Get the MCP server instance
        mcp_server = get_server()
        logger.info("✅ MCP server initialized successfully")

        # Initialize help system if needed
        try:
            help_system.initialize_help_system(mcp_server)
            logger.info("✅ Help system initialized")
        except Exception as e:
            logger.warning(f"Help system initialization failed: {e}")

        app.state.start_time = time.time()
        app.state.execution_count = 0

        logger.info("🌟 MCP Execution Service ready on port 8002")

    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP server: {e}")
        logger.error(traceback.format_exc())

    yield

    # Shutdown
    logger.info("🛑 Shutting down MCP Execution Service...")
    # Close WebSocket connections
    for connection in active_connections[:]:
        with suppress(Exception):
            await connection.close()
    active_connections.clear()


# Create FastAPI app
app = FastAPI(
    title="MCP Execution Service",
    description="REST API for executing MCP tools, resources, and prompts",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def get_function_signature(func) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """Extract function signature and parameter information."""
    try:
        sig = inspect.signature(func)
        parameters = {}

        for name, param in sig.parameters.items():
            param_info = {
                "name": name,
                "required": param.default == inspect.Parameter.empty,
                "type": (
                    str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                ),
            }

            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default

            parameters[name] = param_info

        return {
            "parameters": parameters,
            "return_type": (
                str(sig.return_annotation)
                if sig.return_annotation != inspect.Parameter.empty
                else "Any"
            ),
        }
    except Exception as e:
        logger.warning(f"Could not extract signature for {func.__name__}: {e}")
        return {"parameters": {}, "return_type": "Any"}


async def execute_function_safely(func, **kwargs) -> ExecutionResponse:  # type: ignore[no-untyped-def]
    """Execute a function with error handling and performance monitoring."""
    start_time = time.time()

    try:
        # Filter kwargs to only include parameters the function accepts
        sig = inspect.signature(func)
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}

        # Execute function (handle both sync and async)
        if inspect.iscoroutinefunction(func):
            result = await func(**filtered_kwargs)
        else:
            result = func(**filtered_kwargs)

        execution_time = time.time() - start_time

        # Increment execution counter
        if hasattr(app.state, "execution_count"):
            app.state.execution_count += 1

        return ExecutionResponse(
            success=True,
            result=result,
            execution_time=execution_time,
            timestamp=datetime.now(UTC).isoformat(),
            metadata={
                "function_name": func.__name__,
                "module": func.__module__,
                "filtered_parameters": filtered_kwargs,
                "parameter_count": len(filtered_kwargs),
            },
        )

    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = str(e)

        logger.error(f"Function execution failed: {func.__name__}")
        logger.error(f"Error: {error_msg}")
        logger.error(f"Parameters: {kwargs}")
        logger.error(traceback.format_exc())

        return ExecutionResponse(
            success=False,
            error=error_msg,
            execution_time=execution_time,
            timestamp=datetime.now(UTC).isoformat(),
            metadata={
                "function_name": func.__name__,
                "module": func.__module__,
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
            },
        )


# =============================================================================
# DISCOVERY ENDPOINTS
# =============================================================================


@app.get("/api/tools/list", response_model=list[ToolSchema])
async def list_all_tools() -> list[ToolSchema]:
    """List all available MCP tools with their schemas."""
    tools = []

    # Tool definitions with their corresponding functions
    tool_definitions = {
        # Account Tools
        "get_account_info": (
            account_tools.get_account_info,
            "Get current account information including balances and status",
        ),
        "get_positions": (
            account_tools.get_positions,
            "Get all current positions in the portfolio",
        ),
        "get_open_position": (
            account_tools.get_open_position,
            "Get details for a specific open position",
        ),
        # Position Tools
        "close_position": (position_tools.close_position, "Close a specific position"),
        "close_all_positions": (position_tools.close_all_positions, "Close all open positions"),
        # Market Data Tools
        "get_stock_quote": (market_data_tools.get_stock_quote, "Get latest quote for a stock"),
        "get_stock_snapshots": (
            market_data_tools.get_stock_snapshots,
            "Get comprehensive market snapshots",
        ),
        "get_stock_bars": (market_data_tools.get_stock_bars, "Get historical price bars"),
        "get_stock_bars_intraday": (
            market_data_tools.get_stock_bars_intraday,
            "Get intraday historical bars with analysis",
        ),
        "get_stock_trades": (market_data_tools.get_stock_trades, "Get recent trades for a stock"),
        "get_stock_latest_trade": (
            market_data_tools.get_stock_latest_trade,
            "Get the latest trade for a stock",
        ),
        "get_stock_latest_bar": (
            market_data_tools.get_stock_latest_bar,
            "Get the latest minute bar for a stock",
        ),
        # Market Info Tools
        "get_market_clock": (
            market_info_tools.get_market_clock,
            "Get current market status and next open/close times",
        ),
        "get_market_calendar": (
            market_info_tools.get_market_calendar,
            "Get market calendar for specified date range",
        ),
        # Options Tools
        "get_option_contracts": (
            options_tools.get_option_contracts,
            "Get option contracts for underlying symbol",
        ),
        "get_option_latest_quote": (
            options_tools.get_option_latest_quote,
            "Get latest quote for an option contract",
        ),
        "get_option_snapshot": (
            options_tools.get_option_snapshot,
            "Get comprehensive option snapshot with Greeks",
        ),
        # Technical Analysis Tools
        "get_stock_peak_trough_analysis": (
            peak_trough_analysis_tool.analyze_peaks_and_troughs,
            "Get stock peak and trough analysis for day trading signals",
        ),
        "analyze_peaks_troughs_fast": (
            c_peak_trough_wrapper.analyze_peaks_troughs_fast,
            "Ultra-fast peak/trough analysis using C implementation",
        ),
        "compare_peak_trough_implementations": (
            c_peak_trough_wrapper.compare_implementations,
            "Compare performance between C and Python implementations",
        ),
        # Volume Bar Tools
        "get_volume_bars_from_history": (
            volume_bars_tool.get_volume_bars_from_history,
            "Generate volume bars from historical data",
        ),
        "compare_bar_types": (
            volume_bars_tool.compare_bar_types,
            "Compare statistical properties of time bars vs volume bars",
        ),
        "start_volume_bar_streaming": (
            volume_bars_tool.start_volume_bar_streaming,
            "Start real-time volume bar aggregation",
        ),
        "get_volume_bar_stats": (
            volume_bars_tool.get_volume_bar_stats,
            "Get current volume bar statistics and recent bars",
        ),
        # Day Trading Scanner Tools
        "scan_day_trading_opportunities": (
            day_trading_scanner.scan_day_trading_opportunities,
            "Scan for explosive day-trading opportunities",
        ),
        "scan_explosive_momentum": (
            day_trading_scanner.scan_explosive_momentum,
            "Quick scanner for explosive momentum moves",
        ),
        "scan_after_hours_opportunities": (
            after_hours_scanner.scan_after_hours_opportunities,
            "Scan for after-hours trading opportunities",
        ),
        "analyze_market_activity_fast": (
            c_stock_analyzer_wrapper.analyze_market_activity_fast,
            "Ultra-fast market activity analysis using C implementation",
        ),
        "scan_explosive_stocks_fast": (
            c_stock_analyzer_wrapper.scan_explosive_stocks_fast,
            "Lightning-fast scan for explosive penny stocks",
        ),
        "compare_analyzer_performance": (
            c_stock_analyzer_wrapper.compare_analyzer_performance,
            "Compare performance between C and Python analyzers",
        ),
        # Streaming Analytics
        "get_enhanced_streaming_analytics": (
            streaming_tools.get_enhanced_streaming_analytics,  # type: ignore[attr-defined]
            "Enhanced streaming analytics with real-time calculations",
        ),
        # P&L Analysis
        "get_single_day_pnl": (
            single_day_pnl.get_single_day_pnl,
            "Calculate P&L for a single specific trading day only",
        ),
        # Watchlist Tools
        "create_watchlist": (
            watchlist_tools.create_watchlist,
            "Create a new watchlist with specified symbols",
        ),
        "get_watchlists": (watchlist_tools.get_watchlists, "Get all watchlists for the account"),
        "update_watchlist": (watchlist_tools.update_watchlist, "Update an existing watchlist"),
        # Asset Tools
        "get_all_assets": (
            asset_tools.get_all_assets,
            "Get all available assets with optional filtering",
        ),
        "get_asset_info": (
            asset_tools.get_asset_info,
            "Get detailed information about a specific asset",
        ),
        # Corporate Action Tools
        "get_corporate_announcements": (
            corporate_action_tools.get_corporate_announcements,
            "Get corporate action announcements",
        ),
        # Streaming Tools
        "start_global_stock_stream": (
            streaming_tools.start_global_stock_stream,
            "Start global real-time stock data stream",
        ),
        "stop_global_stock_stream": (
            streaming_tools.stop_global_stock_stream,
            "Stop the global stock streaming session",
        ),
        "add_symbols_to_stock_stream": (
            streaming_tools.add_symbols_to_stock_stream,
            "Add symbols to existing stock stream",
        ),
        "get_stock_stream_data": (
            streaming_tools.get_stock_stream_data,
            "Get streaming data for analysis",
        ),
        "list_active_stock_streams": (
            streaming_tools.list_active_stock_streams,
            "List all active streaming subscriptions",
        ),
        "get_stock_stream_buffer_stats": (
            streaming_tools.get_stock_stream_buffer_stats,
            "Get detailed streaming buffer statistics",
        ),
        "clear_stock_stream_buffers": (
            streaming_tools.clear_stock_stream_buffers,
            "Clear streaming buffers to free memory",
        ),
        # Stream-Aware Tools
        "stream_aware_price_monitor": (
            streaming_tools.stream_aware_price_monitor,
            "Enhanced real-time price monitoring",
        ),
        "stream_optimized_order_placement": (
            streaming_tools.stream_optimized_order_placement,
            "Place order using optimal pricing from stream",
        ),
        # Order Tools
        "place_stock_order": (order_tools.place_stock_order, "Place a stock order of any type"),
        "get_orders": (order_tools.get_orders, "Get orders with specified status"),
        "cancel_order_by_id": (order_tools.cancel_order_by_id, "Cancel a specific order by ID"),
        "cancel_all_orders": (order_tools.cancel_all_orders, "Cancel all open orders"),
        "place_option_market_order": (
            order_tools.place_option_market_order,
            "Place single or multi-leg options market order",
        ),
        # Monitoring Tools
        "start_hybrid_monitoring": (
            monitoring_tools.start_hybrid_monitoring,
            "Start the hybrid trading monitoring service",
        ),
        "stop_hybrid_monitoring": (
            monitoring_tools.stop_hybrid_monitoring,
            "Stop the hybrid trading monitoring service",
        ),
        "get_hybrid_monitoring_status": (
            monitoring_tools.get_hybrid_monitoring_status,
            "Get monitoring service status",
        ),
        "verify_monitoring_active": (
            monitoring_tools.verify_monitoring_active,
            "Verify monitoring is running with proof",
        ),
        "add_symbols_to_watchlist": (
            monitoring_tools.add_symbols_to_watchlist,
            "Add symbols to monitoring watchlist",
        ),
        "remove_symbols_from_watchlist": (
            monitoring_tools.remove_symbols_from_watchlist,
            "Remove symbols from watchlist",
        ),
        "get_current_watchlist": (
            monitoring_tools.get_current_watchlist,
            "Get current monitoring watchlist",
        ),
        "get_current_trading_signals": (
            monitoring_tools.get_current_trading_signals,
            "Get current trading signals",
        ),
        "get_profit_spike_alerts": (
            monitoring_tools.get_profit_spike_alerts,
            "Get latest profit spike alerts",
        ),
        "check_positions_after_order": (
            monitoring_tools.check_positions_after_order,
            "Force position check after order execution",
        ),
        "ping_monitoring_service": (
            monitoring_tools.ping_monitoring_service,
            "Ping monitoring service for health check",
        ),
        "get_monitoring_alerts": (
            monitoring_tools.get_monitoring_alerts,
            "Get recent monitoring alerts",
        ),
        # FastAPI Monitoring Tools
        "start_fastapi_monitoring_service": (
            fastapi_monitoring_tools.start_fastapi_monitoring_service,
            "Start FastAPI monitoring service",
        ),
        "stop_fastapi_monitoring_service": (
            fastapi_monitoring_tools.stop_fastapi_monitoring_service,
            "Stop FastAPI monitoring service",
        ),
        "get_fastapi_monitoring_status": (
            fastapi_monitoring_tools.get_fastapi_monitoring_status,
            "Get FastAPI monitoring status",
        ),
        "add_symbols_to_fastapi_watchlist": (
            fastapi_monitoring_tools.add_symbols_to_fastapi_watchlist,
            "Add symbols to FastAPI watchlist",
        ),
        "remove_symbols_from_fastapi_watchlist": (
            fastapi_monitoring_tools.remove_symbols_from_fastapi_watchlist,
            "Remove symbols from FastAPI watchlist",
        ),
        "get_fastapi_positions": (
            fastapi_monitoring_tools.get_fastapi_positions,
            "Get positions from FastAPI service",
        ),
        "check_positions_after_order_fastapi": (
            fastapi_monitoring_tools.check_positions_after_order_fastapi,
            "Check positions after order via FastAPI",
        ),
        "get_fastapi_signals": (
            fastapi_monitoring_tools.get_fastapi_signals,
            "Get trading signals from FastAPI service",
        ),
        # Extended Hours Tools
        "get_extended_market_clock": (
            enhanced_market_clock.get_extended_market_clock,
            "Enhanced market clock with pre/post sessions",
        ),
        "validate_extended_hours_order": (
            extended_hours_orders.validate_extended_hours_order,
            "Validate extended hours order",
        ),
        "place_extended_hours_order": (
            extended_hours_orders.place_extended_hours_order,
            "Place order with automatic extended hours detection",
        ),
        "get_extended_hours_info": (
            extended_hours_orders.get_extended_hours_info,
            "Get extended hours trading information",
        ),
        # Advanced Plotting Tools
        "generate_advanced_technical_plots": (
            advanced_plotting_tool.generate_advanced_technical_plots,  # type: ignore[attr-defined]
            "Generate professional technical analysis plots",
        ),
        "generate_stock_plot": (
            plot_py_tool.generate_stock_plot,
            "Generate stock analysis plots using plot.py",
        ),
        # Help and Debug Tools
        "cleanup": (cleanup_tool.cleanup_server, "Clean up unnecessary temporary files"),
        "list_cleanup_candidates": (
            cleanup_tool.list_cleanup_candidates,
            "List files that can be cleaned up",
        ),
    }

    for tool_name, (func, description) in tool_definitions.items():
        try:
            signature = get_function_signature(func)

            tools.append(
                ToolSchema(
                    name=tool_name,
                    description=description,
                    parameters=signature["parameters"],
                    module=func.__module__,
                    function_name=func.__name__,
                )
            )
        except Exception as e:
            logger.warning(f"Could not process tool {tool_name}: {e}")

    return tools


@app.get("/api/resources/list", response_model=list[ResourceSchema])
async def list_all_resources() -> list[ResourceSchema]:
    """List all available MCP resources."""
    resources = []

    # Resource definitions with their corresponding functions
    resource_definitions = {
        "account://status": (
            account_resources.get_account_status,
            "Real-time account health and trading capacity",
        ),
        "positions://current": (
            position_resources.get_current_positions,
            "Live position data with P&L updates",
        ),
        "positions://intraday_pnl": (intraday_pnl.get_intraday_pnl, "Track today's intraday P&L"),
        "market://conditions": (
            market_resources.get_market_conditions,
            "Current market status and conditions",
        ),
        "market://momentum": (market_momentum.get_market_momentum, "Market momentum analysis"),
        "data://quality": (data_quality.get_data_quality_check, "Data quality and latency metrics"),  # type: ignore[attr-defined]
        "server://health": (
            server_health.get_server_health,
            "Server health and performance metrics",
        ),
        "server://session": (session_status.get_session_status, "Current session information"),
        "server://apis": (api_monitor.get_api_status, "API connectivity status"),
        "streaming://status": (
            streaming_resources.get_streaming_status,  # type: ignore[attr-defined]
            "Real-time streaming status",
        ),
        "streaming://buffers": (
            streaming_resources.get_buffer_status,  # type: ignore[attr-defined]
            "Streaming buffer statistics",
        ),
        "streaming://activity": (
            streaming_resources.get_activity_summary,  # type: ignore[attr-defined]
            "Recent streaming activity",
        ),
        "portfolio://summary": (
            portfolio_resources.get_portfolio_summary,  # type: ignore[attr-defined]
            "Portfolio summary and performance",
        ),
        "portfolio://risk": (portfolio_resources.get_risk_metrics, "Portfolio risk analysis"),  # type: ignore[attr-defined]
        "help://tools": (help_system.get_tools_help, "Available tools help"),  # type: ignore[attr-defined]
        "help://prompts": (help_system.get_prompts_help, "Available prompts help"),  # type: ignore[attr-defined]
    }

    for uri, (func, description) in resource_definitions.items():
        try:
            signature = get_function_signature(func)

            resources.append(
                ResourceSchema(
                    uri=uri,
                    name=uri.split("://")[1],
                    description=description,
                    parameters=signature["parameters"],
                    module=func.__module__,
                    function_name=func.__name__,
                )
            )
        except Exception as e:
            logger.warning(f"Could not process resource {uri}: {e}")

    return resources


@app.get("/api/prompts/list", response_model=list[PromptSchema])
async def list_all_prompts() -> list[PromptSchema]:
    """List all available MCP prompts."""
    prompts = []

    # Prompt definitions with their corresponding functions
    prompt_definitions = {
        "list_trading_capabilities": (
            list_trading_capabilities.list_trading_capabilities,  # type: ignore[attr-defined]
            "List all trading capabilities with guided workflows",
        ),
        "account_analysis": (
            account_analysis_prompt.account_analysis,
            "Complete portfolio health check with actionable insights",
        ),
        "position_management": (
            position_management_prompt.position_management,
            "Strategic position review and optimization",
        ),
        "market_analysis": (
            market_analysis_prompt.market_analysis,
            "Real-time market analysis with trading opportunities",
        ),
        "startup": (startup_prompt.startup, "Execute comprehensive day trading startup checks"),
        "day_trading_workflow": (
            day_trading_workflow.day_trading_workflow,  # type: ignore[attr-defined]
            "Complete day trading workflow execution",
        ),
        "master_scanning_workflow": (
            master_scanning_workflow.master_scanning_workflow,  # type: ignore[attr-defined]
            "Master scanning workflow for opportunity detection",
        ),
        "market_session_workflow": (
            market_session_workflow.market_session_workflow,  # type: ignore[attr-defined]
            "Market session analysis and workflow",
        ),
        "options_strategy": (
            options_strategy_prompt.options_strategy,  # type: ignore[attr-defined]
            "Options trading strategy analysis",
        ),
        "order_strategy": (
            order_strategy_prompt.order_strategy,  # type: ignore[attr-defined]
            "Order placement strategy optimization",
        ),
        "portfolio_review": (
            portfolio_review_prompt.portfolio_review,  # type: ignore[attr-defined]
            "Comprehensive portfolio review and analysis",
        ),
        "pro_technical_workflow": (
            pro_technical_workflow.pro_technical_workflow,  # type: ignore[attr-defined]
            "Professional technical analysis workflow",
        ),
        "risk_management": (
            risk_management_prompt.risk_management,  # type: ignore[attr-defined]
            "Risk management analysis and recommendations",
        ),
        "stream_centric_trading": (
            stream_centric_trading_prompt.stream_centric_trading,  # type: ignore[attr-defined]
            "Stream-centric trading workflow",
        ),
        "stock_news_analysis": (
            stock_news_prompt.stock_news_analysis,  # type: ignore[attr-defined]
            "Stock news analysis and impact assessment",
        ),
        "tools_reference": (
            tools_reference_prompt.list_all_tools,
            "Complete tools reference and usage guide",
        ),
    }

    for prompt_name, (func, description) in prompt_definitions.items():
        try:
            signature = get_function_signature(func)

            prompts.append(
                PromptSchema(
                    name=prompt_name,
                    description=description,
                    arguments=signature["parameters"],
                    module=func.__module__,
                    function_name=func.__name__,
                )
            )
        except Exception as e:
            logger.warning(f"Could not process prompt {prompt_name}: {e}")

    return prompts


# =============================================================================
# EXECUTION ENDPOINTS
# =============================================================================


@app.post("/api/execute/tool/{tool_name}", response_model=ExecutionResponse)
async def execute_tool(tool_name: str, request: ToolExecutionRequest) -> ExecutionResponse:
    """Execute a specific MCP tool with parameters."""

    # Tool function mapping
    tool_functions = {
        # Account Tools
        "get_account_info": account_tools.get_account_info,
        "get_positions": account_tools.get_positions,
        "get_open_position": account_tools.get_open_position,
        # Position Tools
        "close_position": position_tools.close_position,
        "close_all_positions": position_tools.close_all_positions,
        # Market Data Tools
        "get_stock_quote": market_data_tools.get_stock_quote,
        "get_stock_snapshots": market_data_tools.get_stock_snapshots,
        "get_stock_bars": market_data_tools.get_stock_bars,
        "get_stock_bars_intraday": market_data_tools.get_stock_bars_intraday,
        "get_stock_trades": market_data_tools.get_stock_trades,
        "get_stock_latest_trade": market_data_tools.get_stock_latest_trade,
        "get_stock_latest_bar": market_data_tools.get_stock_latest_bar,
        # Market Info Tools
        "get_market_clock": market_info_tools.get_market_clock,
        "get_market_calendar": market_info_tools.get_market_calendar,
        # Options Tools
        "get_option_contracts": options_tools.get_option_contracts,
        "get_option_latest_quote": options_tools.get_option_latest_quote,
        "get_option_snapshot": options_tools.get_option_snapshot,
        # Technical Analysis Tools
        "get_stock_peak_trough_analysis": peak_trough_analysis_tool.analyze_peaks_and_troughs,
        "analyze_peaks_troughs_fast": c_peak_trough_wrapper.analyze_peaks_troughs_fast,
        "compare_peak_trough_implementations": c_peak_trough_wrapper.compare_implementations,
        # Volume Bar Tools
        "get_volume_bars_from_history": volume_bars_tool.get_volume_bars_from_history,
        "compare_bar_types": volume_bars_tool.compare_bar_types,
        "start_volume_bar_streaming": volume_bars_tool.start_volume_bar_streaming,
        "get_volume_bar_stats": volume_bars_tool.get_volume_bar_stats,
        # Day Trading Scanner Tools
        "scan_day_trading_opportunities": day_trading_scanner.scan_day_trading_opportunities,
        "scan_explosive_momentum": day_trading_scanner.scan_explosive_momentum,
        "scan_after_hours_opportunities": after_hours_scanner.scan_after_hours_opportunities,
        "analyze_market_activity_fast": c_stock_analyzer_wrapper.analyze_market_activity_fast,
        "scan_explosive_stocks_fast": c_stock_analyzer_wrapper.scan_explosive_stocks_fast,
        "compare_analyzer_performance": c_stock_analyzer_wrapper.compare_analyzer_performance,
        # Streaming Tools
        "get_enhanced_streaming_analytics": streaming_tools.get_enhanced_streaming_analytics,  # type: ignore[attr-defined]
        "start_global_stock_stream": streaming_tools.start_global_stock_stream,
        "stop_global_stock_stream": streaming_tools.stop_global_stock_stream,
        "add_symbols_to_stock_stream": streaming_tools.add_symbols_to_stock_stream,
        "get_stock_stream_data": streaming_tools.get_stock_stream_data,
        "list_active_stock_streams": streaming_tools.list_active_stock_streams,
        "get_stock_stream_buffer_stats": streaming_tools.get_stock_stream_buffer_stats,
        "clear_stock_stream_buffers": streaming_tools.clear_stock_stream_buffers,
        "stream_aware_price_monitor": streaming_tools.stream_aware_price_monitor,
        "stream_optimized_order_placement": streaming_tools.stream_optimized_order_placement,
        # P&L Tools
        "get_single_day_pnl": single_day_pnl.get_single_day_pnl,
        # Watchlist Tools
        "create_watchlist": watchlist_tools.create_watchlist,
        "get_watchlists": watchlist_tools.get_watchlists,
        "update_watchlist": watchlist_tools.update_watchlist,
        # Asset Tools
        "get_all_assets": asset_tools.get_all_assets,
        "get_asset_info": asset_tools.get_asset_info,
        # Corporate Action Tools
        "get_corporate_announcements": corporate_action_tools.get_corporate_announcements,
        # Order Tools
        "place_stock_order": order_tools.place_stock_order,
        "get_orders": order_tools.get_orders,
        "cancel_order_by_id": order_tools.cancel_order_by_id,
        "cancel_all_orders": order_tools.cancel_all_orders,
        "place_option_market_order": order_tools.place_option_market_order,
        # Monitoring Tools
        "start_hybrid_monitoring": monitoring_tools.start_hybrid_monitoring,
        "stop_hybrid_monitoring": monitoring_tools.stop_hybrid_monitoring,
        "get_hybrid_monitoring_status": monitoring_tools.get_hybrid_monitoring_status,
        "verify_monitoring_active": monitoring_tools.verify_monitoring_active,
        "add_symbols_to_watchlist": monitoring_tools.add_symbols_to_watchlist,
        "remove_symbols_from_watchlist": monitoring_tools.remove_symbols_from_watchlist,
        "get_current_watchlist": monitoring_tools.get_current_watchlist,
        "get_current_trading_signals": monitoring_tools.get_current_trading_signals,
        "get_profit_spike_alerts": monitoring_tools.get_profit_spike_alerts,
        "check_positions_after_order": monitoring_tools.check_positions_after_order,
        "ping_monitoring_service": monitoring_tools.ping_monitoring_service,
        "get_monitoring_alerts": monitoring_tools.get_monitoring_alerts,
        # FastAPI Monitoring Tools
        "start_fastapi_monitoring_service": fastapi_monitoring_tools.start_fastapi_monitoring_service,
        "stop_fastapi_monitoring_service": fastapi_monitoring_tools.stop_fastapi_monitoring_service,
        "get_fastapi_monitoring_status": fastapi_monitoring_tools.get_fastapi_monitoring_status,
        "add_symbols_to_fastapi_watchlist": fastapi_monitoring_tools.add_symbols_to_fastapi_watchlist,
        "remove_symbols_from_fastapi_watchlist": fastapi_monitoring_tools.remove_symbols_from_fastapi_watchlist,
        "get_fastapi_positions": fastapi_monitoring_tools.get_fastapi_positions,
        "check_positions_after_order_fastapi": fastapi_monitoring_tools.check_positions_after_order_fastapi,
        "get_fastapi_signals": fastapi_monitoring_tools.get_fastapi_signals,
        # Extended Hours Tools
        "get_extended_market_clock": enhanced_market_clock.get_extended_market_clock,
        "validate_extended_hours_order": extended_hours_orders.validate_extended_hours_order,
        "place_extended_hours_order": extended_hours_orders.place_extended_hours_order,
        "get_extended_hours_info": extended_hours_orders.get_extended_hours_info,
        # Advanced Plotting Tools
        "generate_advanced_technical_plots": advanced_plotting_tool.generate_advanced_technical_plots,  # type: ignore[attr-defined]
        "generate_stock_plot": plot_py_tool.generate_stock_plot,
        # Cleanup Tools
        "cleanup": cleanup_tool.cleanup_server,
        "list_cleanup_candidates": cleanup_tool.list_cleanup_candidates,
    }

    if tool_name not in tool_functions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found. Available tools: {list(tool_functions.keys())}",
        )

    func = tool_functions[tool_name]
    return await execute_function_safely(func, **request.parameters)


@app.get("/api/execute/resource/{resource_uri:path}", response_model=ExecutionResponse)
async def get_resource(
    resource_uri: str, request: ResourceRequest | None = None
) -> ExecutionResponse:
    """Get data from a specific MCP resource."""

    # Resource function mapping
    resource_functions = {
        "account://status": account_resources.get_account_status,
        "positions://current": position_resources.get_current_positions,
        "positions://intraday_pnl": intraday_pnl.get_intraday_pnl,
        "market://conditions": market_resources.get_market_conditions,
        "market://momentum": market_momentum.get_market_momentum,
        "data://quality": data_quality.get_data_quality_check,  # type: ignore[attr-defined]
        "server://health": server_health.get_server_health,
        "server://session": session_status.get_session_status,
        "server://apis": api_monitor.get_api_status,
        "streaming://status": streaming_resources.get_streaming_status,  # type: ignore[attr-defined]
        "streaming://buffers": streaming_resources.get_buffer_status,  # type: ignore[attr-defined]
        "streaming://activity": streaming_resources.get_activity_summary,  # type: ignore[attr-defined]
        "portfolio://summary": portfolio_resources.get_portfolio_summary,  # type: ignore[attr-defined]
        "portfolio://risk": portfolio_resources.get_risk_metrics,  # type: ignore[attr-defined]
    }

    if resource_uri not in resource_functions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource '{resource_uri}' not found. Available resources: {list(resource_functions.keys())}",
        )

    func = resource_functions[resource_uri]
    parameters = request.parameters if request else {}
    return await execute_function_safely(func, **parameters)


@app.post("/api/execute/prompt/{prompt_name}", response_model=ExecutionResponse)
async def execute_prompt(prompt_name: str, request: PromptExecutionRequest) -> ExecutionResponse:
    """Execute a specific MCP prompt with arguments."""

    # Prompt function mapping
    prompt_functions = {
        "list_trading_capabilities": list_trading_capabilities.list_trading_capabilities,  # type: ignore[attr-defined]
        "account_analysis": account_analysis_prompt.account_analysis,
        "position_management": position_management_prompt.position_management,
        "market_analysis": market_analysis_prompt.market_analysis,
        "startup": startup_prompt.startup,
        "day_trading_workflow": day_trading_workflow.day_trading_workflow,  # type: ignore[attr-defined]
        "master_scanning_workflow": master_scanning_workflow.master_scanning_workflow,  # type: ignore[attr-defined]
        "market_session_workflow": market_session_workflow.market_session_workflow,  # type: ignore[attr-defined]
        "options_strategy": options_strategy_prompt.options_strategy,  # type: ignore[attr-defined]
        "order_strategy": order_strategy_prompt.order_strategy,  # type: ignore[attr-defined]
        "portfolio_review": portfolio_review_prompt.portfolio_review,  # type: ignore[attr-defined]
        "pro_technical_workflow": pro_technical_workflow.pro_technical_workflow,  # type: ignore[attr-defined]
        "risk_management": risk_management_prompt.risk_management,  # type: ignore[attr-defined]
        "stream_centric_trading": stream_centric_trading_prompt.stream_centric_trading,  # type: ignore[attr-defined]
        "stock_news_analysis": stock_news_prompt.stock_news_analysis,  # type: ignore[attr-defined]
        "tools_reference": tools_reference_prompt.list_all_tools,
    }

    if prompt_name not in prompt_functions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{prompt_name}' not found. Available prompts: {list(prompt_functions.keys())}",
        )

    func = prompt_functions[prompt_name]
    return await execute_function_safely(func, **request.arguments)


# =============================================================================
# STATUS AND HEALTH ENDPOINTS
# =============================================================================


@app.get("/api/status", response_model=ServiceStatus)
async def get_service_status() -> ServiceStatus:
    """Get comprehensive service status."""
    uptime = time.time() - getattr(app.state, "start_time", time.time())
    execution_count = getattr(app.state, "execution_count", 0)

    return ServiceStatus(
        status="running",
        uptime=uptime,
        total_executions=execution_count,
        active_connections=len(active_connections),
        server_info={
            "mcp_server_initialized": mcp_server is not None,
            "python_version": sys.version,
            "fastapi_version": "0.104.1",  # Approximate version
            "port": 8002,
            "cors_enabled": True,
            "websocket_enabled": True,
        },
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return HTMLResponse(
        content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MCP Execution Service</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-left: 4px solid #007acc; }
            .method { color: #007acc; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🚀 MCP Execution Service</h1>
        <p>REST API for executing MCP tools, resources, and prompts with live connections</p>

        <h2>📊 Discovery Endpoints</h2>
        <div class="endpoint"><span class="method">GET</span> /api/tools/list - List all available tools</div>
        <div class="endpoint"><span class="method">GET</span> /api/resources/list - List all available resources</div>
        <div class="endpoint"><span class="method">GET</span> /api/prompts/list - List all available prompts</div>

        <h2>⚡ Execution Endpoints</h2>
        <div class="endpoint"><span class="method">POST</span> /api/execute/tool/{tool_name} - Execute any tool</div>
        <div class="endpoint"><span class="method">GET</span> /api/execute/resource/{resource_uri} - Get resource data</div>
        <div class="endpoint"><span class="method">POST</span> /api/execute/prompt/{prompt_name} - Run any prompt</div>

        <h2>🔄 Real-time</h2>
        <div class="endpoint"><span class="method">WS</span> /ws/stream - WebSocket streaming interface</div>

        <h2>📈 Status</h2>
        <div class="endpoint"><span class="method">GET</span> /api/status - Service status and metrics</div>
        <div class="endpoint"><span class="method">GET</span> /health - Health check</div>

        <p><strong>Port:</strong> 8002 | <strong>CORS:</strong> Enabled | <strong>Real-time:</strong> WebSocket</p>
        <p><a href="/docs">📚 Interactive API Documentation</a></p>
    </body>
    </html>
    """
    )


# =============================================================================
# WEBSOCKET ENDPOINTS
# =============================================================================


@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming execution results."""
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            # Wait for client message
            data = await websocket.receive_text()

            try:
                request_data = json.loads(data)
                request_type = request_data.get("type")

                if request_type == "execute_tool":
                    tool_name = request_data.get("tool_name")
                    parameters = request_data.get("parameters", {})

                    # Execute tool and stream result
                    response = await execute_tool(
                        tool_name, ToolExecutionRequest(parameters=parameters)
                    )

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "tool_result",
                                "tool_name": tool_name,
                                "response": response.dict(),
                            }
                        )
                    )

                elif request_type == "get_resource":
                    resource_uri = request_data.get("resource_uri")
                    parameters = request_data.get("parameters", {})

                    # Get resource and stream result
                    response = await get_resource(
                        resource_uri, ResourceRequest(parameters=parameters)
                    )

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "resource_result",
                                "resource_uri": resource_uri,
                                "response": response.dict(),
                            }
                        )
                    )

                elif request_type == "execute_prompt":
                    prompt_name = request_data.get("prompt_name")
                    arguments = request_data.get("arguments", {})

                    # Execute prompt and stream result
                    response = await execute_prompt(
                        prompt_name, PromptExecutionRequest(arguments=arguments)
                    )

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "prompt_result",
                                "prompt_name": prompt_name,
                                "response": response.dict(),
                            }
                        )
                    )

                elif request_type == "ping":
                    await websocket.send_text(
                        json.dumps({"type": "pong", "timestamp": datetime.now(UTC).isoformat()})
                    )

                else:
                    await websocket.send_text(
                        json.dumps(
                            {"type": "error", "message": f"Unknown request type: {request_type}"}
                        )
                    )

            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON format"})
                )
            except Exception as e:
                await websocket.send_text(
                    json.dumps(
                        {"type": "error", "message": str(e), "traceback": traceback.format_exc()}
                    )
                )

    except WebSocketDisconnect:
        pass
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)


# =============================================================================
# MAIN EXECUTION
# =============================================================================


def main() -> None:
    """Main entry point for the MCP execution service."""
    logger.info("🚀 Starting MCP Execution Service on port 8002...")

    uvicorn.run(
        "alpaca_mcp_server.web.mcp_execution_service:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
