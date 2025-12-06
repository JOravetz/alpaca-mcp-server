#!/usr/bin/env python3
"""Format Finviz JSON data for terminal display."""
import sys
import json

def format_screener(data):
    """Format screener results for display."""
    print("=" * 70)
    print(f" FINVIZ {data.get('scan_type', 'SCANNER').upper()} - {data.get('timestamp', '')}")
    print("=" * 70)
    print()

    stocks = data.get("stocks", [])
    if not stocks:
        print(" No stocks found.")
        print()
        print(f" URL: {data.get('url', 'N/A')}")
        return

    # Header
    print(f" {'TICKER':<8} {'PRICE':>10} {'CHANGE':>10} {'VOLUME':>12} {'MKT CAP':>10} {'SECTOR':<20}")
    print("-" * 70)

    for stock in stocks[:20]:  # Limit to 20 stocks
        ticker = stock.get("ticker", "")[:8]
        price = stock.get("price", "")[:10]
        change = stock.get("change", "")[:10]
        volume = stock.get("volume", "")[:12]
        market_cap = stock.get("market_cap", "")[:10]
        sector = stock.get("sector", "")[:20]

        # Color the change (using ANSI codes)
        if change.startswith("-"):
            change_display = f"\033[91m{change}\033[0m"  # Red
        elif change and change != "-":
            change_display = f"\033[92m{change}\033[0m"  # Green
        else:
            change_display = change

        print(f" {ticker:<8} {price:>10} {change_display:>10} {volume:>12} {market_cap:>10} {sector:<20}")

    print()
    print(f" Showing {min(len(stocks), 20)} of {data.get('total_found', len(stocks))} results")
    print()
    print(f" \033[93m{data.get('note', '')}\033[0m")  # Yellow note
    print()
    print(f" URL: {data.get('url', 'N/A')}")
    print("=" * 70)


def format_quote(data):
    """Format individual stock quote for display."""
    ticker = data.get("ticker", "UNKNOWN")
    company = data.get("company", "Unknown Company")

    print("=" * 70)
    print(f" {company} ({ticker})")
    print("=" * 70)
    print()

    # Key metrics in two columns
    key_fields = [
        ("price", "Price"),
        ("change", "Change"),
        ("volume", "Volume"),
        ("avg_volume", "Avg Volume"),
        ("market_cap", "Market Cap"),
        ("pe", "P/E"),
        ("eps_(ttm)", "EPS (TTM)"),
        ("forward_pe", "Forward P/E"),
        ("dividend_yield", "Dividend"),
        ("52w_high", "52W High"),
        ("52w_low", "52W Low"),
        ("beta", "Beta"),
        ("rsi_(14)", "RSI (14)"),
        ("target_price", "Target Price"),
        ("short_float", "Short Float"),
        ("short_ratio", "Short Ratio"),
    ]

    print(" Key Metrics:")
    print("-" * 35)
    for key, label in key_fields:
        value = data.get(key, "")
        if value:
            # Color price changes
            if "change" in key.lower():
                if value.startswith("-"):
                    value = f"\033[91m{value}\033[0m"  # Red
                else:
                    value = f"\033[92m{value}\033[0m"  # Green
            print(f"   {label:<15} {value}")

    print()

    # News section
    news = data.get("news", [])
    if news:
        print(" Recent News:")
        print("-" * 35)
        for item in news[:5]:
            time = item.get("time", "")
            headline = item.get("headline", "")[:50]
            print(f"   [{time}] {headline}...")
        print()

    # Analyst ratings
    ratings = data.get("analyst_ratings", [])
    if ratings:
        print(" Analyst Ratings:")
        print("-" * 35)
        for rating in ratings[:3]:
            date = rating.get("date", "")
            action = rating.get("action", "")
            analyst = rating.get("analyst", "")[:15]
            rate = rating.get("rating", "")
            target = rating.get("price_target", "")
            print(f"   {date} | {analyst:<15} | {action} → {rate} ({target})")
        print()

    print("=" * 70)
    print(f" \033[93mNote: Data may be 15-20 min delayed (free tier)\033[0m")
    print("=" * 70)


try:
    data = json.load(sys.stdin)

    if "error" in data:
        print(f"\033[91mError: {data['error']}\033[0m")
        sys.exit(1)

    # Detect if it's a quote or screener result
    if "stocks" in data:
        format_screener(data)
    else:
        format_quote(data)

except json.JSONDecodeError:
    print("Error: Invalid JSON input")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
