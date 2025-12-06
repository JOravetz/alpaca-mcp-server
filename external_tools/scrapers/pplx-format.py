#!/usr/bin/env python3
"""Format Perplexity Finance JSON data for terminal display."""
import sys
import json

try:
    data = json.load(sys.stdin)
    q = data.get("quote", {})
    p = data.get("profile", {})

    print("=" * 60)
    print(f" {q.get('name', 'Unknown')} ({q.get('symbol', '?')})")
    print("=" * 60)
    print()
    print(f" Price:          ${q.get('price', 0):.2f}")
    print(f" Change:         {q.get('change', 0):+.2f} ({q.get('changesPercentage', 0):+.2f}%)")
    ah = q.get("afterHoursPrice")
    if ah:
        print(f" After Hours:    ${ah:.2f} ({q.get('afterHoursPercentChange', 0):+.2f}%)")
    print()
    print(f" Day Range:      ${q.get('dayLow', 0):.2f} - ${q.get('dayHigh', 0):.2f}")
    print(f" 52W Range:      ${q.get('yearLow', 0):.2f} - ${q.get('yearHigh', 0):.2f}")
    print(f" Prev Close:     ${q.get('previousClose', 0):.2f}")
    print(f" Open:           ${q.get('open', 0):.2f}")
    print()

    mc = q.get("marketCap", 0) or 0
    if mc >= 1e12:
        mc_str = f"${mc/1e12:.2f}T"
    elif mc >= 1e9:
        mc_str = f"${mc/1e9:.2f}B"
    else:
        mc_str = f"${mc/1e6:.2f}M"

    vol = q.get("volume", 0) or 0
    if vol >= 1e6:
        vol_str = f"{vol/1e6:.1f}M"
    else:
        vol_str = f"{vol/1e3:.1f}K"

    print(f" Market Cap:     {mc_str}")
    print(f" Volume:         {vol_str}")
    pe = q.get("pe")
    print(f" P/E Ratio:      {pe:.2f}" if pe else " P/E Ratio:      N/A")
    eps = q.get("eps")
    print(f" EPS:            ${eps:.2f}" if eps else " EPS:            N/A")
    div = q.get("dividendYieldTTM")
    print(f" Div Yield:      {div*100:.2f}%" if div else " Div Yield:      N/A")
    print()

    # Profile info
    if p and not p.get("error"):
        ceo = p.get("ceo")
        if ceo:
            print(f" CEO:            {ceo}")
        sector = p.get("sector")
        if sector:
            print(f" Sector:         {sector}")
        industry = p.get("industry")
        if industry:
            print(f" Industry:       {industry}")
        employees = p.get("fullTimeEmployees")
        if employees:
            print(f" Employees:      {int(employees):,}")
        print()
        desc = p.get("description", "")
        if desc:
            print(" Description:")
            print(f"   {desc[:250]}...")

    print()
    print("=" * 60)
    mkt = "OPEN" if q.get("isMarketOpen") else "CLOSED"
    print(f" Exchange: {q.get('exchange', 'N/A')} | Market {mkt}")
    print("=" * 60)

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
