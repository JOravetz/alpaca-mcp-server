#!/usr/bin/env python3
"""Format Short Squeeze scanner JSON data for terminal display."""
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


def format_number(n):
    """Format large numbers with K/M/B suffix."""
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    elif n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(int(n))


def format_short_squeeze(data):
    """Format short squeeze data for display."""
    exchange = data.get('exchange_filter', 'all')
    min_si = data.get('min_short_interest', 20)
    last_updated = data.get('last_updated', 'Unknown')
    timestamp = data.get('timestamp', '')
    stocks = data.get('stocks', [])

    # Header
    exchange_label = exchange.upper() if exchange != 'all' else 'ALL EXCHANGES'
    print("=" * 95)
    print(f" {BOLD}{MAGENTA}SHORT SQUEEZE CANDIDATES{RESET} - {exchange_label}")
    print(f" {DIM}Data from highshortinterest.com | Updated: {last_updated}{RESET}")
    print(f" {DIM}Scanned: {timestamp} | Min SI: {min_si}%{RESET}")
    print("=" * 95)
    print()

    if not stocks:
        print(f" {YELLOW}No stocks found with short interest >= {min_si}%{RESET}")
        print()
        return

    # Summary stats
    avg_si = sum(s['short_interest'] for s in stocks) / len(stocks) if stocks else 0
    max_si = max(s['short_interest'] for s in stocks) if stocks else 0

    print(f" {BOLD}Summary{RESET}")
    print("-" * 40)
    print(f"   Stocks found: {CYAN}{len(stocks)}{RESET}")
    print(f"   Avg Short Interest: {YELLOW}{avg_si:.1f}%{RESET}")
    print(f"   Max Short Interest: {RED}{max_si:.1f}%{RESET}")
    print()

    # Stocks table
    print(f" {BOLD}High Short Interest Stocks{RESET}")
    print("-" * 95)
    print(f" {'#':<3} {'TICKER':<6} {'COMPANY':<28} {'EXCH':<6} {'SI%':>7} {'FLOAT':>10} {'OUTST':>10} {'INDUSTRY':<20}")
    print("-" * 95)

    for i, stock in enumerate(stocks[:30], 1):
        ticker = stock.get('ticker', '')[:6]
        company = stock.get('company', '')[:28]
        exch = stock.get('exchange', '')[:6]
        si = stock.get('short_interest', 0)
        float_str = stock.get('float', '')[:10]
        outst = stock.get('outstanding', '')[:10]
        industry = stock.get('industry', '')[:20]

        # Color code by short interest level
        if si >= 40:
            si_color = f"{BOLD}{RED}"  # Extreme squeeze potential
            ticker_color = f"{BOLD}{MAGENTA}"
        elif si >= 30:
            si_color = RED  # High squeeze potential
            ticker_color = CYAN
        elif si >= 25:
            si_color = YELLOW  # Moderate squeeze potential
            ticker_color = RESET
        else:
            si_color = RESET
            ticker_color = RESET

        print(f" {i:<3} {ticker_color}{ticker:<6}{RESET} {company:<28} {exch:<6} {si_color}{si:>6.1f}%{RESET} {float_str:>10} {outst:>10} {industry:<20}")

    print()
    print(f" {DIM}Showing {min(len(stocks), 30)} of {len(stocks)} results{RESET}")
    print()

    # Legend
    print(f" {BOLD}Short Interest Guide:{RESET}")
    print(f"   {BOLD}{RED}40%+{RESET} = Extreme squeeze potential (high risk/reward)")
    print(f"   {RED}30-40%{RESET} = High squeeze potential")
    print(f"   {YELLOW}25-30%{RESET} = Moderate squeeze potential")
    print(f"   20-25% = Elevated short interest")
    print()
    print(f" {BOLD}Squeeze Factors:{RESET}")
    print(f"   - High SI% + Low Float = Maximum squeeze pressure")
    print(f"   - Positive catalyst + High SI% = Squeeze trigger")
    print(f"   - Watch for volume spikes indicating covering")
    print()

    print("=" * 95)
    print(f" {YELLOW}{data.get('note', 'Short interest >20% indicates high squeeze potential. Data updated weekly.')}{RESET}")
    print("=" * 95)


try:
    data = json.load(sys.stdin)

    if "error" in data:
        print(f"{RED}Error: {data['error']}{RESET}")
        sys.exit(1)

    format_short_squeeze(data)

except json.JSONDecodeError:
    print("Error: Invalid JSON input")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
