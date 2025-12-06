#!/usr/bin/env python3
"""Format Stocktwits JSON data for terminal display."""
import sys
import json

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def format_trending(data):
    """Format trending symbols for display."""
    print("=" * 70)
    print(f" {BOLD}STOCKTWITS TRENDING{RESET} - {data.get('timestamp', '')}")
    print("=" * 70)
    print()

    symbols = data.get("symbols", [])
    if not symbols:
        print(" No trending symbols found.")
        return

    # Header
    print(f" {'#':<3} {'TICKER':<8} {'COMPANY':<35} {'SCORE':>8} {'WATCHERS':>10}")
    print("-" * 70)

    for i, sym in enumerate(symbols[:20], 1):
        ticker = sym.get("ticker", "")[:8]
        title = sym.get("title", "")[:35]
        score = sym.get("trending_score")
        watchers = sym.get("watchlist_count", 0)

        # Format score with color
        if score:
            score_str = f"{score:.2f}"
            if score > 5:
                score_display = f"{GREEN}{score_str}{RESET}"
            else:
                score_display = score_str
        else:
            score_display = "-"

        # Format watchers
        if watchers >= 100000:
            watchers_str = f"{watchers/1000:.0f}K"
        elif watchers >= 1000:
            watchers_str = f"{watchers/1000:.1f}K"
        else:
            watchers_str = str(watchers)

        print(f" {i:<3} {ticker:<8} {title:<35} {score_display:>8} {watchers_str:>10}")

    print()
    print(f" {YELLOW}Tip: Use --symbol TICKER for detailed sentiment analysis{RESET}")
    print("=" * 70)


def format_symbol(data):
    """Format symbol sentiment analysis for display."""
    ticker = data.get("ticker", "UNKNOWN")
    title = data.get("title", "Unknown Company")
    sentiment = data.get("sentiment_summary", {})

    print("=" * 70)
    print(f" {BOLD}{title} ({ticker}){RESET}")
    print("=" * 70)
    print()

    # Sentiment summary
    print(f" {BOLD}Sentiment Analysis{RESET}")
    print("-" * 35)

    bullish = sentiment.get("bullish", 0)
    bearish = sentiment.get("bearish", 0)
    neutral = sentiment.get("neutral", 0)
    total = sentiment.get("total", 0)
    score = sentiment.get("sentiment_score", 0)

    # Sentiment score with color
    if score > 20:
        score_color = GREEN
        mood = "BULLISH"
    elif score < -20:
        score_color = RED
        mood = "BEARISH"
    else:
        score_color = YELLOW
        mood = "NEUTRAL"

    print(f"   Overall Mood:   {score_color}{BOLD}{mood}{RESET}")
    print(f"   Sentiment Score: {score_color}{score:+.1f}%{RESET}")
    print()
    print(f"   {GREEN}Bullish:{RESET}  {bullish:3d} ({sentiment.get('bullish_pct', 0):.1f}%)")
    print(f"   {RED}Bearish:{RESET}  {bearish:3d} ({sentiment.get('bearish_pct', 0):.1f}%)")
    print(f"   {YELLOW}Neutral:{RESET}  {neutral:3d}")
    print(f"   Total:     {total:3d} messages analyzed")
    print()

    # Visual bar
    if total > 0:
        bar_width = 40
        bull_chars = int(bullish / total * bar_width)
        bear_chars = int(bearish / total * bar_width)
        neut_chars = bar_width - bull_chars - bear_chars

        bar = f"{GREEN}{'█' * bull_chars}{RESET}{YELLOW}{'█' * neut_chars}{RESET}{RED}{'█' * bear_chars}{RESET}"
        print(f"   [{bar}]")
        print()

    # Watchlist count
    watchers = data.get("watchlist_count", 0)
    if watchers >= 100000:
        watchers_str = f"{watchers/1000:.0f}K"
    elif watchers >= 1000:
        watchers_str = f"{watchers/1000:.1f}K"
    else:
        watchers_str = str(watchers)
    print(f"   Watchlist: {CYAN}{watchers_str}{RESET} traders watching")
    print()

    # Recent messages
    messages = data.get("messages", [])
    if messages:
        print(f" {BOLD}Recent Messages{RESET}")
        print("-" * 35)

        for msg in messages[:10]:
            # Sentiment indicator
            sent = msg.get("sentiment")
            if sent == "Bullish":
                sent_icon = f"{GREEN}▲{RESET}"
            elif sent == "Bearish":
                sent_icon = f"{RED}▼{RESET}"
            else:
                sent_icon = f"{YELLOW}●{RESET}"

            user = msg.get("user", "anon")[:12]
            followers = msg.get("followers", 0)
            body = msg.get("body", "")[:60].replace("\n", " ")
            likes = msg.get("likes", 0)

            # User credibility indicator (based on followers)
            if followers >= 10000:
                cred = f"{CYAN}★{RESET}"
            elif followers >= 1000:
                cred = f"{BLUE}●{RESET}"
            else:
                cred = " "

            print(f"   {sent_icon}{cred} @{user:<12} {body}...")
            if likes > 0:
                print(f"      {YELLOW}♥ {likes}{RESET}")

        print()

    print("=" * 70)
    print(f" {YELLOW}Data from Stocktwits social sentiment API{RESET}")
    print("=" * 70)


try:
    data = json.load(sys.stdin)

    if "error" in data:
        print(f"{RED}Error: {data['error']}{RESET}")
        sys.exit(1)

    mode = data.get("mode", "")

    if mode == "trending":
        format_trending(data)
    elif mode == "symbol":
        format_symbol(data)
    else:
        # Unknown mode, just pretty print
        print(json.dumps(data, indent=2))

except json.JSONDecodeError:
    print("Error: Invalid JSON input")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
