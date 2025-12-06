#!/usr/bin/env python3
"""Format Barchart options flow JSON data for terminal display."""
import sys
import json

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def format_number(n):
    """Format large numbers with K/M suffix."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def format_options_flow(data):
    """Format options flow data for display."""
    mode = data.get('mode', 'active')
    ticker = data.get('ticker', '')
    timestamp = data.get('timestamp', '')
    sentiment = data.get('sentiment', {})
    options = data.get('options', [])

    # Header
    mode_labels = {
        'active': 'MOST ACTIVE',
        'unusual': 'UNUSUAL ACTIVITY',
        'calls': 'ACTIVE CALLS',
        'puts': 'ACTIVE PUTS',
        'volume': 'BY VOLUME',
        'symbol': f'{ticker} OPTIONS'
    }

    print("=" * 85)
    print(f" {BOLD}BARCHART OPTIONS FLOW - {mode_labels.get(mode, mode.upper())}{RESET}")
    print(f" {DIM}{timestamp}{RESET}")
    print("=" * 85)
    print()

    if not options:
        print(f" {YELLOW}No options data available. Market may be closed.{RESET}")
        print()
        return

    # Sentiment summary
    call_vol = sentiment.get('call_volume', 0)
    put_vol = sentiment.get('put_volume', 0)
    pc_ratio = sentiment.get('put_call_ratio', 0)

    print(f" {BOLD}Sentiment Summary{RESET}")
    print("-" * 40)

    # Put/Call ratio interpretation
    if pc_ratio < 0.7:
        sentiment_color = GREEN
        sentiment_text = "BULLISH (low P/C)"
    elif pc_ratio > 1.0:
        sentiment_color = RED
        sentiment_text = "BEARISH (high P/C)"
    else:
        sentiment_color = YELLOW
        sentiment_text = "NEUTRAL"

    print(f"   {GREEN}Call Volume:{RESET} {format_number(call_vol):>10}")
    print(f"   {RED}Put Volume:{RESET}  {format_number(put_vol):>10}")
    print(f"   Put/Call Ratio: {sentiment_color}{pc_ratio:.2f}{RESET} ({sentiment_text})")
    print()

    # Options table
    print(f" {BOLD}Options Flow{RESET}")
    print("-" * 85)
    print(f" {'SYM':<5} {'TYPE':<4} {'STRIKE':>8} {'EXP':>10} {'DTE':>4} {'LAST':>7} {'BID':>7} {'ASK':>7} {'VOL':>8} {'OI':>8} {'V/OI':>6}")
    print("-" * 85)

    for opt in options[:25]:
        symbol = opt.get('symbol', '')[:5]
        opt_type = opt.get('type', '')[:4]
        strike = opt.get('strike', 0)
        exp = opt.get('expiration', '')[:10]
        dte = opt.get('days_to_exp', 0)
        last = opt.get('last', 0)
        bid = opt.get('bid', 0)
        ask = opt.get('ask', 0)
        vol = opt.get('volume', 0)
        oi = opt.get('open_interest', 0)
        vol_oi = opt.get('vol_oi_ratio', 0)

        # Color code by type
        if opt_type == 'Call':
            type_color = GREEN
        else:
            type_color = RED

        # Highlight unusual activity
        vol_oi_color = RESET
        if vol_oi >= 3.0:
            vol_oi_color = f"{BOLD}{CYAN}"  # Very unusual
        elif vol_oi >= 1.5:
            vol_oi_color = CYAN  # Unusual

        # Format values
        strike_str = f"${strike:.0f}" if strike >= 10 else f"${strike:.2f}"
        last_str = f"${last:.2f}" if last < 100 else f"${last:.0f}"
        bid_str = f"${bid:.2f}" if bid < 100 else f"${bid:.0f}"
        ask_str = f"${ask:.2f}" if ask < 100 else f"${ask:.0f}"

        print(f" {symbol:<5} {type_color}{opt_type:<4}{RESET} {strike_str:>8} {exp:>10} {dte:>4} {last_str:>7} {bid_str:>7} {ask_str:>7} {format_number(vol):>8} {format_number(oi):>8} {vol_oi_color}{vol_oi:.1f}{RESET}")

    print()
    print(f" {DIM}Showing {min(len(options), 25)} of {len(options)} results{RESET}")
    print()

    # Legend
    print(f" {BOLD}Legend:{RESET}")
    print(f"   {GREEN}Call{RESET} = Bullish bet  |  {RED}Put{RESET} = Bearish bet")
    print(f"   {CYAN}V/OI > 1.5{RESET} = Unusual activity (potential smart money)")
    print(f"   {BOLD}{CYAN}V/OI > 3.0{RESET} = Very unusual (strong signal)")
    print()

    print("=" * 85)
    print(f" {YELLOW}{data.get('note', 'Data may be delayed')}{RESET}")
    print("=" * 85)


try:
    data = json.load(sys.stdin)

    if "error" in data:
        print(f"{RED}Error: {data['error']}{RESET}")
        sys.exit(1)

    format_options_flow(data)

except json.JSONDecodeError:
    print("Error: Invalid JSON input")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
