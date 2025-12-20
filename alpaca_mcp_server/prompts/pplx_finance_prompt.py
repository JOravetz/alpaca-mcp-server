"""Perplexity Finance Comprehensive Analysis - Bypasses Cloudflare with Camoufox."""

import asyncio
from pathlib import Path


async def pplx_finance(symbol: str) -> str:
    """
    Get comprehensive stock analysis from Perplexity Finance using Camoufox.

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

    Returns:
        Comprehensive stock analysis with all Perplexity Finance data
    """
    if not symbol:
        return "Error: Please provide a stock symbol (e.g., /pplx-finance RKLB)"

    # Clean the symbol input
    symbol = symbol.strip().upper()

    # Path to the Camoufox scraper script
    script_path = Path.cwd() / "external_tools" / "scrapers" / "pplx-camoufox.py"

    if not script_path.exists():
        return f"Error: pplx-camoufox.py script not found at {script_path}"

    try:
        # Build command
        cmd = ["uv", "run", "python3", str(script_path), symbol]

        # Run the scraper script
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(script_path.parent),
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=120  # 2 minute timeout
        )

        output = stdout.decode("utf-8")

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
            return f"Error running pplx-camoufox: {error_msg}"

        if not output.strip():
            return f"No data returned for {symbol}"

        return output

    except asyncio.TimeoutError:
        return f"Timeout: Exceeded 120 seconds fetching {symbol}"
    except FileNotFoundError:
        return "Error: 'uv' command not found. Make sure uv is installed."
    except Exception as e:
        return f"Error: {str(e)}"
