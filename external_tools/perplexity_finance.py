#!/usr/bin/env python3
"""
Perplexity Finance API Fetcher
Bypasses Cloudflare to fetch stock data from Perplexity Finance.

Two methods available:
1. REST API (cloudscraper) - Fast quotes, profiles, earnings
2. Browser (undetected-chromedriver) - Full AI analysis, news, price movement

Usage:
    uv run python external_tools/perplexity_finance.py KITT PMI PLRZ
    uv run python external_tools/perplexity_finance.py AAPL --full
    uv run python external_tools/perplexity_finance.py TSLA --json
    uv run python external_tools/perplexity_finance.py NVDA --browser  # Full AI analysis
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime

try:
    import cloudscraper
except ImportError:
    print("Error: cloudscraper not installed. Run: uv pip install cloudscraper")
    sys.exit(1)


BASE_URL = "https://www.perplexity.ai"


def fetch_with_browser(symbol: str, timeout: int = 12) -> str:
    """
    Fetch full stock page using undetected-chromedriver.
    Returns formatted text with AI analysis, news, price movement history.

    Requires: xvfb, undetected-chromedriver, html2text
    """
    script = f'''
import undetected_chromedriver as uc
import time

driver = uc.Chrome(version_main=142)
driver.get("https://www.perplexity.ai/finance/{symbol.upper()}")
time.sleep({timeout})
print(driver.page_source)
driver.quit()
'''

    cmd = [
        "xvfb-run", "--auto-servernum",
        "uv", "run", "--with", "undetected-chromedriver",
        "python3", "-c", script
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 60
        )

        if result.returncode != 0:
            return f"Error fetching {symbol}: {result.stderr}"

        html = result.stdout

        # Convert HTML to text using html2text
        html2text_result = subprocess.run(
            ["html2text"],
            input=html,
            capture_output=True,
            text=True
        )

        return html2text_result.stdout

    except subprocess.TimeoutExpired:
        return f"Timeout fetching {symbol}"
    except FileNotFoundError as e:
        return f"Missing dependency: {e}. Install with: sudo apt install xvfb html2text"
    except Exception as e:
        return f"Error: {str(e)}"


def create_scraper():
    """Create a cloudscraper instance to bypass Cloudflare."""
    return cloudscraper.create_scraper()


def fetch_quote(scraper, symbol: str) -> dict:
    """Fetch stock quote data."""
    url = f"{BASE_URL}/rest/finance/quote/{symbol}?with_history=false&with_ui_hints=true"
    try:
        r = scraper.get(url, timeout=30)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def fetch_profile(scraper, symbol: str) -> dict:
    """Fetch company profile data."""
    url = f"{BASE_URL}/rest/finance/profile/{symbol}"
    try:
        r = scraper.get(url, timeout=30)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def fetch_earnings(scraper, symbol: str) -> list:
    """Fetch earnings history."""
    url = f"{BASE_URL}/rest/finance/earnings/{symbol}"
    try:
        r = scraper.get(url, timeout=30)
        if r.status_code == 200:
            return r.json()
        return [{"error": f"HTTP {r.status_code}"}]
    except Exception as e:
        return [{"error": str(e)}]


def fetch_financials(scraper, symbol: str) -> dict:
    """Fetch financial statements."""
    url = f"{BASE_URL}/rest/finance/financials/{symbol}"
    try:
        r = scraper.get(url, timeout=30)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def fetch_all(scraper, symbol: str) -> dict:
    """Fetch all available data for a symbol."""
    return {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "quote": fetch_quote(scraper, symbol),
        "profile": fetch_profile(scraper, symbol),
        "earnings": fetch_earnings(scraper, symbol),
    }


def format_quote_summary(quote: dict, profile: dict = None) -> str:
    """Format quote data as readable summary."""
    if "error" in quote:
        return f"Error: {quote['error']}"

    lines = []
    symbol = quote.get("symbol", "???")
    name = quote.get("name", profile.get("companyName", "Unknown") if profile else "Unknown")

    # Header
    lines.append(f"\n{'='*60}")
    lines.append(f"  {symbol} - {name}")
    lines.append(f"{'='*60}")

    # Price info
    price = quote.get("price", 0)
    change = quote.get("change", 0)
    change_pct = quote.get("changesPercentage", 0)

    direction = "+" if change >= 0 else ""
    lines.append(f"\n  Price:     ${price:.2f}  ({direction}{change:.2f} / {direction}{change_pct:.2f}%)")

    # After hours
    ah_price = quote.get("afterHoursPrice")
    ah_change_pct = quote.get("afterHoursPercentChange")
    ah_type = (quote.get("afterHoursType") or "").replace("_", " ").title()
    if ah_price:
        ah_dir = "+" if ah_change_pct >= 0 else ""
        lines.append(f"  {ah_type}:  ${ah_price:.2f}  ({ah_dir}{ah_change_pct:.2f}%)")

    # Day range
    day_low = quote.get("dayLow", 0)
    day_high = quote.get("dayHigh", 0)
    lines.append(f"\n  Day Range:  ${day_low:.2f} - ${day_high:.2f}")

    # Year range
    year_low = quote.get("yearLow", 0)
    year_high = quote.get("yearHigh", 0)
    lines.append(f"  52W Range:  ${year_low:.2f} - ${year_high:.2f}")

    # Volume
    volume = quote.get("volume", 0)
    avg_volume = quote.get("avgVolume", 0)
    vol_ratio = volume / avg_volume if avg_volume > 0 else 0
    lines.append(f"\n  Volume:     {volume:,.0f}")
    lines.append(f"  Avg Volume: {avg_volume:,.0f}")
    if vol_ratio > 1.5:
        lines.append(f"  Vol Ratio:  {vol_ratio:.1f}x  ** HIGH VOLUME **")
    elif vol_ratio > 0:
        lines.append(f"  Vol Ratio:  {vol_ratio:.1f}x")

    # Market cap
    mkt_cap = quote.get("marketCap", 0)
    if mkt_cap >= 1e9:
        lines.append(f"\n  Market Cap: ${mkt_cap/1e9:.2f}B")
    elif mkt_cap >= 1e6:
        lines.append(f"\n  Market Cap: ${mkt_cap/1e6:.2f}M")
    else:
        lines.append(f"\n  Market Cap: ${mkt_cap:,.0f}")

    # Fundamentals
    pe = quote.get("pe")
    eps = quote.get("eps")
    if pe and eps:
        lines.append(f"  P/E Ratio:  {pe:.2f}")
        lines.append(f"  EPS:        ${eps:.2f}")

    # Moving averages
    ma50 = quote.get("priceAvg50", 0)
    ma200 = quote.get("priceAvg200", 0)
    if ma50 > 0:
        pct_from_50 = ((price - ma50) / ma50) * 100
        lines.append(f"\n  50-Day MA:  ${ma50:.2f} ({pct_from_50:+.1f}% from current)")
    if ma200 > 0:
        pct_from_200 = ((price - ma200) / ma200) * 100
        lines.append(f"  200-Day MA: ${ma200:.2f} ({pct_from_200:+.1f}% from current)")

    # Profile info if available
    if profile and "error" not in profile:
        lines.append(f"\n  Exchange:   {profile.get('exchange', 'N/A')}")
        lines.append(f"  Industry:   {profile.get('industry', 'N/A')}")
        lines.append(f"  Sector:     {profile.get('sector', 'N/A')}")
        lines.append(f"  Employees:  {profile.get('fullTimeEmployees', 'N/A')}")

        desc = profile.get("description", "")
        if desc:
            # Truncate description
            if len(desc) > 200:
                desc = desc[:200] + "..."
            lines.append(f"\n  Description: {desc}")

    lines.append(f"\n{'='*60}\n")

    return "\n".join(lines)


def format_earnings_summary(earnings: list) -> str:
    """Format earnings data as readable summary."""
    if not earnings or (len(earnings) == 1 and "error" in earnings[0]):
        return "  No earnings data available.\n"

    lines = ["\n  RECENT EARNINGS:"]
    lines.append("  " + "-" * 50)

    for e in earnings[:4]:  # Last 4 quarters
        date = e.get("date", "")[:10]
        period = f"{e.get('fiscalPeriod', '')} {e.get('fiscalYear', '')}"
        revenue = e.get("actualRevenue", 0)
        eps = e.get("actualEps", 0)
        move = e.get("postEarningsMove1D")

        rev_str = f"${revenue/1e6:.1f}M" if revenue >= 1e6 else f"${revenue:,.0f}"
        move_str = f"{move*100:+.1f}%" if move else "N/A"

        lines.append(f"  {date} ({period}): Rev {rev_str}, EPS ${eps:.2f}, Move: {move_str}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch stock data from Perplexity Finance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s KITT PMI PLRZ          # Quick summary of multiple stocks
  %(prog)s AAPL --full            # Full report with earnings
  %(prog)s TSLA --json            # Raw JSON output
  %(prog)s NVDA --earnings        # Include earnings history
        """
    )
    parser.add_argument("symbols", nargs="+", help="Stock symbol(s) to look up")
    parser.add_argument("--full", "-f", action="store_true", help="Full report with all data")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON")
    parser.add_argument("--earnings", "-e", action="store_true", help="Include earnings data")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    parser.add_argument("--browser", "-b", action="store_true",
                        help="Use browser for full AI analysis (slower but more comprehensive)")

    args = parser.parse_args()

    scraper = create_scraper()

    for symbol in args.symbols:
        symbol = symbol.upper()

        # Browser mode - full AI analysis
        if args.browser:
            print(f"\n{'='*60}")
            print(f"  Fetching {symbol} via browser (AI analysis)...")
            print(f"{'='*60}\n")
            result = fetch_with_browser(symbol)
            print(result)
            continue

        if args.json or args.full:
            data = fetch_all(scraper, symbol)
            if args.json:
                print(json.dumps(data, indent=2))
            else:
                # Full formatted report
                quote = data.get("quote", {})
                profile = data.get("profile", {})
                earnings = data.get("earnings", [])

                print(format_quote_summary(quote, profile))
                print(format_earnings_summary(earnings))
        else:
            # Quick summary
            quote = fetch_quote(scraper, symbol)
            profile = fetch_profile(scraper, symbol) if not args.quiet else None

            if args.quiet:
                # One-line output
                if "error" not in quote:
                    price = quote.get("price", 0)
                    change_pct = quote.get("changesPercentage", 0)
                    ah_price = quote.get("afterHoursPrice", price)
                    ah_pct = quote.get("afterHoursPercentChange", 0)
                    volume = quote.get("volume", 0)
                    avg_vol = quote.get("avgVolume", 1)
                    vol_ratio = volume / avg_vol if avg_vol else 0

                    print(f"{symbol}: ${price:.2f} ({change_pct:+.1f}%) | AH: ${ah_price:.2f} ({ah_pct:+.1f}%) | Vol: {vol_ratio:.1f}x")
                else:
                    print(f"{symbol}: Error - {quote.get('error')}")
            else:
                print(format_quote_summary(quote, profile))

                if args.earnings:
                    earnings = fetch_earnings(scraper, symbol)
                    print(format_earnings_summary(earnings))


if __name__ == "__main__":
    main()
