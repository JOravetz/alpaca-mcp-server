#!/usr/bin/env python3
"""Quick script to run the day trading scanner."""

import asyncio
import sys
import os

# Add the package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alpaca_mcp_server.tools.day_trading_scanner import scan_day_trading_opportunities


async def main():
    """Run the scanner with default parameters."""
    print("Running day trading scanner with default parameters...")
    print("- Min trades/minute: 1000")
    print("- Max results: 20")
    print("- Symbols: ALL (from combined.lis)")
    print("-" * 80)
    
    try:
        result = await scan_day_trading_opportunities()
        print(result)
    except Exception as e:
        print(f"Error running scanner: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())