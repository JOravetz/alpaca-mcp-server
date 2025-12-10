# Plot Commands

## plot-help
Show detailed help for all plot commands
```bash
echo "📊 PLOT COMMANDS HELP GUIDE"
echo "=========================="
echo ""
echo "🎯 BASIC PLOTTING:"
echo "  plot                    → Plot SPY with defaults (21-window, 1 day, 1Min)"
echo "  plot SYMBOL             → Plot any symbol with defaults"
echo "  plot SYMBOL WINDOW      → Custom window length (3-101, must be odd)"
echo "  plot SYMBOL WINDOW DAYS → Custom days back (1-30)"
echo "  plot SYMBOL WINDOW DAYS TIMEFRAME → Custom timeframe"
echo ""
echo "📁 FILE-BASED PLOTTING:"
echo "  plot-file               → Plot all symbols from data/momentum.lis"
echo "  plot-file FILENAME      → Plot symbols from custom file"
echo "  plot-file FILENAME DAYS → Custom days with file"
echo "  plot-check              → Preview file contents before plotting"
echo ""
echo "🔢 MULTI-SYMBOL PLOTTING:"
echo "  plot-multi              → Plot SPY,QQQ with defaults"
echo "  plot-multi 'SYM1,SYM2' → Plot custom symbols (use quotes!)"
echo ""
echo "📋 EXAMPLES:"
echo "  plot WHLR 51            → WHLR with 51-period Hanning filter"
echo "  plot AAPL 21 5 5Min     → AAPL, 21-window, 5 days, 5Min bars"
echo "  plot-file data/combined.lis 10 15Min → File with 10 days, 15Min bars"
echo "  plot-multi 'TSLA,NVDA,AAPL' 31 → Multiple stocks, 31-window"
echo ""
echo "⚙️  PARAMETERS:"
echo "  SYMBOL     → Stock ticker (e.g., AAPL, TSLA, SPY)"
echo "  WINDOW     → Hanning filter length: 3-101 (default: 21, must be odd)"
echo "  DAYS       → Trading days back: 1-30 (default: 1)"
echo "  TIMEFRAME  → Bar size: 1Min, 5Min, 15Min, 30Min, 1Hour, 1Day"
echo "  LOOKAHEAD  → Peak sensitivity: 1-50 (default: 1, higher=more sensitive)"
echo "  FEED       → Data source: sip, iex, otc (default: sip)"
echo ""
echo "🚨 SAFETY LIMITS:"
echo "  • Maximum 100 symbols per file (plot-file auto-checks)"
echo "  • Maximum 20 symbols for multi-symbol plots"
echo "  • Window length auto-adjusted to odd numbers"
echo ""
echo "💡 TIPS:"
echo "  • Use plot-check to preview large files before plotting"
echo "  • Higher window values = smoother but less sensitive"
echo "  • 15Min/30Min timeframes work better for multi-day analysis"
echo "  • Use quotes around comma-separated symbols: 'AAPL,MSFT'"
echo ""
echo "📊 OUTPUT:"
echo "  • Interactive plots with peak/trough detection"
echo "  • Support/resistance levels highlighted"
echo "  • Signal summary tables with trading levels"
echo "  • Statistical analysis and momentum indicators"
echo ""
echo "🔧 TROUBLESHOOTING:"
echo "  • If plot fails: Check symbol validity and market hours"
echo "  • If file not found: Use plot-check to verify file path"
echo "  • If too many symbols: Use head -N filename.lis to limit"
echo ""
```

## plot
Generate technical analysis plots with peak/trough detection
```bash
cd /home/jjoravet/alpaca-mcp-server-enhanced/alpaca_mcp_server/tools

# Show help if requested
if [[ "$1" == "--help" || "$1" == "-h" || "$1" == "help" ]]; then
    echo "🎯 PLOT COMMAND HELP"
    echo "Usage: plot [SYMBOL] [WINDOW] [DAYS] [TIMEFRAME] [LOOKAHEAD] [FEED]"
    echo ""
    echo "Arguments (all optional):"
    echo "  SYMBOL     → Stock ticker (default: SPY)"
    echo "  WINDOW     → Hanning filter length 3-101 (default: 21)"
    echo "  DAYS       → Trading days back 1-30 (default: 1)"
    echo "  TIMEFRAME  → Bar size: 1Min,5Min,15Min,30Min,1Hour,1Day (default: 1Min)"
    echo "  LOOKAHEAD  → Peak sensitivity 1-50 (default: 1)"
    echo "  FEED       → Data source: sip,iex,otc (default: sip)"
    echo ""
    echo "Examples:"
    echo "  plot                    → SPY with all defaults"
    echo "  plot WHLR               → WHLR with defaults"
    echo "  plot WHLR 51            → WHLR with 51-period filter"
    echo "  plot AAPL 21 5 5Min     → AAPL, 21-window, 5 days, 5Min bars"
    echo ""
    exit 0
fi

SYMBOL=${1:-"SPY"}
WINDOW=${2:-21}
DAYS=${3:-1}
TIMEFRAME=${4:-"1Min"}
LOOKAHEAD=${5:-1}
FEED=${6:-"sip"}

echo "🎯 Generating plot: Symbol=$SYMBOL, Window=$WINDOW, Days=$DAYS, Timeframe=$TIMEFRAME"
python plot.py -s "$SYMBOL" -w "$WINDOW" -d "$DAYS" -t "$TIMEFRAME" -l "$LOOKAHEAD" -f "$FEED"
```

## plot-file
Plot all symbols from a file with safety checks (max 100 symbols)
```bash
cd /home/jjoravet/alpaca-mcp-server-enhanced

# Show help if requested
if [[ "$1" == "--help" || "$1" == "-h" || "$1" == "help" ]]; then
    echo "📁 PLOT-FILE COMMAND HELP"
    echo "Usage: plot-file [FILENAME] [DAYS] [TIMEFRAME] [WINDOW]"
    echo ""
    echo "Arguments (all optional):"
    echo "  FILENAME   → Symbol file path (default: data/momentum.lis)"
    echo "  DAYS       → Trading days back 1-30 (default: 15)"
    echo "  TIMEFRAME  → Bar size (default: 15Min)"
    echo "  WINDOW     → Hanning filter length (default: 101)"
    echo ""
    echo "Examples:"
    echo "  plot-file                           → Use momentum.lis with defaults"
    echo "  plot-file data/combined.lis         → Different file"
    echo "  plot-file data/momentum.lis 10      → 10 days instead of 15"
    echo "  plot-file data/momentum.lis 10 5Min → 10 days, 5Min bars"
    echo ""
    echo "Safety: Automatically checks for 100 symbol limit"
    echo "Tip: Use plot-check to preview file contents first"
    exit 0
fi

FILE=${1:-"data/momentum.lis"}
DAYS=${2:-15}
TIMEFRAME=${3:-"15Min"}
WINDOW=${4:-101}

if [ ! -f "$FILE" ]; then
    echo "❌ File not found: $FILE"
    echo "Available files:"
    ls -1 data/*.lis 2>/dev/null || echo "No .lis files in data/"
    echo ""
    echo "💡 Use 'plot-file help' for usage examples"
    exit 1
fi

SYMBOL_COUNT=$(wc -l < "$FILE")
echo "📊 Found $SYMBOL_COUNT symbols in $FILE"

if [ "$SYMBOL_COUNT" -gt 100 ]; then
    echo "❌ Too many symbols ($SYMBOL_COUNT > 100 limit)"
    echo "Consider limiting with: head -100 $FILE"
    echo "Or use: head -100 $FILE > temp.lis && plot-file temp.lis"
    exit 1
fi

if [ "$SYMBOL_COUNT" -eq 0 ]; then
    echo "❌ No symbols found in $FILE"
    exit 1
fi

SYMBOLS=$(cat "$FILE" | tr '\n' ',' | sed 's/,$//')

echo "🎯 Plotting $SYMBOL_COUNT symbols from $FILE"
echo "Parameters: Days=$DAYS, Timeframe=$TIMEFRAME, Window=$WINDOW"

cd alpaca_mcp_server/tools
python plot.py -s "$SYMBOLS" --no-plot --report -d "$DAYS" -t "$TIMEFRAME" -w "$WINDOW"
```

## plot-multi
Plot multiple symbols (comma-separated)
```bash
cd /home/jjoravet/alpaca-mcp-server-enhanced/alpaca_mcp_server/tools

# Show help if requested
if [[ "$1" == "--help" || "$1" == "-h" || "$1" == "help" ]]; then
    echo "🔢 PLOT-MULTI COMMAND HELP"
    echo "Usage: plot-multi [SYMBOLS] [WINDOW] [DAYS] [TIMEFRAME]"
    echo ""
    echo "Arguments (all optional):"
    echo "  SYMBOLS    → Comma-separated tickers (default: 'SPY,QQQ')"
    echo "  WINDOW     → Hanning filter length (default: 21)"
    echo "  DAYS       → Trading days back (default: 1)"
    echo "  TIMEFRAME  → Bar size (default: 1Min)"
    echo ""
    echo "Examples:"
    echo "  plot-multi                          → SPY,QQQ with defaults"
    echo "  plot-multi 'AAPL,MSFT,NVDA'        → Tech stocks"
    echo "  plot-multi 'TSLA,RIVN,LCID' 31     → EV stocks, 31-window"
    echo "  plot-multi 'SPY,QQQ,IWM' 21 5 5Min → ETFs, 5 days, 5Min"
    echo ""
    echo "Important: Use quotes around symbol list!"
    echo "Limit: Maximum 20 symbols recommended"
    exit 0
fi

SYMBOLS=${1:-"SPY,QQQ"}
WINDOW=${2:-21}
DAYS=${3:-1}
TIMEFRAME=${4:-"1Min"}

echo "🎯 Plotting multiple symbols: $SYMBOLS"
echo "Parameters: Window=$WINDOW, Days=$DAYS, Timeframe=$TIMEFRAME"
python plot.py -s "$SYMBOLS" -w "$WINDOW" -d "$DAYS" -t "$TIMEFRAME"
```

## plot-check
Check symbol file contents before plotting
```bash
cd /home/jjoravet/alpaca-mcp-server-enhanced

# Show help if requested
if [[ "$1" == "--help" || "$1" == "-h" || "$1" == "help" ]]; then
    echo "🔍 PLOT-CHECK COMMAND HELP"
    echo "Usage: plot-check [FILENAME]"
    echo ""
    echo "Arguments:"
    echo "  FILENAME   → Symbol file to inspect (default: data/momentum.lis)"
    echo ""
    echo "Examples:"
    echo "  plot-check                    → Check momentum.lis"
    echo "  plot-check data/combined.lis  → Check combined.lis"
    echo ""
    echo "Shows: Symbol count, safety status, first/last symbols"
    echo "Use this before plot-file to avoid errors"
    exit 0
fi

FILE=${1:-"data/momentum.lis"}

if [ ! -f "$FILE" ]; then
    echo "❌ File not found: $FILE"
    echo ""
    echo "📁 Available .lis files:"
    ls -1 data/*.lis 2>/dev/null || echo "No .lis files found in data/"
    echo ""
    echo "💡 Use 'plot-check help' for usage info"
    exit 1
fi

SYMBOL_COUNT=$(wc -l < "$FILE")
echo "📊 SYMBOL FILE ANALYSIS"
echo "======================="
echo "📁 File: $FILE"
echo "📊 Symbol count: $SYMBOL_COUNT"
echo "📊 Safety status: $([ $SYMBOL_COUNT -le 100 ] && echo "✅ Within 100 symbol limit" || echo "❌ Exceeds 100 symbol limit")"
echo "📊 File size: $(du -h "$FILE" | cut -f1)"
echo "📊 Last modified: $(stat -c %y "$FILE" | cut -d. -f1)"
echo ""

if [ "$SYMBOL_COUNT" -gt 0 ]; then
    echo "🔝 First 10 symbols:"
    head -10 "$FILE" | nl -w2 -s'. '
    
    if [ "$SYMBOL_COUNT" -gt 10 ]; then
        echo ""
        echo "🔻 Last 5 symbols:"
        tail -5 "$FILE" | nl -v$((SYMBOL_COUNT-4)) -w2 -s'. '
    fi
    
    echo ""
    echo "💡 Ready for plotting commands:"
    echo "   plot-file $FILE"
    echo "   plot-file $FILE 10      # 10 days"
    echo "   plot-file $FILE 10 5Min # 10 days, 5Min bars"
else
    echo "❌ File is empty"
fi
```
