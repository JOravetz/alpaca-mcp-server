---
name: auto_trade_setup
description: Intelligent trade setup based on your detected patterns and current market conditions
---

# Auto Trade Setup

I'll analyze the market and set up trades based on your patterns. You can provide:
- Just a symbol: `/auto_trade_setup AAPL`
- Symbol and strategy: `/auto_trade_setup AAPL debit_spread`
- Full parameters: `/auto_trade_setup AAPL debit_spread 5 14` (width, expiration days)

## Setting up trade for: $ARGUMENTS

Let me analyze the current market conditions and your trading patterns...

### Step 1: Market Analysis
I'll check:
- Current price and quote
- Peak/trough levels for support/resistance
- Volume and momentum indicators
- Market hours status

### Step 2: Strategy Selection
Based on your patterns, I'll recommend:
- **Debit Spread** if expecting directional move
- **Iron Condor** if expecting range-bound
- **Protective Put** if already holding shares

### Step 3: Strike Selection
Using your typical parameters:
- Spread width based on your average
- Expiration based on your preference (usually 14 days)
- Strike prices aligned with support/resistance

### Step 4: Risk Management
- Position size based on 2% account risk
- Stop loss at 50% of debit paid
- Profit target at 50% of max profit

### Step 5: Order Preparation
I'll prepare the multi-leg order with:
- Proper market hours handling
- Extended hours flag if needed
- Scheduled execution if market closed

### Step 6: Monitoring Setup
- Add to watchlist
- Enable profit spike alerts
- Set up position monitoring

## Implementation:

```python
# Parse arguments
args = "$ARGUMENTS".split()
symbol = args[0] if args else "SPY"
strategy = args[1] if len(args) > 1 else "auto"
width = float(args[2]) if len(args) > 2 else None
expiration = int(args[3]) if len(args) > 3 else 14

# Get current market data
quote = mcp__alpaca-trading__get_stock_quote(symbol)
analysis = mcp__alpaca-trading__analyze_peaks_troughs_fast(symbol, "5Min", 1)

# Extract key levels
current_price = quote.get('ask_price', quote.get('bid_price'))
support = analysis.get('support_level')
resistance = analysis.get('resistance_level')

print(f"Current Price: ${current_price}")
print(f"Support: ${support}")
print(f"Resistance: ${resistance}")

# Determine strategy if auto
if strategy == "auto":
    if current_price near support:
        strategy = "bull_call_spread"
    elif current_price near resistance:
        strategy = "bear_put_spread"
    else:
        strategy = "iron_condor"

# Calculate strikes
if strategy == "bull_call_spread":
    buy_strike = round(current_price / 5) * 5  # ATM
    sell_strike = buy_strike + (width or 5)
    order_type = "debit"
    
elif strategy == "bear_put_spread":
    sell_strike = round(current_price / 5) * 5
    buy_strike = sell_strike + (width or 5)
    order_type = "credit"

# Check market hours
market_status = mcp__alpaca-trading__get_extended_market_clock()

if market_status['is_open']:
    # Place order now
    print("Market open - placing order")
else:
    # Schedule for next session
    print(f"Market closed - scheduling for {market_status['next_open']}")
    
# Set up monitoring
mcp__alpaca-trading__add_symbols_to_fastapi_watchlist([symbol])
mcp__alpaca-trading__start_fastapi_monitoring_service()
```

## Your Typical Patterns:
- Average spread width: $5
- Preferred expiration: 14 days
- Entry near support for bullish plays
- Entry near resistance for bearish plays
- Position size: 1-3 contracts
- Exit at 50% profit or -50% loss

$ARGUMENTS