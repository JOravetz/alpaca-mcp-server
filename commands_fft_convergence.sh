#!/bin/bash
# FFT Analysis + Multi-Tool Convergence Workflow
# The ultimate family-protection trading system with mathematical validation

echo "🧮 FAMILY-PROTECTION TRADING: FFT + MULTI-TOOL CONVERGENCE"
echo "==========================================================="

# Step 1: Run FFT momentum analysis
echo "Step 1: Running FFT momentum analysis (latest.sh)..."
./latest.sh

if [ $? -eq 0 ]; then
    echo "✅ FFT analysis complete"
    LATEST_FFT=$(ls -t output.avo.*.dat | head -1)
    echo "📊 FFT results: $LATEST_FFT"
else
    echo "❌ FFT analysis failed - check dependencies"
    exit 1
fi

# Step 2: Extract top 20 FFT rankings
echo -e "\nStep 2: Extracting top 20 FFT momentum leaders..."
FFT_TOP20=$(python3 -c "
import re

# Read the latest FFT output
with open('output.avo.latest.dat', 'r') as f:
    lines = f.readlines()

# Find the data section (skip headers)
data_lines = []
in_data = False
for line in lines:
    if 'Rank' in line and 'Symbol' in line:
        in_data = True
        continue
    if in_data and line.strip() and not line.startswith('-'):
        data_lines.append(line.strip())

# Extract top 20 symbols
symbols = []
for i, line in enumerate(data_lines[:20]):
    if i >= 20:
        break
    parts = line.split()
    if len(parts) >= 2:
        symbols.append(parts[1])  # Symbol is second column

print(','.join(symbols))
")

echo "✅ Top 20 FFT momentum stocks: $FFT_TOP20"

# Step 3: Run C analyzer on same universe
echo -e "\nStep 3: Running real-time C analyzer for convergence validation..."
./stock_analyzer_json combined.lis > fft_convergence_analysis_$(date +%Y%m%d_%H%M%S).json 2>fft_convergence_stderr_$(date +%Y%m%d_%H%M%S).log

CONVERGENCE_JSON=$(ls -t fft_convergence_analysis_*.json | head -1)
echo "✅ C analyzer complete: $CONVERGENCE_JSON"

# Step 4: Convergence analysis - find stocks that appear in both FFT and C analyzer top ranks
echo -e "\nStep 4: Multi-tool convergence analysis..."
python3 -c "
import json

# Load C analyzer results
with open('$CONVERGENCE_JSON', 'r') as f:
    c_data = json.load(f)

# Get top 20 symbols from C analyzer
c_top20 = [stock['symbol'] for stock in c_data['stocks'][:20]]

# FFT top 20 symbols
fft_top20 = '$FFT_TOP20'.split(',')

# Find convergence
convergence_stocks = []
for symbol in fft_top20:
    if symbol in c_top20:
        # Get detailed data from C analyzer
        for stock in c_data['stocks']:
            if stock['symbol'] == symbol:
                fft_rank = fft_top20.index(symbol) + 1
                c_rank = c_top20.index(symbol) + 1
                convergence_stocks.append({
                    'symbol': symbol,
                    'fft_rank': fft_rank,
                    'c_rank': c_rank,
                    'gradient': stock['gradient_recent'],
                    'price': stock['price'],
                    'trades': stock['trades']
                })
                break

# Sort by combined ranking strength (lower is better)
convergence_stocks.sort(key=lambda x: x['fft_rank'] + x['c_rank'])

print('🎯 MULTI-TOOL CONVERGENCE ANALYSIS (HIGHEST CONFIDENCE TRADES)')
print('=' * 70)
print('Only stocks validated by BOTH FFT mathematics AND real-time gradients')
print()
print('Symbol | FFT Rank | C Rank | Combined | Gradient | Price    | Trades')
print('-------|----------|--------|----------|----------|----------|--------')

for stock in convergence_stocks[:10]:
    combined_rank = stock['fft_rank'] + stock['c_rank']
    print(f\"{stock['symbol']:6} | {stock['fft_rank']:8} | {stock['c_rank']:6} | {combined_rank:8} | {stock['gradient']:7.1f}% | ${stock['price']:8.2f} | {stock['trades']:6}\")
    
if len(convergence_stocks) == 0:
    print('❌ NO CONVERGENCE FOUND - Market conditions may be unstable')
    print('   Wait for clearer signals before family-risking trades')
else:
    print(f'\\n✅ CONVERGENCE FOUND: {len(convergence_stocks)} stocks validated by both systems')
    print('🚀 These are the HIGHEST CONFIDENCE opportunities for family-protection trading')

# Export convergence symbols for news analysis
if convergence_stocks:
    convergence_symbols = [s['symbol'] for s in convergence_stocks[:10]]
    with open('convergence_symbols.txt', 'w') as f:
        f.write(','.join(convergence_symbols))
    print(f'\\n📁 Convergence symbols saved to: convergence_symbols.txt')
"

# Step 5: Fetch RSS news for convergence stocks only
echo -e "\nStep 5: Fetching news for convergence stocks (highest confidence)..."
if [ -f "convergence_symbols.txt" ]; then
    CONVERGENCE_SYMBOLS=$(cat convergence_symbols.txt)
    echo "🔍 Analyzing news for: $CONVERGENCE_SYMBOLS"
    
    python3 yf_rss.py --symbols "$CONVERGENCE_SYMBOLS" --output "convergence_news_$(date +%Y%m%d_%H%M%S).json"
    
    CONVERGENCE_NEWS=$(ls -t convergence_news_*.json | head -1)
    if [ -f "$CONVERGENCE_NEWS" ]; then
        echo "✅ Convergence news analysis: $CONVERGENCE_NEWS"
    fi
else
    echo "⚠️ No convergence stocks found - skipping news analysis"
fi

# Step 6: Final family-protection trading recommendations
echo -e "\nStep 6: Final family-protection trading recommendations..."
python3 -c "
import json

# Load convergence analysis
with open('$CONVERGENCE_JSON', 'r') as f:
    data = json.load(f)

try:
    with open('convergence_symbols.txt', 'r') as f:
        convergence_symbols = f.read().strip().split(',')
except:
    convergence_symbols = []

if not convergence_symbols:
    print('❌ NO CONVERGENCE STOCKS - NOT SAFE FOR FAMILY TRADING TODAY')
    print('🚨 RECOMMENDATION: WAIT for clearer mathematical signals')
    print('   The family depends on high-confidence trades only')
    exit()

print('🏆 FINAL FAMILY-PROTECTION TRADING RECOMMENDATIONS')
print('=' * 55)
print('⚠️ CRITICAL: These are the ONLY stocks validated by multiple systems')
print()

# Get detailed analysis for convergence stocks
for i, symbol in enumerate(convergence_symbols[:5]):
    for stock in data['stocks']:
        if stock['symbol'] == symbol:
            gradient = stock['gradient_recent'] 
            price = stock['price']
            trades = stock['trades']
            
            # Family protection rules
            position_size = min(50000, max(10000, 100000 / price))  # $10K-$50K position
            profit_target = price * 1.03  # 3% profit target
            stop_loss = price * 0.98      # 2% stop loss
            
            confidence = 'MAXIMUM' if gradient > 10 and trades > 200 else 'HIGH'
            
            print(f'{i+1}. {symbol} - {confidence} CONFIDENCE')
            print(f'   💰 Entry: \${price:.4f} | Target: \${profit_target:.4f} | Stop: \${stop_loss:.4f}')
            print(f'   📊 Gradient: {gradient:.1f}% | Trades: {trades} | Position: {position_size:,.0f} shares')
            
            if i == 0:
                print(f'   🎯 #1 FAMILY-PROTECTION CANDIDATE')
            print()
            break

print('🚨 FAMILY TRADING EXECUTION RULES:')
print('1. Use stream_optimized_order_placement MCP tool for entries')
print('2. Monitor positions every 10 seconds - family depends on vigilance') 
print('3. SELL at 3% profit target - no exceptions for family security')
print('4. NEVER let profits evaporate - remember the BIYA lesson (\$19K → \$2K)')
print('5. If no convergence stocks, DO NOT TRADE - wait for better signals')
"

# Step 7: MCP commands for live execution
echo -e "\nStep 7: MCP COMMANDS FOR CLAUDE CODE (LIVE TRADING):"
echo "=================================================="
if [ -f "convergence_symbols.txt" ]; then
    CONVERGENCE_SYMBOLS=$(cat convergence_symbols.txt)
    echo "# Get real-time snapshots for convergence validation"
    echo "mcp__alpaca-trading__get_stock_snapshots(symbols='$CONVERGENCE_SYMBOLS')"
    echo ""
    echo "# Check peak/trough signals before entry (MANDATORY)"
    IFS=',' read -ra SYMBOLS_ARRAY <<< "$CONVERGENCE_SYMBOLS"
    for symbol in "${SYMBOLS_ARRAY[@]:0:3}"; do
        echo "mcp__alpaca-trading__get_stock_peak_trough_analysis(symbols='$symbol', timeframe='1Min', days=1)"
    done
    echo ""
    echo "# Start streaming for top candidate"
    echo "mcp__alpaca-trading__start_global_stock_stream(symbols=['${SYMBOLS_ARRAY[0]}'], data_types=['trades', 'quotes'])"
    echo "mcp__alpaca-trading__stream_aware_price_monitor(symbol='${SYMBOLS_ARRAY[0]}', analysis_seconds=10)"
fi

echo -e "\n✅ FFT + Multi-tool convergence workflow complete!"
echo "📁 Files created:"
echo "   - $CONVERGENCE_JSON (C analyzer results)"
if [ -f "convergence_symbols.txt" ]; then
    echo "   - convergence_symbols.txt (highest confidence stocks)"
fi
if [ -f "$CONVERGENCE_NEWS" ]; then
    echo "   - $CONVERGENCE_NEWS (news for convergence stocks)"
fi
echo -e "\n🎯 FAMILY PROTECTION STATUS:"
if [ -f "convergence_symbols.txt" ] && [ -s "convergence_symbols.txt" ]; then
    echo "✅ CONVERGENCE VALIDATED - Safe to proceed with family-protection trading"
else
    echo "❌ NO CONVERGENCE - NOT SAFE for family-risking trades today"
fi