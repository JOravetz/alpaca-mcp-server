#!/bin/bash
# Quick Scan Macro - Find and analyze top opportunities
# Usage: ./macro_quick_scan.sh

echo "🔍 QUICK MARKET SCAN - $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"

echo -e "\n📊 Running Day Trading Scanner..."
uv run python -c "from alpaca_mcp_server.tools import scan_day_trading_opportunities; print(scan_day_trading_opportunities())" 2>/dev/null

echo -e "\n🚀 Running Explosive Momentum Scanner..."
uv run python -c "from alpaca_mcp_server.tools import scan_explosive_momentum; print(scan_explosive_momentum())" 2>/dev/null

echo -e "\n⚡ Running C Analyzer (High-Speed)..."
./bin/stock_analyzer_json 2>/dev/null | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('stocks'):
        print(f\"Found {len(data['stocks'])} high-activity stocks:\")
        for i, stock in enumerate(data['stocks'][:5], 1):
            print(f\"  {i}. {stock.get('symbol', 'N/A')} - {stock.get('trades_per_minute', 0):.0f} trades/min, \${stock.get('price', 0):.2f}\")
    else:
        print('No high-activity stocks found')
except:
    print('Scanner returned no data')
"

echo -e "\n✅ Scan Complete!"