"""Discover - Perplexity general discover pages (/top + /tech) via Camoufox."""

import asyncio
from pathlib import Path


async def discover(articles: int = 500) -> str:
    """
    Get comprehensive research data from Perplexity Discover pages.

    Scrapes two discover pages for comprehensive research:
    - /discover/top - Trending/popular content
    - /discover/tech - Technology news and articles

    Note: /discover/you requires authentication for personalized content,
    so it's excluded from scraping.

    Bypasses Cloudflare to fetch ALL data including:
    - Combined feed from both pages with source tags [top]/[tech]
    - Popular threads and discussions
    - Topic categories
    - Per-page article counts

    Args:
        articles: Total articles across both pages (default: 500, max: 1000)

    Returns:
        Comprehensive discover data for research

    Examples:
        /discover           # Fetch 500 articles (default)
        /discover 100       # Fetch 100 articles
        /discover 1000      # Fetch 1000 articles (max)
    """
    # Path to the Camoufox scraper script
    script_path = Path.cwd() / "external_tools" / "scrapers" / "pplx-camoufox.py"

    if not script_path.exists():
        return f"Error: pplx-camoufox.py script not found at {script_path}"

    # Enforce limits (default 500, max 1000)
    if articles > 1000:
        articles = 1000
    elif articles < 1:
        articles = 500

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

        # Longer timeout for 2 pages with up to 1000 articles
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=240  # 4 minute timeout for 2 pages
        )

        output = stdout.decode("utf-8")

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
            return f"Error running pplx-camoufox --discover: {error_msg}"

        if not output.strip():
            return "No discover data returned"

        return output

    except asyncio.TimeoutError:
        return f"Timeout: Exceeded 240 seconds fetching {articles} articles from discover pages"
    except FileNotFoundError:
        return "Error: 'uv' command not found. Make sure uv is installed."
    except Exception as e:
        return f"Error: {str(e)}"
