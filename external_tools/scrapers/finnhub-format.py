#!/usr/bin/env python3
"""Format Finnhub real-time data for terminal display."""
import sys
import json

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def format_price(price):
    """Format price with appropriate precision."""
    if price is None:
        return "N/A"
    if price >= 1000:
        return f"${price:,.0f}"
    elif price >= 100:
        return f"${price:.2f}"
    elif price >= 1:
        return f"${price:.2f}"
    else:
        return f"${price:.4f}"


def format_change(change, change_pct):
    """Format change with color coding."""
    if change is None or change_pct is None:
        return f"{DIM}N/A{RESET}"

    if change > 0:
        return f"{GREEN}+{change:.2f} (+{change_pct:.2f}%){RESET}"
    elif change < 0:
        return f"{RED}{change:.2f} ({change_pct:.2f}%){RESET}"
    else:
        return f"{DIM}0.00 (0.00%){RESET}"


def format_number(n):
    """Format large numbers with K/M/B suffix."""
    if n is None:
        return "N/A"
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    elif n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(int(n))


def format_quote(data):
    """Format single quote data."""
    symbol = data.get('symbol', '')
    timestamp = data.get('timestamp', '')
    quote = data.get('quote', {})

    print("=" * 60)
    print(f" {BOLD}{CYAN}FINNHUB REAL-TIME QUOTE{RESET} - {BOLD}{symbol}{RESET}")
    print(f" {DIM}{timestamp}{RESET}")
    print("=" * 60)
    print()

    current = quote.get('current', 0)
    change = quote.get('change', 0)
    change_pct = quote.get('change_percent', 0)

    # Large price display
    print(f" {BOLD}Current Price:{RESET}")
    price_color = GREEN if change > 0 else RED if change < 0 else RESET
    print(f"   {price_color}{BOLD}{format_price(current)}{RESET}")
    print(f"   {format_change(change, change_pct)}")
    print()

    # Day range
    print(f" {BOLD}Today's Range:{RESET}")
    print(f"   Low:  {format_price(quote.get('low'))}")
    print(f"   High: {format_price(quote.get('high'))}")
    print(f"   Open: {format_price(quote.get('open'))}")
    print()

    # Previous close
    print(f" {BOLD}Previous Close:{RESET} {format_price(quote.get('previous_close'))}")
    print()

    print("=" * 60)
    print(f" {DIM}Source: finnhub.io | Data may be delayed 15 minutes{RESET}")
    print("=" * 60)


def format_multi_quotes(data):
    """Format multiple quotes."""
    timestamp = data.get('timestamp', '')
    quotes = data.get('quotes', [])
    errors = data.get('errors', [])

    print("=" * 80)
    print(f" {BOLD}{CYAN}FINNHUB MULTI-QUOTE SCANNER{RESET}")
    print(f" {DIM}{timestamp}{RESET}")
    print("=" * 80)
    print()

    if not quotes:
        print(f" {YELLOW}No quotes available{RESET}")
        if errors:
            print(f" {RED}Errors: {len(errors)} symbols failed{RESET}")
        print()
        return

    # Summary
    gainers = [q for q in quotes if q.get('change_percent', 0) > 0]
    losers = [q for q in quotes if q.get('change_percent', 0) < 0]

    print(f" {BOLD}Summary{RESET}")
    print("-" * 40)
    print(f"   Total: {len(quotes)} symbols")
    print(f"   {GREEN}Gainers: {len(gainers)}{RESET}")
    print(f"   {RED}Losers: {len(losers)}{RESET}")
    print()

    # Quotes table
    print(f" {BOLD}Real-Time Quotes (sorted by % change){RESET}")
    print("-" * 80)
    print(f" {'SYMBOL':<8} {'CURRENT':>10} {'CHANGE':>10} {'CHANGE%':>10} {'HIGH':>10} {'LOW':>10} {'OPEN':>10}")
    print("-" * 80)

    for q in quotes:
        symbol = q.get('symbol', '')[:8]
        current = q.get('current', 0)
        change = q.get('change', 0)
        change_pct = q.get('change_percent', 0)
        high = q.get('high', 0)
        low = q.get('low', 0)
        open_p = q.get('open', 0)

        # Color coding
        if change_pct > 5:
            row_color = f"{BOLD}{GREEN}"
        elif change_pct > 0:
            row_color = GREEN
        elif change_pct < -5:
            row_color = f"{BOLD}{RED}"
        elif change_pct < 0:
            row_color = RED
        else:
            row_color = RESET

        change_str = f"+{change:.2f}" if change > 0 else f"{change:.2f}"
        pct_str = f"+{change_pct:.2f}%" if change_pct > 0 else f"{change_pct:.2f}%"

        print(f" {row_color}{symbol:<8}{RESET} {format_price(current):>10} {change_str:>10} {pct_str:>10} {format_price(high):>10} {format_price(low):>10} {format_price(open_p):>10}")

    print()

    if errors:
        print(f" {YELLOW}Failed symbols:{RESET} {', '.join(e['symbol'] for e in errors)}")
        print()

    print("=" * 80)
    print(f" {DIM}Source: finnhub.io | Data may be delayed 15 minutes{RESET}")
    print("=" * 80)


def format_news(data):
    """Format company or market news."""
    mode = data.get('mode', 'news')
    symbol = data.get('symbol', '')
    category = data.get('category', '')
    timestamp = data.get('timestamp', '')
    date_range = data.get('date_range', '')
    articles = data.get('articles', [])

    print("=" * 90)
    if mode == "news":
        print(f" {BOLD}{MAGENTA}FINNHUB NEWS{RESET} - {BOLD}{symbol}{RESET}")
    else:
        print(f" {BOLD}{MAGENTA}FINNHUB MARKET NEWS{RESET} - {category.upper()}")
    print(f" {DIM}{timestamp} | Range: {date_range}{RESET}")
    print("=" * 90)
    print()

    if not articles:
        print(f" {YELLOW}No news articles found{RESET}")
        print()
        return

    print(f" {BOLD}Latest Headlines ({len(articles)} articles){RESET}")
    print("-" * 90)
    print()

    for i, article in enumerate(articles[:15], 1):
        headline = article.get('headline', '')[:80]
        source = article.get('source', '')[:15]
        dt = article.get('datetime', '')
        summary = article.get('summary', '')[:200]
        url = article.get('url', '')

        # Highlight keywords
        headline_display = headline
        for keyword in ['surge', 'soar', 'jump', 'rally', 'gain', 'up', 'rise', 'high']:
            if keyword.lower() in headline.lower():
                headline_display = f"{GREEN}{headline}{RESET}"
                break
        for keyword in ['crash', 'plunge', 'drop', 'fall', 'down', 'low', 'sink', 'tumble']:
            if keyword.lower() in headline.lower():
                headline_display = f"{RED}{headline}{RESET}"
                break

        print(f" {CYAN}{i:2}.{RESET} {headline_display}")
        print(f"     {DIM}[{source}] {dt}{RESET}")
        if summary:
            print(f"     {DIM}{summary}...{RESET}")
        print()

    print("-" * 90)
    print(f" {DIM}Tip: Use --json for full article URLs and metadata{RESET}")
    print("=" * 90)


def format_earnings(data):
    """Format earnings calendar."""
    timestamp = data.get('timestamp', '')
    date_range = data.get('date_range', '')
    earnings = data.get('earnings', [])
    note = data.get('note', '')

    print("=" * 100)
    print(f" {BOLD}{YELLOW}FINNHUB EARNINGS CALENDAR{RESET}")
    print(f" {DIM}{timestamp} | Range: {date_range}{RESET}")
    print("=" * 100)
    print()

    if not earnings:
        print(f" {YELLOW}No earnings announcements in this date range{RESET}")
        print()
        return

    # Group by date
    by_date = {}
    for e in earnings:
        date = e.get('date', 'Unknown')
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(e)

    print(f" {BOLD}Upcoming Earnings ({len(earnings)} companies){RESET}")
    print("-" * 100)
    print(f" {'DATE':<12} {'SYMBOL':<8} {'TIME':<6} {'Q':<4} {'EPS EST':>10} {'EPS ACT':>10} {'SURPRISE':>10} {'REV EST':>12}")
    print("-" * 100)

    for date in sorted(by_date.keys()):
        for e in by_date[date]:
            symbol = e.get('symbol', '')[:8]
            hour = e.get('hour', '')[:6]
            quarter = f"Q{e.get('quarter', '?')}" if e.get('quarter') else ""
            eps_est = e.get('eps_estimate')
            eps_act = e.get('eps_actual')
            eps_surprise = e.get('eps_surprise')
            rev_est = e.get('revenue_estimate')

            # Format hour nicely
            hour_display = {
                'bmo': 'BMO',   # Before Market Open
                'amc': 'AMC',   # After Market Close
                'dmh': 'DMH',   # During Market Hours
            }.get(hour.lower(), hour.upper())

            # Format values
            eps_est_str = f"${eps_est:.2f}" if eps_est is not None else "-"
            eps_act_str = f"${eps_act:.2f}" if eps_act is not None else "-"
            rev_est_str = format_number(rev_est) if rev_est else "-"

            # Color surprise
            if eps_surprise is not None:
                if eps_surprise > 0:
                    surprise_str = f"{GREEN}+${eps_surprise:.2f}{RESET}"
                elif eps_surprise < 0:
                    surprise_str = f"{RED}${eps_surprise:.2f}{RESET}"
                else:
                    surprise_str = "$0.00"
            else:
                surprise_str = "-"

            print(f" {date:<12} {CYAN}{symbol:<8}{RESET} {hour_display:<6} {quarter:<4} {eps_est_str:>10} {eps_act_str:>10} {surprise_str:>10} {rev_est_str:>12}")

    print()
    print(f" {BOLD}Legend:{RESET}")
    print(f"   BMO = Before Market Open (pre-market)")
    print(f"   AMC = After Market Close (after-hours)")
    print(f"   DMH = During Market Hours")
    print()
    print(f" {BOLD}Trading Tips:{RESET}")
    print(f"   - {GREEN}Positive surprise{RESET} often triggers momentum")
    print(f"   - Watch for high IV crush after earnings")
    print(f"   - Consider straddles/strangles before announcement")
    print()

    print("=" * 100)
    print(f" {DIM}Source: finnhub.io{RESET}")
    print("=" * 100)


try:
    data = json.load(sys.stdin)

    if "error" in data:
        print(f"{RED}Error: {data['error']}{RESET}")
        sys.exit(1)

    mode = data.get('mode', '')

    if mode == "quote":
        format_quote(data)
    elif mode == "multi":
        format_multi_quotes(data)
    elif mode in ["news", "market-news"]:
        format_news(data)
    elif mode == "earnings":
        format_earnings(data)
    else:
        # Unknown mode, just pretty print JSON
        print(json.dumps(data, indent=2))

except json.JSONDecodeError:
    print("Error: Invalid JSON input")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
