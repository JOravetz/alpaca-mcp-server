"""Resource registration module for MCP server."""

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


def register_account_resources(mcp):
    """Register account-related resources."""

    @mcp.resource("account://status")
    async def get_account_status() -> dict:
        """Real-time account health and trading capacity."""
        return await account_resources.get_account_status()


def register_position_resources(mcp):
    """Register position-related resources."""

    @mcp.resource("positions://current")
    async def get_current_positions() -> dict:
        """Live position data with P&L updates."""
        return await position_resources.get_current_positions()

    @mcp.resource("positions://intraday_pnl")
    async def get_intraday_pnl_resource() -> dict:
        """Track today's intraday P&L with default parameters."""
        return await intraday_pnl.get_intraday_pnl()


def register_market_resources(mcp):
    """Register market-related resources."""

    @mcp.resource("market://conditions")
    async def get_market_conditions() -> dict:
        """Current market status and conditions."""
        return await market_resources.get_market_conditions()

    @mcp.resource("market://momentum")
    async def get_market_momentum_resource() -> dict:
        """Real-time market momentum for SPY with default parameters."""
        return await market_momentum.get_market_momentum()


def register_portfolio_resources(mcp):
    """Register portfolio-related resources."""

    @mcp.resource("portfolio://performance")
    async def get_portfolio_performance() -> dict:
        """Real-time portfolio performance metrics and P&L analysis."""
        return await portfolio_resources.get_portfolio_performance()

    @mcp.resource("portfolio://allocation")
    async def get_portfolio_allocation() -> dict:
        """Asset allocation breakdown with winners/losers analysis."""
        return await portfolio_resources.get_portfolio_allocation()

    @mcp.resource("portfolio://risk")
    async def get_portfolio_risk() -> dict:
        """Portfolio risk metrics and exposure analysis."""
        return await portfolio_resources.get_portfolio_risk()


def register_streaming_resources(mcp):
    """Register streaming-related resources."""

    @mcp.resource("streams://status")
    async def get_stream_status() -> dict:
        """Real-time streaming status and buffer statistics."""
        return await streaming_resources.get_stream_status()

    @mcp.resource("streams://performance")
    async def get_stream_performance() -> dict:
        """Streaming performance metrics and health indicators."""
        return await streaming_resources.get_stream_performance()


def register_system_resources(mcp):
    """Register system monitoring resources."""

    @mcp.resource("data://quality")
    async def get_data_quality_resource() -> dict:
        """Monitor data feed quality with default parameters."""
        return await data_quality.get_data_quality()

    @mcp.resource("server://health")
    async def get_server_health_resource() -> dict:
        """Comprehensive server health monitoring."""
        return await server_health.get_server_health()

    @mcp.resource("server://session")
    async def get_session_status_resource() -> dict:
        """Trading session and market status."""
        return await session_status.get_session_status()

    @mcp.resource("server://apis")
    async def get_api_status_resource() -> dict:
        """Monitor API connections and performance."""
        return await api_monitor.get_api_status()


def register_help_resources(mcp):
    """Register help system resources."""

    @mcp.resource("help://tools")
    async def get_all_tools_help_resource() -> str:
        """Comprehensive help for all available tools organized by category."""
        return await help_system.get_all_tools_help_resource()

    @mcp.resource("help://tools/{tool_name}")
    async def get_tool_help_resource(tool_name: str) -> str:
        """Detailed help for a specific tool including parameters and examples."""
        return await help_system.get_tool_help_resource(tool_name)

    @mcp.resource("help://prompts")
    async def get_all_prompts_help_resource() -> str:
        """Comprehensive help for all available workflows/prompts."""
        return await help_system.get_all_prompts_help_resource()

    @mcp.resource("help://prompts/{prompt_name}")
    async def get_prompt_help_resource(prompt_name: str) -> str:
        """Detailed help for a specific workflow/prompt including parameters and examples."""
        return await help_system.get_prompt_help_resource(prompt_name)

    @mcp.resource("help://search/{query}")
    async def search_tools_resource(query: str) -> str:
        """Search tools by name, description, or category."""
        return await help_system.search_tools_resource(query)


def register_resource_mirror_tools(mcp):
    """Register resource mirror tools for Claude Code compatibility."""

    @mcp.tool()
    async def resource_account_status() -> dict:
        """Tool mirror of account://status resource."""
        return await account_resources.get_account_status()

    @mcp.tool()
    async def resource_current_positions() -> dict:
        """Tool mirror of positions://current resource."""
        return await position_resources.get_current_positions()

    @mcp.tool()
    async def resource_market_conditions() -> dict:
        """Tool mirror of market://conditions resource."""
        return await market_resources.get_market_conditions()

    @mcp.tool()
    async def resource_market_momentum(
        symbol: str = "SPY",
        timeframe_minutes: int = 1,
        analysis_hours: int = 2,
        sma_short: int = 5,
        sma_long: int = 20,
    ) -> dict:
        """Tool mirror of market://momentum resource."""
        return await market_momentum.get_market_momentum(
            symbol=symbol,
            timeframe_minutes=timeframe_minutes,
            analysis_hours=analysis_hours,
            sma_short=sma_short,
            sma_long=sma_long,
        )

    @mcp.tool()
    async def resource_intraday_pnl(
        days_back: int = 0,
        include_open_positions: bool = True,
        min_trade_value: float = 0.0,
        symbol_filter: str | None = None,
    ) -> dict:
        """Tool mirror of positions://intraday_pnl resource."""
        return await intraday_pnl.get_intraday_pnl(
            days_back=days_back,
            include_open_positions=include_open_positions,
            min_trade_value=min_trade_value,
            symbol_filter=symbol_filter,
        )

    @mcp.tool()
    async def resource_data_quality(
        test_symbols: list | None = None,
        latency_threshold_ms: float = 500.0,
        quote_age_threshold_seconds: float = 60.0,
        spread_threshold_pct: float = 1.0,
    ) -> dict:
        """Tool mirror of data://quality resource."""
        return await data_quality.get_data_quality(
            test_symbols=test_symbols,  # type: ignore[arg-type]
            latency_threshold_ms=latency_threshold_ms,
            quote_age_threshold_seconds=quote_age_threshold_seconds,
            spread_threshold_pct=spread_threshold_pct,
        )

    @mcp.tool()
    async def resource_server_health() -> dict:
        """Tool mirror of server://health resource."""
        return await server_health.get_server_health()

    @mcp.tool()
    async def resource_session_status() -> dict:
        """Tool mirror of server://session resource."""
        return await session_status.get_session_status()

    @mcp.tool()
    async def resource_api_status() -> dict:
        """Tool mirror of server://apis resource."""
        return await api_monitor.get_api_status()


def register_all_resources(mcp):
    """Register all resources with the MCP server."""
    register_account_resources(mcp)
    register_position_resources(mcp)
    register_market_resources(mcp)
    register_portfolio_resources(mcp)
    register_streaming_resources(mcp)
    register_system_resources(mcp)
    register_help_resources(mcp)
    register_resource_mirror_tools(mcp)
