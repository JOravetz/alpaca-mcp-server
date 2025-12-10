---
name: peak_trough_trading
description: Analyzes peak/trough, checks quote, places limit order at support, then monitors
---

# peak_trough_trading

This command automates: Analyzes peak/trough, checks quote, places limit order at support, then monitors

Estimated time saved: 45 seconds

## What it does:
Analyzes peak/trough, checks quote, places limit order at support, then monitors

## Implementation:
```bash

# Detected peak/trough analysis - automating the trading workflow
symbol=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.symbols')
if [ ! -z "$symbol" ]; then
    echo "🎯 Auto-trading workflow triggered for $symbol"
    
    # Get current quote
    echo "📊 Checking current price..."
    claude-code "Get quote for $symbol"
    
    # Suggest order at support
    echo "💡 Suggesting limit order at identified support level"
    echo "   Run: place_stock_order at trough price"
    
    # Set up monitoring
    echo "👁️ Ready to monitor position after order"
fi

```

$ARGUMENTS
