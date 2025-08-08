"""Stock News Fetcher - Get latest Yahoo Finance RSS news for any ticker."""

import subprocess
from pathlib import Path


async def stock_news(ticker: str) -> str:
    """
    Fetch latest news for a stock ticker from Yahoo Finance RSS feed.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA', 'TTD')

    Returns:
        Formatted news articles with timestamps and links
    """
    if not ticker:
        return "❌ Error: Please provide a ticker symbol (e.g., /stock-news AAPL)"

    # Clean the ticker input
    ticker = ticker.strip().upper()

    # Path to the RSS script
    script_path = Path.cwd() / "yf_rss.py"

    if not script_path.exists():
        return f"❌ Error: RSS news script not found at {script_path}"

    try:
        # Run the RSS fetcher using uv
        result = subprocess.run(
            ["uv", "run", "python", str(script_path), ticker],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            if "ModuleNotFoundError" in result.stderr:
                return "❌ Error: Missing dependencies. Run: uv add feedparser"
            return f"❌ Error fetching news: {result.stderr[:200]}"

        output = result.stdout.strip()

        if not output:
            return f"📰 No news found for {ticker}"

        # Add header if not already present
        if not output.startswith("📊"):
            output = f"📊 {ticker} - Latest News\n{'='*60}\n{output}"

        return output

    except subprocess.TimeoutExpired:
        return f"⏱️ Request timed out while fetching news for {ticker}"
    except Exception as e:
        return f"❌ Error: {str(e)}"
