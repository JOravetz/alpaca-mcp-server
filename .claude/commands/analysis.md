# Technical Analysis Tools
Show the technical analysis and market data tools available for stock analysis.

## Primary Analysis Tools

**New Peak/Trough Analysis (🔥 Recommended):**
- `get_stock_peak_trough_analysis("SYMBOLS", timeframe="1Min", window_len=11, lookahead=1)`
- Perfect for finding precise entry/exit points using zero-phase Hanning filtering
- Returns BUY/LONG and SELL/SHORT signals with support/resistance levels

**Market Data Tools:**
- `get_stock_bars_intraday("SYMBOL", timeframe="1Min", limit=200)` - Detailed intraday analysis
- `get_stock_bars("SYMBOL", days=5)` - Daily historical data
- `get_stock_quote("SYMBOL")` - Current bid/ask prices
- `get_stock_latest_trade("SYMBOL")` - Most recent trade

**Real-time Analysis:**
- `get_stock_stream_data("SYMBOL", "trades", recent_seconds=120)` - Live trade flow
- `get_stock_snapshots("SYMBOL1,SYMBOL2,SYMBOL3")` - Multi-stock overview

## Analysis Parameters for Different Strategies

**Scalping (1Min bars):**
```
get_stock_peak_trough_analysis("SYMBOL", 
    timeframe="1Min", 
    window_len=11,       # Less smoothing
    lookahead=1,         # Most sensitive
    min_peak_distance=3  # Closer peaks
)
```

**Day Trading (1-5Min bars):**
```
get_stock_peak_trough_analysis("SYMBOL", 
    timeframe="1Min", 
    window_len=11,       # Standard smoothing
    lookahead=1,         # Sensitive
    min_peak_distance=5  # Standard spacing
)
```

**Swing Analysis (15Min+ bars):**
```
get_stock_peak_trough_analysis("SYMBOL", 
    timeframe="15Min", 
    window_len=21,       # More smoothing
    lookahead=5,         # Less sensitive
    min_peak_distance=10 # Wider spacing
)
```

## COMMAND: `/analyze [SYMBOLS]`
**Analyzes ALL provided stocks comprehensively without cherry-picking**

### CLAUDE EXECUTION INSTRUCTIONS:
When user runs `/analyze [SYMBOLS]`, Claude MUST:

1. **Parse ALL symbols** from the arguments (space or comma separated)
2. **Execute parallel analysis** for EVERY symbol provided - NO EXCEPTIONS
3. **Generate complete reports** for each stock

### EXECUTION PATTERN:
```
User: /analyze AAPL MSFT TSLA NVDA AMD
Claude executes IN PARALLEL:
- get_stock_peak_trough_analysis("AAPL,MSFT,TSLA,NVDA,AMD")
- get_stock_snapshots("AAPL,MSFT,TSLA,NVDA,AMD")
- get_stock_quote() for EACH symbol
- get_stock_bars_intraday() for EACH symbol showing momentum
```

### OUTPUT FORMAT:
```
📊 TECHNICAL ANALYSIS REPORT
============================
Analyzing ALL [X] stocks provided...

🎯 STOCK 1: [SYMBOL]
━━━━━━━━━━━━━━━━━━━
Current Price: $[Price] ([Change]%)
Signal: [BUY/SELL/HOLD]
Support: $[Level] | Resistance: $[Level]
Volume: [Volume] | Avg Volume: [Avg]
Momentum: [Rising/Falling/Flat]
Entry Point: $[Suggested entry]
Stop Loss: $[Suggested stop]

🎯 STOCK 2: [SYMBOL]
━━━━━━━━━━━━━━━━━━━
[Same format for EVERY stock]

[Continue for ALL stocks provided]

📈 SUMMARY RANKINGS
==================
STRONGEST BUY SIGNALS:
1. [Symbol] - [Reason]
2. [Symbol] - [Reason]
3. [Symbol] - [Reason]

AVOID/SELL SIGNALS:
1. [Symbol] - [Reason]
2. [Symbol] - [Reason]

HIGHEST MOMENTUM:
1. [Symbol] - [Metric]
2. [Symbol] - [Metric]
```

### PARALLEL EXECUTION EXAMPLE:
When user types: `/analyze AAPL MSFT GOOGL AMZN META NVDA TSLA AMD`

Claude MUST analyze ALL 8 stocks by executing:
```python
# PARALLEL BATCH 1: Peak/Trough Analysis
get_stock_peak_trough_analysis("AAPL,MSFT,GOOGL,AMZN,META,NVDA,TSLA,AMD", 
                               timeframe="1Min", window_len=11)

# PARALLEL BATCH 2: Market Data (ALL stocks)
- get_stock_snapshots("AAPL,MSFT,GOOGL,AMZN,META,NVDA,TSLA,AMD")
- get_stock_quote("AAPL")
- get_stock_quote("MSFT")
- get_stock_quote("GOOGL")
- get_stock_quote("AMZN")
- get_stock_quote("META")
- get_stock_quote("NVDA")
- get_stock_quote("TSLA")
- get_stock_quote("AMD")

# PARALLEL BATCH 3: Intraday Bars (if needed for momentum)
- get_stock_bars_intraday() for each stock
```

## CRITICAL REQUIREMENTS:
1. **NEVER skip stocks** - If user provides 10 symbols, analyze ALL 10
2. **NEVER cherry-pick** - Don't select "top 3" or "most interesting"
3. **ALWAYS use parallel execution** - Run multiple tools simultaneously
4. **ALWAYS provide analysis for EVERY stock** - Even if some show no clear signals
5. **MAINTAIN ORDER** - Present stocks in the order provided by user

## ERROR HANDLING:
- If a symbol is invalid: Note it but continue with ALL others
- If API limits hit: Batch the requests but still analyze ALL
- If no data available: Report "No data" but include in report

## ADDITIONAL ANALYSIS COMMANDS:

### `/analyze-scalp [SYMBOLS]`
Analyzes ALL stocks with scalping parameters (window_len=11, min_peak_distance=3)

### `/analyze-swing [SYMBOLS]`
Analyzes ALL stocks with swing parameters (timeframe="15Min", window_len=21, lookahead=5)

### `/analyze-momentum [SYMBOLS]`
Focuses on momentum indicators for ALL stocks:
- Volume analysis
- Price velocity
- Trade frequency
- Relative strength

### `/analyze-entry [SYMBOLS]`
Provides precise entry points for ALL stocks:
- Current support/resistance
- Optimal limit order prices
- Risk/reward ratios
- Stop loss suggestions

## USAGE EXAMPLES:

**Example 1: Analyze scanner results**
```
User: /analyze AAPL MSFT TSLA NVDA AMD GOOGL
Claude: [Analyzes ALL 6 stocks in parallel]
```

**Example 2: Analyze high-liquidity stocks from stock_analyzer_json**
```
User: Run stock_analyzer_json first, then /analyze [top 10 results]
Claude: [Analyzes ALL 10 stocks without filtering]
```

**Example 3: Combined with news**
```
User: /analyze AAPL MSFT TSLA, then run news scraper on all
Claude: [Analyzes ALL 3 stocks, then fetches news for ALL 3]
```

## INTEGRATION WITH STARTUP:
After `/startup` completes and identifies high-liquidity stocks:
1. Use `/analyze [ALL SYMBOLS]` on the complete list
2. Review technical signals for ALL stocks
3. Cross-reference with news from yf_rss.py
4. Make trading decisions based on complete analysis

**Remember: EVERY stock deserves analysis. NO cherry-picking. ALL symbols get processed.**
