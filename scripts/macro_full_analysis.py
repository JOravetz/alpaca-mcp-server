#!/usr/bin/env python
"""
Full Stock Analysis Macro - Comprehensive analysis combining all capabilities
Usage: python macro_full_analysis.py AAPL MSFT TSLA
"""

import sys
import subprocess
import json
from datetime import datetime

def run_command(cmd):
    """Execute command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error: {str(e)}"

def analyze_stock(symbol):
    """Run complete analysis for a single stock"""
    print(f"\n{'='*60}")
    print(f"COMPREHENSIVE ANALYSIS: {symbol}")
    print(f"{'='*60}")
    
    # 1. Get current quote and snapshot
    print(f"\n📊 Market Data for {symbol}:")
    cmd = f"uv run python -c \"from alpaca_mcp_server.tools import get_stock_quote; print(get_stock_quote('{symbol}'))\""
    print(run_command(cmd))
    
    # 2. Technical Analysis - Peak/Trough
    print(f"\n📈 Technical Analysis (Peak/Trough):")
    cmd = f"uv run python -c \"from alpaca_mcp_server.tools import get_stock_peak_trough_analysis; print(get_stock_peak_trough_analysis('{symbol}', timeframe='5Min', days=1))\""
    print(run_command(cmd))
    
    # 3. Generate Plot
    print(f"\n📉 Generating Technical Plot...")
    cmd = f"uv run python plot.py -s {symbol} -t 5Min -d 1 --no-display"
    print(run_command(cmd))
    
    # 4. Get News
    print(f"\n📰 Latest News:")
    cmd = f"./external_tools/news_scrapers/yf_rss.py {symbol}"
    news_output = run_command(cmd)
    # Parse and display first 3 news items
    lines = news_output.split('\n')[:15]
    print('\n'.join(lines))
    
    # 5. Volume Analysis
    print(f"\n📊 Volume Bar Analysis:")
    cmd = f"uv run python -c \"from alpaca_mcp_server.tools import get_volume_bars_from_history; print(get_volume_bars_from_history('{symbol}', days=1))\""
    print(run_command(cmd)[:500] + "...")  # Truncate for readability

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python macro_full_analysis.py SYMBOL1 [SYMBOL2 ...]")
        print("Example: python macro_full_analysis.py AAPL MSFT TSLA")
        sys.exit(1)
    
    symbols = sys.argv[1:]
    print(f"🚀 Starting Comprehensive Analysis")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Symbols: {', '.join(symbols)}")
    
    for symbol in symbols:
        analyze_stock(symbol.upper())
    
    print(f"\n{'='*60}")
    print("✅ Analysis Complete!")