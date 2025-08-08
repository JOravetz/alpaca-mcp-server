#!/bin/bash
# News Analysis + Stock Validation Workflow
# Combines RSS feeds with Alpaca snapshots for catalyst-driven trading

echo "📰 FAMILY-PROTECTION TRADING: NEWS ANALYSIS + STOCK VALIDATION"
echo "=============================================================="

# Step 1: Extract top stocks from latest C analyzer results
echo "Step 1: Extracting top momentum stocks from latest analysis..."
LATEST_JSON=$(ls -t real_time_analysis_*.json | head -1)

if [ ! -f "$LATEST_JSON" ]; then
    echo "❌ No recent analysis found. Run commands_c_analyzer.sh first"
    exit 1
fi

# Extract top 10 stock symbols
TOP_STOCKS=$(python3 -c "
import json
with open('$LATEST_JSON', 'r') as f:
    data = json.load(f)
symbols = [stock['symbol'] for stock in data['stocks'][:10]]
print(','.join(symbols))
")

echo "✅ Top 10 momentum stocks: $TOP_STOCKS"

# Step 2: Fetch RSS news for top momentum stocks
echo -e "\nStep 2: Fetching Yahoo RSS news for top momentum stocks..."
python3 yf_rss.py --symbols "$TOP_STOCKS" --output "momentum_news_$(date +%Y%m%d_%H%M%S).json"

LATEST_NEWS=$(ls -t momentum_news_*.json | head -1)
if [ -f "$LATEST_NEWS" ]; then
    echo "✅ News analysis complete: $LATEST_NEWS"
    ARTICLE_COUNT=$(grep -o '"title"' "$LATEST_NEWS" | wc -l)
    echo "📰 Fetched $ARTICLE_COUNT news articles"
else
    echo "❌ News fetching failed"
fi

# Step 3: Get current market snapshots for validation
echo -e "\nStep 3: Fetching real-time snapshots for validation..."

# Note: These would be MCP commands in Claude Code
echo "🤖 MCP COMMANDS FOR CLAUDE CODE (SNAPSHOT VALIDATION):"
echo "======================================================"
echo "# Get snapshots for top momentum stocks"
echo "mcp__alpaca-trading__get_stock_snapshots(symbols='$TOP_STOCKS')"
echo ""
echo "# Get individual enhanced analytics"
IFS=',' read -ra STOCK_ARRAY <<< "$TOP_STOCKS"
for stock in "${STOCK_ARRAY[@]}"; do
    echo "mcp__alpaca-trading__get_enhanced_streaming_analytics(symbol='$stock', analysis_minutes=15)"
done

# Step 4: News sentiment analysis
echo -e "\nStep 4: Analyzing news sentiment and trading significance..."
python3 -c "
import json
import re
from collections import defaultdict

# Load news data
with open('$LATEST_NEWS', 'r') as f:
    news_data = json.load(f)

# Load stock performance data
with open('$LATEST_JSON', 'r') as f:
    stock_data = json.load(f)

# Create stock performance lookup
stock_performance = {stock['symbol']: stock for stock in stock_data['stocks']}

print('📰 NEWS-DRIVEN TRADING ANALYSIS')
print('=' * 40)

# Analyze by symbol
news_by_symbol = defaultdict(list)
for item in news_data.get('articles', []):
    symbol = item.get('symbol', 'UNKNOWN')
    news_by_symbol[symbol].append(item)

# Trading significance keywords
BULLISH_KEYWORDS = ['earnings beat', 'revenue growth', 'partnership', 'acquisition', 'upgrade', 'breakthrough', 'expansion', 'approval']
BEARISH_KEYWORDS = ['earnings miss', 'downgrade', 'lawsuit', 'investigation', 'decline', 'loss', 'warning', 'recall']

for symbol in '$TOP_STOCKS'.split(','):
    if symbol in news_by_symbol and symbol in stock_performance:
        perf = stock_performance[symbol]
        articles = news_by_symbol[symbol]
        
        print(f'\n🎯 {symbol} | Price: \${perf[\"price\"]:.2f} | Gradient: {perf[\"gradient_recent\"]:.1f}%')
        print('─' * 50)
        
        sentiment_score = 0
        catalyst_found = False
        
        for article in articles[:3]:  # Top 3 articles
            title = article.get('title', '').lower()
            
            # Check for trading catalysts
            bullish = sum(1 for kw in BULLISH_KEYWORDS if kw in title)
            bearish = sum(1 for kw in BEARISH_KEYWORDS if kw in title)
            sentiment_score += bullish - bearish
            
            if bullish > 0 or bearish > 0:
                catalyst_found = True
                catalyst_type = '🚀 BULLISH' if bullish > bearish else '🔻 BEARISH'
                print(f'{catalyst_type}: {article.get(\"title\", \"\")}')
        
        # Trading recommendation
        if catalyst_found and perf['gradient_recent'] > 5:
            print('✅ TRADING SIGNAL: News catalyst + momentum = HIGH CONFIDENCE')
        elif catalyst_found:
            print('⚠️ CATALYST DETECTED but weak momentum - WAIT for better entry')
        elif perf['gradient_recent'] > 10:
            print('📈 STRONG MOMENTUM but no news catalyst - TECHNICAL play')
        else:
            print('❌ No significant catalysts or momentum')
"

# Step 5: Create trading priority list
echo -e "\nStep 5: Creating family-protection trading priority list..."
python3 -c "
import json

# Load both datasets
with open('$LATEST_JSON', 'r') as f:
    stock_data = json.load(f)
    
try:
    with open('$LATEST_NEWS', 'r') as f:
        news_data = json.load(f)
    has_news = True
except:
    has_news = False
    news_data = {'articles': []}

print('🏆 FAMILY-PROTECTION TRADING PRIORITY LIST')
print('=' * 50)
print('Based on: Momentum + Volume + News Catalysts')
print()

# Create news lookup
news_count = {}
if has_news:
    for article in news_data.get('articles', []):
        symbol = article.get('symbol', '')
        news_count[symbol] = news_count.get(symbol, 0) + 1

# Score and rank stocks
for i, stock in enumerate(stock_data['stocks'][:5]):
    symbol = stock['symbol']
    gradient = stock['gradient_recent']
    trades = stock['trades']
    price = stock['price']
    news = news_count.get(symbol, 0)
    
    # Family protection score
    momentum_score = gradient * 0.4
    liquidity_score = min(trades / 100, 10)  # Max 10 points
    news_score = min(news * 2, 6)  # Max 6 points
    total_score = momentum_score + liquidity_score + news_score
    
    confidence = 'HIGH' if total_score > 15 else 'MEDIUM' if total_score > 8 else 'LOW'
    
    print(f'{i+1}. {symbol:6} | \${price:8.2f} | {gradient:6.1f}% gradient | {trades:4} trades | {news:2} news | Score: {total_score:5.1f} | {confidence}')
    
    if i == 0:
        print(f'   🎯 TOP FAMILY-PROTECTION CANDIDATE')
    
print()
print('🚨 FAMILY TRADING RULES:')
print('- ONLY trade HIGH confidence stocks (Score > 15)')
print('- Set 3% profit targets for family security')  
print('- NEVER hold overnight - take profits same day')
print('- Monitor every 10 seconds when holding positions')
"

echo -e "\n✅ News analysis workflow complete!"
echo "📁 Files created:"
echo "   - $LATEST_NEWS (news analysis)"
echo -e "\n🤖 Next: Run MCP snapshot commands in Claude Code for real-time validation"