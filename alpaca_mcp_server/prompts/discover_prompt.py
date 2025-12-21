"""Finance Discover - Perplexity Finance discover page data via Camoufox."""

import asyncio
from pathlib import Path


async def discover(articles: int = 200) -> str:
    """
    Get finance trends, news, and topics from Perplexity Finance discover page.

    Bypasses Cloudflare to fetch ALL discover data including:
    - Market indices (S&P, NASDAQ, Dow with % changes)
    - Finance news & analysis articles (configurable count)
    - Trending content and topics
    - Trending companies with real-time quotes
    - Topic categories

    Args:
        articles: Number of articles to fetch (default: 200, max: 500)

    Returns:
        Comprehensive finance discover data for day trading research

    Examples:
        /discover           # Fetch 200 articles (default)
        /discover 50        # Fetch 50 articles
        /discover 500       # Fetch 500 articles (max)
    """
    # Path to the Camoufox scraper script
    script_path = Path.cwd() / "external_tools" / "scrapers" / "pplx-camoufox.py"

    if not script_path.exists():
        return f"Error: pplx-camoufox.py script not found at {script_path}"

    # Enforce limits
    if articles > 500:
        articles = 500
    elif articles < 1:
        articles = 200

    try:
        # Build command with --discover flag and --articles
        cmd = ["uv", "run", "python3", str(script_path), "--discover", "--articles", str(articles)]

        # Run the scraper script
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(script_path.parent),
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=180  # 3 minute timeout for larger article counts
        )

        output = stdout.decode("utf-8")

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
            return f"Error running pplx-camoufox --discover: {error_msg}"

        if not output.strip():
            return "No discover data returned"

        return output

    except asyncio.TimeoutError:
        return f"Timeout: Exceeded 180 seconds fetching {articles} articles from discover page"
    except FileNotFoundError:
        return "Error: 'uv' command not found. Make sure uv is installed."
    except Exception as e:
        return f"Error: {str(e)}"
