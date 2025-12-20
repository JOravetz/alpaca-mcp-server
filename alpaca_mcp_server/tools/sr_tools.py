"""
Support & Resistance MCP Tools.

High-performance S/R analysis using the sr_alpaca C binary.
Provides professional-grade support/resistance detection with:
- Multiple timeframes (1Min to 1Month)
- Peak detection methods (scipy-style, hanning filter)
- Williams Fractals detection
- Volume Profile / POC analysis
- VWAP-based S/R detection
- Agglomerative clustering for level grouping
"""

import asyncio
import os
from pathlib import Path

# Path to the sr_alpaca binary
SR_ALPACA_BINARY = Path(os.path.expanduser("~/autotrade/bin/sr_alpaca"))

# Valid timeframes
VALID_TIMEFRAMES = [
    "1Min", "5Min", "15Min", "30Min",
    "1Hour", "2Hour", "4Hour",
    "1Day", "1Week", "1Month"
]

# Valid peak detection methods
VALID_METHODS = ["peak", "hanning"]


async def get_support_resistance(
    symbol: str,
    timeframe: str = "5Min",
    days: int = 30,
    clusters: int = 5,
    method: str = "peak",
    fractals: bool = False,
    volume_profile: bool = False,
    vwap: bool = False,
    samples: int = 10000,
    verbose: bool = False,
) -> str:
    """
    Get professional support and resistance levels for a stock.

    Uses high-performance C implementation with multiple analysis methods:
    - Scipy-style peak detection (EXACT Python match)
    - Williams Fractals (classic 5-bar pattern)
    - Volume Profile / POC (institutional-grade)
    - VWAP-based S/R detection

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "TSLA", "RKLB")
        timeframe: Bar timeframe - 1Min, 5Min, 15Min, 30Min, 1Hour, 2Hour, 4Hour, 1Day, 1Week, 1Month
        days: Number of trading days to analyze (default: 30)
        clusters: Number of S/R level clusters (default: 5)
        method: Peak detection method - "peak" (scipy-style) or "hanning"
        fractals: Enable Williams Fractals detection
        volume_profile: Enable Volume Profile / POC analysis
        vwap: Enable VWAP-based S/R detection
        samples: Maximum bars to fetch (default: 10000)
        verbose: Show detailed debug output

    Returns:
        Formatted S/R analysis with support levels, resistance levels, and current price context

    Examples:
        get_support_resistance("AAPL")
        get_support_resistance("TSLA", timeframe="1Hour", days=60)
        get_support_resistance("SPY", volume_profile=True, vwap=True)
        get_support_resistance("NVDA", fractals=True, volume_profile=True, vwap=True)
    """
    symbol = symbol.strip().upper()

    if not SR_ALPACA_BINARY.exists():
        return f"Error: sr_alpaca binary not found at {SR_ALPACA_BINARY}"

    if timeframe not in VALID_TIMEFRAMES:
        return f"Error: Invalid timeframe '{timeframe}'. Valid options: {', '.join(VALID_TIMEFRAMES)}"

    if method not in VALID_METHODS:
        return f"Error: Invalid method '{method}'. Valid options: {', '.join(VALID_METHODS)}"

    try:
        # Build command
        cmd = [
            str(SR_ALPACA_BINARY),
            "-s", symbol,
            "-t", timeframe,
            "-d", str(days),
            "-c", str(clusters),
            "-m", method,
            "-n", str(samples),
        ]

        if fractals:
            cmd.append("--fractals")
        if volume_profile:
            cmd.append("--volume-profile")
        if vwap:
            cmd.append("--vwap")
        if verbose:
            cmd.append("-v")

        # Run the sr_alpaca binary
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=60  # 1 minute timeout
        )

        output = stdout.decode("utf-8").strip()

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
            # Check for common errors
            if "No peaks detected" in error_msg or "No peaks detected" in output:
                return f"{symbol}: No S/R levels detected. Try different timeframe or more days."
            return f"Error running sr_alpaca: {error_msg}"

        if not output:
            return f"No S/R data returned for {symbol}"

        return output

    except TimeoutError:
        return f"Error: Timeout analyzing {symbol} (exceeded 60 seconds)"
    except FileNotFoundError:
        return f"Error: sr_alpaca binary not found at {SR_ALPACA_BINARY}"
    except Exception as e:
        return f"Error: {str(e)}"


async def get_support_resistance_comprehensive(
    symbol: str,
    timeframe: str = "5Min",
    days: int = 30,
    clusters: int = 5,
) -> str:
    """
    Get comprehensive S/R analysis with ALL features enabled.

    Combines peak detection, Williams Fractals, Volume Profile, and VWAP
    for maximum trading intelligence.

    Args:
        symbol: Stock ticker symbol
        timeframe: Bar timeframe (default: 5Min)
        days: Number of trading days (default: 30)
        clusters: Number of S/R clusters (default: 5)

    Returns:
        Full S/R analysis with all detection methods

    Examples:
        get_support_resistance_comprehensive("AAPL")
        get_support_resistance_comprehensive("RKLB", timeframe="1Hour", days=60)
    """
    return await get_support_resistance(
        symbol=symbol,
        timeframe=timeframe,
        days=days,
        clusters=clusters,
        fractals=True,
        volume_profile=True,
        vwap=True,
    )


async def get_volume_profile(
    symbol: str,
    timeframe: str = "5Min",
    days: int = 30,
) -> str:
    """
    Get Volume Profile analysis with POC (Point of Control) and Value Area.

    Identifies price levels with highest trading activity - key for
    institutional-grade support/resistance detection.

    Args:
        symbol: Stock ticker symbol
        timeframe: Bar timeframe (default: 5Min)
        days: Number of trading days (default: 30)

    Returns:
        Volume Profile analysis with POC and Value Area

    Examples:
        get_volume_profile("SPY")
        get_volume_profile("NVDA", timeframe="1Hour", days=60)
    """
    return await get_support_resistance(
        symbol=symbol,
        timeframe=timeframe,
        days=days,
        volume_profile=True,
    )


async def get_intraday_sr_levels(
    symbol: str,
    days: int = 5,
    clusters: int = 8,
) -> str:
    """
    Get intraday S/R levels optimized for day trading.

    Uses 5-minute bars with more clusters for granular level detection.
    Includes Volume Profile and VWAP for institutional-grade analysis.

    Args:
        symbol: Stock ticker symbol
        days: Number of trading days (default: 5)
        clusters: Number of S/R clusters (default: 8 for intraday)

    Returns:
        Intraday S/R levels for day trading

    Examples:
        get_intraday_sr_levels("AAPL")
        get_intraday_sr_levels("TSLA", days=3, clusters=10)
    """
    return await get_support_resistance(
        symbol=symbol,
        timeframe="5Min",
        days=days,
        clusters=clusters,
        volume_profile=True,
        vwap=True,
    )


async def get_swing_sr_levels(
    symbol: str,
    days: int = 60,
    clusters: int = 5,
) -> str:
    """
    Get S/R levels optimized for swing trading.

    Uses hourly bars over 60 days for medium-term level detection.
    Includes Williams Fractals for classic pattern recognition.

    Args:
        symbol: Stock ticker symbol
        days: Number of trading days (default: 60)
        clusters: Number of S/R clusters (default: 5)

    Returns:
        Swing trading S/R levels

    Examples:
        get_swing_sr_levels("AAPL")
        get_swing_sr_levels("SPY", days=90)
    """
    return await get_support_resistance(
        symbol=symbol,
        timeframe="1Hour",
        days=days,
        clusters=clusters,
        fractals=True,
        volume_profile=True,
    )


async def get_daily_sr_levels(
    symbol: str,
    days: int = 252,
    clusters: int = 5,
) -> str:
    """
    Get S/R levels from daily bars for position trading.

    Uses daily bars over 1 year (252 trading days) for major level detection.
    Includes all analysis features for comprehensive view.

    Args:
        symbol: Stock ticker symbol
        days: Number of trading days (default: 252 = 1 year)
        clusters: Number of S/R clusters (default: 5)

    Returns:
        Daily S/R levels for position trading

    Examples:
        get_daily_sr_levels("AAPL")
        get_daily_sr_levels("SPY", days=504)  # 2 years
    """
    return await get_support_resistance(
        symbol=symbol,
        timeframe="1Day",
        days=days,
        clusters=clusters,
        fractals=True,
        volume_profile=True,
    )
