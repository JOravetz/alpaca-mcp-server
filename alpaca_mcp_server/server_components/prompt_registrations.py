"""Prompt registration module for MCP server."""

from ..prompts import (
    account_analysis_prompt,
    market_analysis_prompt,
    position_management_prompt,
    scan_prompt,
    startup_prompt,
    tools_reference_prompt,
)


def register_core_prompts(mcp):
    """Register core trading prompts."""

    @mcp.prompt()
    async def list_trading_capabilities() -> str:
        """List all Alpaca trading capabilities with guided workflows."""
        from ..prompts.list_trading_capabilities import list_trading_capabilities as ltc_func

        return await ltc_func()

    @mcp.prompt()
    async def account_analysis() -> str:
        """Complete portfolio health check with actionable insights."""
        return await account_analysis_prompt.account_analysis()

    @mcp.prompt()
    async def position_management(symbol: str | None = None) -> str:
        """Strategic position review and optimization."""
        return await position_management_prompt.position_management(symbol)

    @mcp.prompt()
    async def market_analysis(
        symbols: list = None, timeframe: str = "1Day", analysis_type: str = "comprehensive"
    ) -> str:
        """Real-time market analysis with trading opportunities."""
        return await market_analysis_prompt.market_analysis(symbols, timeframe, analysis_type)

    @mcp.prompt()
    async def list_all_tools() -> str:
        """List all available MCP tools with descriptions and usage examples."""
        return await tools_reference_prompt.list_all_tools()

    @mcp.prompt()
    async def startup() -> str:
        """Execute comprehensive day trading startup checks with parallel execution and high-liquidity scanner."""
        return await startup_prompt.startup()

    @mcp.prompt()
    async def scan() -> str:
        """Scan for day trading opportunities using high-liquidity scanner and technical analysis.

        Uses default parameters: 500 trades/minute threshold, 20 result limit, combined.lis file.
        For custom parameters, use the scan_day_trading_opportunities tool directly.
        """
        return await scan_prompt.scan(500, 20, "combined.lis")


def register_workflow_prompts(mcp):
    """Register advanced workflow prompts."""

    @mcp.prompt()
    async def day_trading_workflow(symbol: str | None = None) -> str:
        """Complete day trading analysis and setup workflow for any symbol."""
        from ..prompts.day_trading_workflow import day_trading_workflow as dtw_func

        return await dtw_func(symbol)

    @mcp.prompt()
    async def master_scanning_workflow(scan_type: str = "comprehensive") -> str:
        """Master scanner workflow using all available scanner tools simultaneously."""
        from ..prompts.master_scanning_workflow import master_scanning_workflow as msw_func

        return await msw_func(scan_type)

    @mcp.prompt()
    async def pro_technical_workflow(symbol: str, timeframe: str = "comprehensive") -> str:
        """Professional technical analysis workflow using advanced algorithms and peak/trough detection."""
        from ..prompts.pro_technical_workflow import pro_technical_workflow as ptw_func

        return await ptw_func(symbol, timeframe)

    @mcp.prompt()
    async def market_session_workflow(session_type: str = "full_day") -> str:
        """Complete market session strategy using timing tools and session-specific analysis."""
        from ..prompts.market_session_workflow import market_session_workflow as msw_func

        return await msw_func(session_type)


def register_stream_centric_prompts(mcp):
    """Register stream-centric trading prompts."""

    @mcp.prompt()
    async def stream_centric_trading_cycle(symbols: str = "AUTO") -> str:
        """Universal trading cycle with single-stream concurrent architecture.

        Args:
            symbols: Comma-separated symbols (e.g., "AAPL,MSFT") or "AUTO" for scanner results
        """
        from ..prompts.stream_centric_trading_prompt import (
            stream_centric_trading_cycle as sctc_func,
        )

        return await sctc_func(symbols)

    @mcp.prompt()
    async def stream_concurrent_monitoring_cycle(symbols: str = "AUTO") -> str:
        """Continuous monitoring cycle using stream-centric concurrent architecture.

        Args:
            symbols: Comma-separated symbols or "AUTO" for current stream symbols
        """
        from ..prompts.stream_centric_trading_prompt import (
            stream_concurrent_monitoring_cycle as scmc_func,
        )

        return await scmc_func(symbols)


def register_all_prompts(mcp):
    """Register all prompts with the MCP server."""
    register_core_prompts(mcp)
    register_workflow_prompts(mcp)
    register_stream_centric_prompts(mcp)
