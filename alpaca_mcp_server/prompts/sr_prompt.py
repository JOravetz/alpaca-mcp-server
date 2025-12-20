"""Support & Resistance Analysis Prompt - Uses sr_alpaca C binary."""


async def sr(symbol: str, mode: str = "intraday") -> str:
    """
    Get professional support and resistance levels for day trading.

    Uses high-performance C implementation (sr_alpaca) with:
    - Scipy-style peak detection (EXACT Python match)
    - Williams Fractals (classic 5-bar pattern)
    - Volume Profile / POC (institutional-grade)
    - VWAP-based S/R detection
    - Agglomerative clustering for level grouping

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'RKLB', 'ASTS')
        mode: Analysis mode - 'intraday' (default), 'swing', 'daily', or 'comprehensive'

    Examples:
        /sr RKLB              # Intraday S/R (5Min, 5 days)
        /sr ASTS intraday     # Same as above
        /sr NVDA swing        # Swing trading (1Hour, 60 days)
        /sr SPY daily         # Position trading (1Day, 252 days)
        /sr TSLA comprehensive # All features enabled
    """
    if not symbol:
        return "Error: Please provide a stock symbol (e.g., /sr RKLB)"

    symbol = symbol.strip().upper()
    mode = mode.strip().lower() if mode else "intraday"

    # Import the sr_tools module
    from ..tools import sr_tools

    # Route to appropriate analysis based on mode
    if mode == "comprehensive":
        result = await sr_tools.get_support_resistance_comprehensive(
            symbol=symbol,
            timeframe="5Min",
            days=30,
            clusters=8,
        )
    elif mode == "swing":
        result = await sr_tools.get_swing_sr_levels(
            symbol=symbol,
            days=60,
            clusters=5,
        )
    elif mode == "daily":
        result = await sr_tools.get_daily_sr_levels(
            symbol=symbol,
            days=252,
            clusters=5,
        )
    else:  # Default: intraday
        result = await sr_tools.get_intraday_sr_levels(
            symbol=symbol,
            days=5,
            clusters=8,
        )

    # Format the output with mode info
    header = f"""
================================================================================
                    SUPPORT & RESISTANCE ANALYSIS: {symbol}
                    Mode: {mode.upper()} | Powered by sr_alpaca
================================================================================
"""
    return header + result
