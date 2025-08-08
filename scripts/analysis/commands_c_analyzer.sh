#!/bin/bash
# C Analyzer + Quick-Data MCP Analysis Workflow
# Provides real-time gradient analysis with advanced statistical validation

echo "🔥 FAMILY-PROTECTION TRADING: C ANALYZER + MCP ANALYSIS"
echo "======================================================="

# Step 1: Compile C analyzer with buffer safety
echo "Step 1: Compiling stock_analyzer_json.c..."
gcc -o stock_analyzer_json stock_analyzer_json.c -lcurl -ljson-c -lm -Wall -Wno-format-truncation
if [ $? -eq 0 ]; then
    echo "✅ C analyzer compiled successfully"
else
    echo "❌ Compilation failed - check dependencies (libcurl, libjson-c)"
    exit 1
fi

# Step 2: Run real-time gradient analysis
echo -e "\nStep 2: Running real-time gradient analysis on $(wc -l < combined.lis) stocks..."
./stock_analyzer_json combined.lis > real_time_analysis_$(date +%Y%m%d_%H%M%S).json 2>analyzer_stderr_$(date +%Y%m%d_%H%M%S).log

# Check if analysis was successful
LATEST_JSON=$(ls -t real_time_analysis_*.json | head -1)
if [ -f "$LATEST_JSON" ]; then
    echo "✅ Analysis complete: $LATEST_JSON"
    PROCESSED_STOCKS=$(grep '"total_processed"' "$LATEST_JSON" | grep -o '[0-9]\+')
    RESULT_COUNT=$(grep '"results_count"' "$LATEST_JSON" | grep -o '[0-9]\+')
    echo "📊 Processed: $PROCESSED_STOCKS stocks → Top $RESULT_COUNT active candidates"
else
    echo "❌ Analysis failed - check analyzer_stderr log"
    exit 1
fi

# Step 3: Convert to CSV for MCP analysis
echo -e "\nStep 3: Converting to CSV for advanced analytics..."
python3 -c "
import json
import pandas as pd
import sys

try:
    with open('$LATEST_JSON', 'r') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data['stocks'])
    csv_file = '${LATEST_JSON%.json}.csv'
    df.to_csv(csv_file, index=False)
    print(f'✅ CSV created: {csv_file}')
    print(f'📊 Dataset shape: {df.shape}')
    print(f'🔍 Columns: {list(df.columns)}')
except Exception as e:
    print(f'❌ Conversion failed: {e}', file=sys.stderr)
    sys.exit(1)
"

# Step 4: Load into quick-data MCP for advanced analysis
echo -e "\nStep 4: Loading into quick-data MCP for statistical analysis..."
CSV_FILE="${LATEST_JSON%.json}.csv"

# Note: These commands would be run in Claude Code with MCP connection
echo "🤖 MCP COMMANDS FOR CLAUDE CODE:"
echo "================================"
echo "mcp__quick-data__load_dataset(file_path='$(pwd)/$CSV_FILE', dataset_name='live_stocks')"
echo "mcp__quick-data__suggest_analysis(dataset_name='live_stocks')"
echo "mcp__quick-data__find_correlations(dataset_name='live_stocks', threshold=0.3)"
echo "mcp__quick-data__detect_outliers(dataset_name='live_stocks', method='iqr')"

# Step 5: Advanced trading analysis
echo -e "\nmcp__quick-data__execute_enhanced_analytics_code_tool(dataset_name='live_stocks', python_code='"'
print("🎯 FAMILY-PROTECTION TRADING ANALYSIS")
print("="*50)

# 1. MOMENTUM LEADERS
momentum_leaders = df.nlargest(5, "gradient_recent")[["symbol", "price", "gradient_recent", "gradient_change", "trades"]].round(2)
print("\n💰 TOP MOMENTUM OPPORTUNITIES:")
for idx, row in momentum_leaders.iterrows():
    status = "🚀 ACCELERATING" if row["gradient_change"] > 0 else "⚠️ DECELERATING"
    print(f"{row['symbol']:6} | ${row['price']:8.2f} | {row['gradient_recent']:6.1f}% gradient | {status}")

# 2. TRADING SCORE (Momentum + Liquidity)
df["trading_score"] = (
    df["gradient_recent"] * 0.4 +
    df["gradient_change"] * 0.3 + 
    np.log10(df["trades"]) * 10
)
top_candidates = df.nlargest(5, "trading_score")[["symbol", "price", "gradient_recent", "trades", "trading_score"]].round(2)
print("\n🏆 OPTIMAL TRADING CANDIDATES (FAMILY PROTECTION):")
for idx, row in top_candidates.iterrows():
    print(f"{row['symbol']:6} | ${row['price']:8.2f} | {row['gradient_recent']:7.1f}% | {row['trades']:6.0f} trades | Score: {row['trading_score']:5.1f}")

# 3. PROFIT TARGETS
df["profit_target"] = df["price"] * 1.03  # 3% family protection target
profit_ready = df[df["gradient_recent"] > 5][["symbol", "price", "profit_target", "gradient_recent"]].round(2)
print(f"\n🎯 STOCKS READY FOR PROFIT-TAKING:")
for idx, row in profit_ready.iterrows():
    print(f"{row['symbol']:6} | Entry: ${row['price']:8.2f} | Target: ${row['profit_target']:8.2f} | Momentum: {row['gradient_recent']:5.1f}%")
"', execution_mode='advanced')"

echo -e "\n✅ C Analyzer workflow complete!"
echo "📁 Files created:"
echo "   - $LATEST_JSON (detailed analysis)"
echo "   - $CSV_FILE (MCP-ready dataset)"
echo -e "\n🤖 Next: Run the MCP commands in Claude Code for advanced analytics"