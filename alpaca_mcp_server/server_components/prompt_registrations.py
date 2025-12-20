"""Prompt registration module for MCP server."""

from ..prompts import (
    account_analysis_prompt,
    market_analysis_prompt,
    pnl_bling_prompt,
    pplx_finance_prompt,
    position_management_prompt,
    scan_prompt,
    startup_prompt,
    stock_news_prompt,
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
        symbols: list = None, timeframe: str = "1Day", analysis_type: str = "comprehensive"  # type: ignore[assignment]
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
    async def scan(filename: str | None = None, limit: int = 20) -> str:
        """Scan for day trading opportunities using high-liquidity scanner and technical analysis.

        Args:
            filename: Optional path to file containing symbols (one per line). If not provided, scans ALL tradeable assets.
            limit: Maximum number of results to return (default: 20)

        Examples:
            /scan                                    # Scan all tradeable assets
            /scan ~/autotrade/momentum.lis          # Scan symbols from file
            /scan ~/autotrade/momentum.lis 50       # Scan file, return top 50
        """
        return await scan_prompt.scan(trades_threshold=None, limit=limit, filename=filename)

    @mcp.prompt()
    async def stock_news(ticker: str) -> str:
        """Get latest news for any stock ticker from Yahoo Finance RSS feed.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA', 'TTD')

        Examples:
            /stock-news AAPL
            /stock-news TTD
        """
        return await stock_news_prompt.stock_news(ticker)

    @mcp.prompt()
    async def pplx_finance(symbol: str) -> str:
        """Get comprehensive stock analysis from Perplexity Finance using Camoufox.

        Bypasses Cloudflare to fetch ALL available data including:
        - Real-time quote with after-hours pricing
        - Latest price movement summaries (THE GOLD for day trading)
        - Recent developments and headlines
        - Bullish vs Bearish key issues analysis
        - Sector peers with prices and changes
        - Earnings history with beat/miss indicators
        - Prediction markets data
        - Research reports with analyst sentiment

        Args:
            symbol: Stock ticker symbol (e.g., 'RKLB', 'NVDA', 'MIMI')

        Examples:
            /pplx-finance RKLB
            /pplx-finance NVDA
        """
        return await pplx_finance_prompt.pplx_finance(symbol)

    @mcp.prompt()
    async def pnl_bling(date: str | None = None) -> str:
        """💰 Generate P&L Dashboard with full bling-bling celebrations and Kokoro TTS.

        Features:
        - Kokoro TTS with Jessica's sultry voice congratulations
        - Tiered celebration animations based on profit level
        - LEGENDARY ($10k+): Full effects with trophy and fireworks
        - EPIC ($5k-$10k): Confetti and money rain
        - Interactive charts and real-time P&L data

        Args:
            date: Optional date in YYYY-MM-DD format (default: today)

        Example:
            /pnl-bling              # Uses today's date
            /pnl-bling 2025-09-15   # Specific date
        """
        import re
        from datetime import datetime

        import pytz

        # If no date provided or empty string, use today's date
        if not date or str(date).strip() == "":
            et_tz = pytz.timezone("America/New_York")
            date = datetime.now(et_tz).strftime("%Y-%m-%d")
        else:
            date = str(date).strip()
            # Clean up the date string - extract YYYY-MM-DD pattern if present
            date_match = re.search(r"\d{4}-\d{2}-\d{2}", date)
            if date_match:
                date = date_match.group()
            elif not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
                # If the input doesn't look like a date, use today
                et_tz = pytz.timezone("America/New_York")
                date = datetime.now(et_tz).strftime("%Y-%m-%d")

        # Always enable sound for full celebration
        sound = True

        return pnl_bling_prompt.generate_pnl_bling_prompt_text(date, sound)


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
