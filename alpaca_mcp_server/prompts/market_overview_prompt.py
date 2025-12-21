"""Market Overview - Perplexity Finance main page data via Camoufox."""

import asyncio
from pathlib import Path


async def market_overview() -> str:
    """
    Get comprehensive market overview from Perplexity Finance main page.

    Bypasses Cloudflare to fetch ALL market data including:
    - Market indices (S&P, NASDAQ, Dow futures + VIX)
    - Market sentiment (bullish/bearish/upbeat indicator)
    - AI-generated market summary (top stories)
    - Top movers (gainers, losers, most active)
    - 11 equity sectors with ETF performance
    - Prediction markets from Polymarket
    - Popular cryptocurrencies (BTC, ETH, SOL, XRP)
    - Fixed income ETFs
    - Standout stocks with z-scores and explanations
    - Recent developments and latest headlines

    Returns:
        Comprehensive market overview for day trading research
    """
    # Path to the Camoufox scraper script
    script_path = Path.cwd() / "external_tools" / "scrapers" / "pplx-camoufox.py"

    if not script_path.exists():
        return f"Error: pplx-camoufox.py script not found at {script_path}"

    try:
        # Build command with --market flag
        cmd = ["uv", "run", "python3", str(script_path), "--market"]

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
            return f"Error running pplx-camoufox --market: {error_msg}"

        if not output.strip():
            return "No market data returned"

        return output

    except asyncio.TimeoutError:
        return "Timeout: Exceeded 120 seconds fetching market overview"
    except FileNotFoundError:
        return "Error: 'uv' command not found. Make sure uv is installed."
    except Exception as e:
        return f"Error: {str(e)}"
