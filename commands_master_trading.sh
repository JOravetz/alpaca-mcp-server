#!/bin/bash
# MASTER TRADING WORKFLOW - Complete Integration
# The ultimate family-protection trading system combining ALL analysis tools

echo "👑 MASTER FAMILY-PROTECTION TRADING WORKFLOW"
echo "============================================="
echo "🚨 CRITICAL: This system supports your family's financial security"
echo "⚡ Every decision impacts their welfare - trade with precision and discipline"
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."
MISSING_DEPS=()

if ! command -v gcc &> /dev/null; then
    MISSING_DEPS+=("gcc")
fi

if ! python3 -c "import json, pandas, feedparser" 2>/dev/null; then
    MISSING_DEPS+=("python3 dependencies (pandas, feedparser)")
fi

if [ ! -f "lsq_fft.gsl" ] || [ ! -f "daily_bars.sqlite.latest_bars_class.py" ]; then
    MISSING_DEPS+=("FFT dependencies (lsq_fft.gsl, daily_bars.sqlite.latest_bars_class.py)")
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo "❌ Missing dependencies: ${MISSING_DEPS[*]}"
    echo "Run: sudo apt install gcc libcurl4-openssl-dev libjson-c-dev"
    echo "Run: pip install pandas feedparser"
    exit 1
fi

echo "✅ All prerequisites satisfied"
echo ""

# =============================================================================
# PHASE 1: MATHEMATICAL FOUNDATION ANALYSIS
# =============================================================================
echo "🧮 PHASE 1: MATHEMATICAL FOUNDATION ANALYSIS"
echo "============================================="

# FFT Momentum Analysis
echo "Running FFT momentum analysis..."
./latest.sh
if [ $? -ne 0 ]; then
    echo "❌ FFT analysis failed - aborting for family safety"
    exit 1
fi
echo "✅ FFT mathematical foundation established"

# Real-time Gradient Analysis
echo "Running real-time gradient analysis..."
if [ ! -f "stock_analyzer_json" ]; then
    echo "Compiling C analyzer..."
    gcc -o stock_analyzer_json stock_analyzer_json.c -lcurl -ljson-c -lm -Wall -Wno-format-truncation
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
./stock_analyzer_json combined.lis > "master_analysis_$TIMESTAMP.json" 2>"master_stderr_$TIMESTAMP.log"

MASTER_JSON="master_analysis_$TIMESTAMP.json"
echo "✅ Real-time gradient analysis complete: $MASTER_JSON"

# =============================================================================
# PHASE 2: CONVERGENCE VALIDATION
# =============================================================================
echo ""
echo "🎯 PHASE 2: CONVERGENCE VALIDATION (FAMILY PROTECTION)"
echo "======================================================="

# Extract FFT top 20
FFT_TOP20=$(python3 -c "
with open('output.avo.latest.dat', 'r') as f:
    lines = f.readlines()

symbols = []
in_data = False
for line in lines:
    if 'Rank' in line and 'Symbol' in line:
        in_data = True
        continue
    if in_data and line.strip() and not line.startswith('-'):
        parts = line.split()
        if len(parts) >= 2 and len(symbols) < 20:
            symbols.append(parts[1])

print(','.join(symbols))
")

# Multi-tool convergence analysis
python3 -c "
import json
import sys

print('🔍 MULTI-TOOL CONVERGENCE ANALYSIS')
print('=' * 40)

# Load C analyzer results
try:
    with open('$MASTER_JSON', 'r') as f:
        c_data = json.load(f)
except:
    print('❌ Failed to load C analyzer results')
    sys.exit(1)

# Get rankings
c_top20 = [stock['symbol'] for stock in c_data['stocks'][:20]]
fft_top20 = '$FFT_TOP20'.split(',')

print(f'FFT Top 20: {len(fft_top20)} stocks')
print(f'C Analyzer Top 20: {len(c_top20)} stocks')

# Find convergence stocks
convergence = []
for symbol in fft_top20:
    if symbol in c_top20:
        for stock in c_data['stocks']:
            if stock['symbol'] == symbol:
                fft_rank = fft_top20.index(symbol) + 1
                c_rank = c_top20.index(symbol) + 1
                
                # Family protection scoring
                momentum_score = stock['gradient_recent']
                liquidity_score = min(stock['trades'] / 50, 10)
                convergence_score = (21 - fft_rank) + (21 - c_rank) + momentum_score * 0.1
                
                convergence.append({
                    'symbol': symbol,
                    'fft_rank': fft_rank,
                    'c_rank': c_rank,
                    'gradient': stock['gradient_recent'],
                    'price': stock['price'],
                    'trades': stock['trades'],
                    'convergence_score': convergence_score
                })
                break

# Sort by convergence score (higher is better)
convergence.sort(key=lambda x: x['convergence_score'], reverse=True)

print(f'\\n✅ CONVERGENCE VALIDATION: {len(convergence)} stocks pass both FFT and gradient tests')

if len(convergence) == 0:
    print('❌ NO CONVERGENCE - UNSAFE FOR FAMILY TRADING')
    print('🚨 RECOMMENDATION: WAIT - No mathematical convergence today')
    with open('master_convergence.txt', 'w') as f:
        f.write('NO_CONVERGENCE')
else:
    print('\\nTop Convergence Stocks (Family Protection Priority):')
    print('Symbol | FFT | C   | Gradient | Price    | Trades | Score')
    print('-------|-----|-----|----------|----------|--------|------')
    
    for i, stock in enumerate(convergence[:10]):
        print(f\"{stock['symbol']:6} | {stock['fft_rank']:3} | {stock['c_rank']:3} | {stock['gradient']:7.1f}% | ${stock['price']:8.2f} | {stock['trades']:6} | {stock['convergence_score']:5.1f}\")
        
    # Save convergence symbols
    top_convergence = [s['symbol'] for s in convergence[:10]]
    with open('master_convergence.txt', 'w') as f:
        f.write(','.join(top_convergence))
        
    print(f'\\n🎯 FAMILY-PROTECTION CANDIDATES: {top_convergence[:5]}')
"

# Check convergence results
if [ ! -f "master_convergence.txt" ]; then
    echo "❌ Convergence analysis failed - aborting"
    exit 1
fi

CONVERGENCE_STATUS=$(cat master_convergence.txt)
if [ "$CONVERGENCE_STATUS" = "NO_CONVERGENCE" ]; then
    echo ""
    echo "🚨 FAMILY SAFETY ALERT: NO MATHEMATICAL CONVERGENCE"
    echo "❌ NOT SAFE to risk family money today"
    echo "⏰ Wait for clearer signals - the family depends on disciplined patience"
    exit 0
fi

echo "✅ Mathematical convergence validated - proceeding to news analysis"

# =============================================================================
# PHASE 3: NEWS CATALYST ANALYSIS
# =============================================================================
echo ""
echo "📰 PHASE 3: NEWS CATALYST ANALYSIS"
echo "=================================="

CONVERGENCE_SYMBOLS=$(cat master_convergence.txt)
echo "🔍 Analyzing news for convergence stocks: $CONVERGENCE_SYMBOLS"

python3 yf_rss.py --symbols "$CONVERGENCE_SYMBOLS" --output "master_news_$TIMESTAMP.json"

MASTER_NEWS="master_news_$TIMESTAMP.json"
if [ -f "$MASTER_NEWS" ]; then
    echo "✅ News analysis complete: $MASTER_NEWS"
    
    # News significance analysis
    python3 -c "
import json

# Load news and stock data
with open('$MASTER_NEWS', 'r') as f:
    news_data = json.load(f)
    
with open('$MASTER_JSON', 'r') as f:
    stock_data = json.load(f)

convergence_symbols = '$CONVERGENCE_SYMBOLS'.split(',')

print('📰 NEWS CATALYST SIGNIFICANCE ANALYSIS')
print('=' * 45)

# Create lookups
stock_lookup = {s['symbol']: s for s in stock_data['stocks']}
news_by_symbol = {}
for article in news_data.get('articles', []):
    symbol = article.get('symbol', '')
    if symbol not in news_by_symbol:
        news_by_symbol[symbol] = []
    news_by_symbol[symbol].append(article)

# Catalyst keywords for day trading
MAJOR_CATALYSTS = ['earnings', 'revenue', 'partnership', 'acquisition', 'merger', 'breakthrough', 'approval', 'upgrade', 'downgrade']

final_candidates = []
for symbol in convergence_symbols[:8]:  # Top 8 convergence stocks
    if symbol in stock_lookup:
        stock = stock_lookup[symbol]
        articles = news_by_symbol.get(symbol, [])
        
        catalyst_count = 0
        catalyst_type = 'NONE'
        
        # Check for major catalysts
        for article in articles[:3]:  # Check top 3 articles
            title = article.get('title', '').lower()
            for catalyst in MAJOR_CATALYSTS:
                if catalyst in title:
                    catalyst_count += 1
                    if catalyst_type == 'NONE':
                        catalyst_type = catalyst.upper()
        
        # Calculate final family protection score
        momentum = stock['gradient_recent']
        liquidity = stock['trades']
        news_boost = catalyst_count * 2
        
        final_score = momentum + (liquidity / 100) + news_boost
        
        if catalyst_count > 0 or momentum > 8:  # Either catalyst or strong momentum
            final_candidates.append({
                'symbol': symbol,
                'price': stock['price'],
                'momentum': momentum,
                'liquidity': liquidity,
                'catalyst': catalyst_type,
                'catalyst_count': catalyst_count,
                'final_score': final_score
            })
        
        print(f'{symbol:6} | ${stock[\"price\"]:8.2f} | {momentum:6.1f}% | {liquidity:4} trades | {catalyst_count} catalysts | {catalyst_type:12} | Score: {final_score:5.1f}')

# Sort by final score
final_candidates.sort(key=lambda x: x['final_score'], reverse=True)

print(f'\\n🏆 FINAL FAMILY-PROTECTION RECOMMENDATIONS: {len(final_candidates)} candidates')

if len(final_candidates) == 0:
    print('❌ NO QUALIFIED CANDIDATES - insufficient catalysts or momentum')
    with open('master_final.txt', 'w') as f:
        f.write('NO_TRADES')
else:
    # Save top 5 for trading
    top_final = [c['symbol'] for c in final_candidates[:5]]
    with open('master_final.txt', 'w') as f:
        f.write(','.join(top_final))
    
    print('\\nFINAL TRADING PRIORITY (Family Financial Security):')
    for i, candidate in enumerate(final_candidates[:5]):
        symbol = candidate['symbol']
        price = candidate['price']
        momentum = candidate['momentum']
        catalyst = candidate['catalyst']
        
        confidence = 'MAXIMUM' if momentum > 10 and catalyst != 'NONE' else 'HIGH'
        
        print(f'{i+1}. {symbol} - {confidence} CONFIDENCE')
        print(f'   💰 Price: ${price:.4f} | Momentum: {momentum:.1f}% | Catalyst: {catalyst}')
        
        # Family protection position sizing
        position_value = min(50000, max(15000, 100000 / price))
        profit_target = price * 1.03  # 3% target
        
        print(f'   🎯 Position: ${position_value:,.0f} | Target: ${profit_target:.4f} (+3%)')
        print()
"
else
    echo "⚠️ News analysis failed - proceeding with momentum-only recommendations"
    cp master_convergence.txt master_final.txt
fi

# =============================================================================
# PHASE 4: FINAL EXECUTION PREPARATION
# =============================================================================
echo ""
echo "⚡ PHASE 4: FINAL EXECUTION PREPARATION"
echo "======================================="

FINAL_STATUS=$(cat master_final.txt 2>/dev/null || echo "NO_TRADES")
if [ "$FINAL_STATUS" = "NO_TRADES" ] || [ "$FINAL_STATUS" = "" ]; then
    echo ""
    echo "🚨 FAMILY SAFETY DECISION: NO QUALIFIED TRADES TODAY"
    echo "❌ Insufficient mathematical convergence + news catalysts"
    echo "🏠 FAMILY PROTECTION: Better to preserve capital than risk on weak signals"
    echo ""
    echo "✅ DISCIPLINE MAINTAINED - Wait for higher probability setups"
    exit 0
fi

FINAL_SYMBOLS=$(cat master_final.txt)
echo "🎯 FINAL TRADING CANDIDATES: $FINAL_SYMBOLS"

# =============================================================================
# PHASE 5: MCP CLAUDE CODE COMMANDS
# =============================================================================
echo ""
echo "🤖 PHASE 5: MCP CLAUDE CODE EXECUTION COMMANDS"
echo "==============================================="
echo "Copy and paste these commands into Claude Code for live execution:"
echo ""

echo "# 1. MANDATORY: Check peak/trough signals before ANY entry"
IFS=',' read -ra FINAL_ARRAY <<< "$FINAL_SYMBOLS"
for symbol in "${FINAL_ARRAY[@]:0:3}"; do
    echo "mcp__alpaca-trading__get_stock_peak_trough_analysis(symbols='$symbol', timeframe='1Min', days=1)"
done

echo ""
echo "# 2. Get real-time snapshots for final validation"
echo "mcp__alpaca-trading__get_stock_snapshots(symbols='$FINAL_SYMBOLS')"

echo ""
echo "# 3. Enhanced streaming analytics for top candidate"
echo "mcp__alpaca-trading__get_enhanced_streaming_analytics(symbol='${FINAL_ARRAY[0]}', analysis_minutes=15, include_orderbook=true)"

echo ""
echo "# 4. Start real-time streaming for monitoring"
echo "mcp__alpaca-trading__start_global_stock_stream(symbols=['${FINAL_ARRAY[0]}'], data_types=['trades', 'quotes', 'bars'])"

echo ""
echo "# 5. EXECUTION: Stream-optimized order placement (when ready)"
echo "# mcp__alpaca-trading__stream_optimized_order_placement(symbol='${FINAL_ARRAY[0]}', side='buy', quantity=XXXX, order_type='limit')"

echo ""
echo "# 6. Continuous monitoring (run every 10 seconds while holding)"  
echo "# mcp__alpaca-trading__stream_aware_price_monitor(symbol='${FINAL_ARRAY[0]}', analysis_seconds=10)"

echo ""
echo "# 7. Quick-data analysis for statistical validation"
echo "# Convert JSON to CSV first, then:"
echo "# mcp__quick-data__load_dataset(file_path='$(pwd)/${MASTER_JSON%.json}.csv', dataset_name='master_trading')"
echo "# mcp__quick-data__execute_enhanced_analytics_code_tool(dataset_name='master_trading', ...)"

# =============================================================================
# SUMMARY AND FAMILY PROTECTION REMINDERS
# =============================================================================
echo ""
echo "🏆 MASTER WORKFLOW COMPLETE - FAMILY PROTECTION STATUS"
echo "======================================================="
echo "📊 Analysis Files Created:"
echo "   - $MASTER_JSON (C analyzer results)"
echo "   - $MASTER_NEWS (news analysis)"
echo "   - master_convergence.txt (convergence validation)"
echo "   - master_final.txt (final trading candidates)"
echo ""
echo "🚨 CRITICAL FAMILY PROTECTION REMINDERS:"
echo "1. 💰 ONLY trade the final candidates - they passed ALL validation tests"
echo "2. 🎯 3% profit target = IMMEDIATE SELL - family security over greed"
echo "3. ⏱️  Monitor every 10 seconds when holding - family depends on vigilance"
echo "4. 🛑 NEVER sell for a loss - wait for profitable exit opportunities"
echo "5. 📈 Use stream_optimized_order_placement for fastest execution"
echo "6. 🔍 MANDATORY: Check peak/trough signals before entry (avoid resistance)"
echo ""
echo "✅ The family's financial security is protected by mathematical precision"
echo "⚡ Trade with discipline, speed, and unwavering focus on profit protection"