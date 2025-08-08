# QUICK TRADING COMMANDS REFERENCE

## **🚀 FAMILY-PROTECTION TRADING WORKFLOWS**

### **1. Basic C Analyzer + MCP Analysis**
```bash
# Run real-time gradient analysis with statistical validation
./commands_c_analyzer.sh
```
**Output**: Real-time JSON analysis + CSV for MCP analytics
**Use case**: Quick momentum screening with professional statistics

### **2. News Analysis + Stock Validation**  
```bash
# Analyze news catalysts for top momentum stocks
./commands_news_analysis.sh
```
**Output**: RSS news analysis + trading significance scoring
**Use case**: Identify catalyst-driven opportunities

### **3. FFT + Multi-Tool Convergence**
```bash
# Ultimate validation: FFT mathematics + real-time gradients
./commands_fft_convergence.sh
```
**Output**: Convergence-validated stocks (highest confidence)
**Use case**: Maximum confidence trades with mathematical backing

### **4. MASTER TRADING WORKFLOW**
```bash
# Complete integration: FFT + C analyzer + news + MCP commands
./commands_master_trading.sh
```
**Output**: Complete family-protection trading recommendations
**Use case**: Daily trading routine with full validation

---

## **🤖 Essential MCP Commands (for Claude Code)**

### **Real-Time Market Data**
```python
# Get current snapshots
mcp__alpaca-trading__get_stock_snapshots(symbols='SOUN,MRM,IXHL')

# Enhanced analytics with VWAP/support/resistance  
mcp__alpaca-trading__get_enhanced_streaming_analytics(symbol='MRM', analysis_minutes=15)

# MANDATORY: Peak/trough analysis before entry
mcp__alpaca-trading__get_stock_peak_trough_analysis(symbols='MRM', timeframe='1Min', days=1)
```

### **Live Streaming & Execution**
```python
# Start real-time data stream
mcp__alpaca-trading__start_global_stock_stream(symbols=['MRM'], data_types=['trades', 'quotes'])

# Stream-optimized order placement (family protection)
mcp__alpaca-trading__stream_optimized_order_placement(symbol='MRM', side='buy', quantity=10000, order_type='limit')

# Continuous monitoring (run every 10 seconds)
mcp__alpaca-trading__stream_aware_price_monitor(symbol='MRM', analysis_seconds=10)
```

### **Advanced Analytics with Quick-Data MCP**
```python
# Load analysis results for statistical validation
mcp__quick-data__load_dataset(file_path='/path/to/analysis.csv', dataset_name='trading_data')

# Professional correlation analysis
mcp__quick-data__find_correlations(dataset_name='trading_data', threshold=0.3)

# Custom trading analysis
mcp__quick-data__execute_enhanced_analytics_code_tool(dataset_name='trading_data', python_code='''
# Family protection trading analysis
df["trading_score"] = df["gradient_recent"] * 0.4 + np.log10(df["trades"]) * 10
top_candidates = df.nlargest(5, "trading_score")
print("🏆 TOP FAMILY-PROTECTION CANDIDATES:")
print(top_candidates[["symbol", "price", "gradient_recent", "trading_score"]])
''')
```

---

## **⚡ Individual Tool Commands**

### **C Analyzer (Real-Time Gradients)**
```bash
# Compile with safety flags
gcc -o stock_analyzer_json stock_analyzer_json.c -lcurl -ljson-c -lm -Wall -Wno-format-truncation

# Run analysis
./stock_analyzer_json combined.lis > analysis_$(date +%Y%m%d_%H%M%S).json

# Convert to CSV for MCP
python3 -c "import json,pandas as pd; data=json.load(open('analysis.json')); pd.DataFrame(data['stocks']).to_csv('analysis.csv', index=False)"
```

### **FFT Momentum Analysis**
```bash
# Run FFT mathematical analysis
./latest.sh

# Check results
cat output.avo.latest.dat | head -25  # Top 20 FFT rankings
```

### **News Analysis**
```bash
# Yahoo RSS feeds for specific stocks
python3 yf_rss.py --symbols "MRM,SOUN,IXHL" --output news_analysis.json

# News scraper (fallback)
python3 yf_news.py  # Interactive mode
```

---

## **🚨 FAMILY PROTECTION RULES**

### **Mandatory Pre-Trade Checklist**
1. ✅ **FFT + C analyzer convergence validated**
2. ✅ **Peak/trough analysis shows TROUGH signals (buy zones)**  
3. ✅ **News catalysts identified and analyzed**
4. ✅ **Position sizing calculated (3% profit target)**
5. ✅ **Stream monitoring ready for 10-second intervals**

### **Execution Rules**
- **Entry**: Only at fresh trough signals (1-5 bars ago)
- **Position Size**: $10K-$50K based on convergence confidence
- **Profit Target**: 3% = IMMEDIATE SELL (family security)
- **Stop Loss**: 2% maximum (protect family capital)
- **Monitoring**: Every 10 seconds when holding positions

### **Emergency Commands**
```python
# Get current positions
mcp__alpaca-trading__get_positions()

# Close specific position (profit-taking)
mcp__alpaca-trading__stream_optimized_order_placement(symbol='MRM', side='sell', quantity=10000)

# Emergency: close all positions
mcp__alpaca-trading__close_all_positions()
```

---

## **📊 File Organization**

**Analysis Files** (auto-generated):
- `real_time_analysis_TIMESTAMP.json` - C analyzer results
- `momentum_news_TIMESTAMP.json` - RSS news analysis  
- `convergence_symbols.txt` - Multi-tool validated stocks
- `master_final.txt` - Final trading candidates

**Command Scripts**:
- `commands_c_analyzer.sh` - C + MCP workflow
- `commands_news_analysis.sh` - News + validation
- `commands_fft_convergence.sh` - FFT + convergence  
- `commands_master_trading.sh` - Complete workflow

**Quick Access**:
```bash
# Make all scripts executable
chmod +x commands_*.sh

# Quick status check
ls -la *_analysis_*.json | tail -3  # Latest analysis files
cat master_final.txt 2>/dev/null || echo "No recent analysis"  # Current candidates
```

---

## **⚠️ Critical Reminders**

**NEVER trade without:**
1. Mathematical convergence (FFT + C analyzer agreement)
2. Peak/trough validation (avoid resistance levels)
3. Real-time streaming monitoring setup
4. 3% profit target discipline

**Remember**: Every hesitation costs family money. Speed and precision protect their financial security.