"""
Perplexity Finance MCP Tools.

Fast REST API access to Perplexity Finance for real-time stock data.
For full AI analysis, use the /pplx slash command instead.
"""

import sys
from pathlib import Path

# Add external_tools to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "external_tools"))

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False


BASE_URL = "https://www.perplexity.ai"


def _create_scraper():
    """Create a cloudscraper instance to bypass Cloudflare."""
    return cloudscraper.create_scraper()


def _fetch_quote(scraper, symbol: str) -> dict:
    """Fetch stock quote data."""
    url = f"{BASE_URL}/rest/finance/quote/{symbol}?with_history=false&with_ui_hints=true"
    try:
        r = scraper.get(url, timeout=30)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def _fetch_profile(scraper, symbol: str) -> dict:
    """Fetch company profile data."""
    url = f"{BASE_URL}/rest/finance/profile/{symbol}"
    try:
        r = scraper.get(url, timeout=30)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


async def get_perplexity_quote(symbols: str) -> str:
    """
    Get real-time stock quotes from Perplexity Finance.
    
    Fast REST API access (~2 seconds) for quick price checks during trading.
    For comprehensive AI analysis with news and bull/bear cases, use /pplx command.
    
    Args:
        symbols: Comma-separated stock symbols (e.g., "NVDA,AAPL,SMX")
    
    Returns:
        Formatted quote data including price, change, after-hours, volume ratio
    
    Examples:
        get_perplexity_quote("NVDA")
        get_perplexity_quote("SMX,PMI,SNCR")
    """
    if not CLOUDSCRAPER_AVAILABLE:
        return "Error: cloudscraper not installed. Run: uv pip install cloudscraper"
    
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    scraper = _create_scraper()
    
    results = []
    for symbol in symbol_list:
        quote = _fetch_quote(scraper, symbol)
        
        if "error" in quote:
            results.append(f"{symbol}: Error - {quote['error']}")
            continue
        
        price = quote.get("price", 0)
        change_pct = quote.get("changesPercentage", 0)
        ah_price = quote.get("afterHoursPrice", price)
        ah_pct = quote.get("afterHoursPercentChange", 0)
        volume = quote.get("volume", 0)
        avg_volume = quote.get("avgVolume", 1)
        vol_ratio = volume / avg_volume if avg_volume else 0
        
        # Day range
        day_low = quote.get("dayLow", 0)
        day_high = quote.get("dayHigh", 0)
        
        # 52 week range
        year_low = quote.get("yearLow", 0)
        year_high = quote.get("yearHigh", 0)
        
        # Moving averages
        ma50 = quote.get("priceAvg50", 0)
        ma200 = quote.get("priceAvg200", 0)
        
        lines = [
            f"\n{'='*50}",
            f"  {symbol} - Perplexity Finance",
            f"{'='*50}",
            f"  Price:      ${price:.2f} ({change_pct:+.2f}%)",
        ]
        
        if ah_price and ah_price != price:
            lines.append(f"  After Hrs:  ${ah_price:.2f} ({ah_pct:+.2f}%)")
        
        lines.extend([
            f"  Day Range:  ${day_low:.2f} - ${day_high:.2f}",
            f"  52W Range:  ${year_low:.2f} - ${year_high:.2f}",
            f"  Volume:     {volume:,.0f} ({vol_ratio:.1f}x avg)",
        ])
        
        # Volume alert
        if vol_ratio >= 2.0:
            lines.append(f"  ⚠️  HIGH VOLUME - {vol_ratio:.1f}x average!")
        
        # MA context
        if ma50 > 0:
            pct_from_50 = ((price - ma50) / ma50) * 100
            lines.append(f"  50-Day MA:  ${ma50:.2f} ({pct_from_50:+.1f}%)")
        
        lines.append("")
        results.append("\n".join(lines))
    
    return "\n".join(results)


async def get_perplexity_movers() -> str:
    """
    Get today's top gainers from Perplexity Finance.
    
    Fetches the current top movers to identify explosive day-trading opportunities.
    Returns top gainers with price, change %, and volume data.
    
    Returns:
        Formatted list of top gaining stocks for day-trading
    """
    if not CLOUDSCRAPER_AVAILABLE:
        return "Error: cloudscraper not installed"
    
    # The top movers are shown on the finance homepage
    # We'll fetch a few known volatile symbols that typically appear
    hot_symbols = ["SMX", "PMI", "SNCR", "ANPA", "CERO", "FOXO", "IMPP", "MULN"]
    
    scraper = _create_scraper()
    movers = []
    
    for symbol in hot_symbols:
        quote = _fetch_quote(scraper, symbol)
        if "error" not in quote:
            change_pct = quote.get("changesPercentage", 0)
            if change_pct > 10:  # Only include if up more than 10%
                movers.append({
                    "symbol": symbol,
                    "price": quote.get("price", 0),
                    "change_pct": change_pct,
                    "volume": quote.get("volume", 0),
                    "avg_volume": quote.get("avgVolume", 1),
                })
    
    # Sort by change percentage
    movers.sort(key=lambda x: x["change_pct"], reverse=True)
    
    if not movers:
        return "No explosive movers found (>10% gain)"
    
    lines = [
        "\n" + "="*60,
        "  🚀 TOP MOVERS - Perplexity Finance",
        "="*60,
        ""
    ]
    
    for m in movers[:10]:
        vol_ratio = m["volume"] / m["avg_volume"] if m["avg_volume"] else 0
        vol_alert = "🔥" if vol_ratio >= 2.0 else ""
        lines.append(
            f"  {m['symbol']:6s} ${m['price']:8.2f}  {m['change_pct']:+7.2f}%  "
            f"Vol: {vol_ratio:.1f}x {vol_alert}"
        )
    
    lines.append("")
    return "\n".join(lines)
