"""Day Trading Opportunity Scanner - Uses updated MCP scanner with professional formatting."""

from datetime import datetime

import pytz

from ..config.global_config import get_global_config


async def scan(
    trades_threshold: int | None = None,  # IGNORED - uses global config
    limit: int | None = 20,
    filename: str | None = "combined.lis",  # IGNORED - scans all assets
) -> str:
    """
    Execute EXPLOSIVE UP-ONLY day trading opportunity scan with extreme volatility focus.

    Uses the updated MCP scanner that filters for ONLY UP STOCKS with global config thresholds.
    NO BORING STOCKS - Only extreme volatility explosive movers.

    Args:
        trades_threshold: IGNORED - Always uses global config value (1000 trades/min)
        limit: Maximum number of explosive opportunities to analyze (default: 20)
        filename: IGNORED - Always scans ALL tradeable assets

    Returns:
        Formatted analysis with EXPLOSIVE UP-ONLY trading opportunities
    """

    # Load global configuration
    config = get_global_config()

    # Simple limit validation (trades_threshold no longer used)
    try:
        if limit is None:
            limit = 20
        elif isinstance(limit, str):
            limit = int(limit) if limit.isdigit() else 20
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 20

    try:
        # Use the updated MCP scanner that scans all symbols from combined.lis
        from ..tools.day_trading_scanner import scan_day_trading_opportunities

        # Call the updated scanner - parameters ignored, uses global config
        result = await scan_day_trading_opportunities(
            symbols="ALL",  # Scan all tradeable assets for explosive moves
            # Note: min_trades_per_minute and min_percent_change are ignored
            # Tool always uses global config values for consistency
            max_symbols=limit,
            sort_by=config.scanner.scanner_sort_method,
        )

        return result

    except Exception as e:
        # Fallback to error message
        edt = pytz.timezone("America/New_York")
        scan_time = datetime.now(edt).strftime("%Y-%m-%d %H:%M:%S EDT")

        return f"""
❌ **SCAN ERROR**
Time: {scan_time}
Error: {str(e)}

• Check MCP scanner is functioning
• Verify API connectivity
• Ensure all required files are present
"""


# Export the function
__all__ = ["scan"]
