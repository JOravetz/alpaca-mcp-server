# CRITICAL MONITORING PROTOCOL - AFTER ENTRY

## IMMEDIATE MONITORING SEQUENCE (0-3 seconds after fill)

### STEP 1: CONFIRM FILL (within 1 second)
```python
get_orders(status="all", limit=1)  # Get exact fill price
```

### STEP 2: START CONTINUOUS MONITORING (within 2 seconds)
```python
# RUN THIS LOOP IMMEDIATELY - NO DELAYS!
while position_open:
    # Every 2-3 seconds MAX:
    get_stock_stream_data(symbol, "trades", recent_seconds=2)
    get_positions()  # Check P&L
    
    # IF PROFIT DETECTED:
    if unrealized_pnl > 0:
        stream_optimized_order_placement(symbol, "sell", quantity)
        break
    
    # Continue monitoring without ANY other tasks
```

## CRITICAL RULES

1. **NO DELAYS** - Start monitoring within 2 seconds of fill
2. **NO DISTRACTIONS** - Don't update todos, don't run other analysis
3. **CONTINUOUS LOOP** - Check every 2-3 seconds without breaks
4. **INSTANT REACTION** - Sell within 1-2 seconds of profit appearing
5. **USE STREAMING** - Real-time data already flowing, just read it

## WHAT NOT TO DO

❌ Update todo lists after buying
❌ Run additional analysis tools
❌ Take breaks in monitoring
❌ Wait for "nice" profit - take ANY profit quickly
❌ Check other stocks while holding position

## PROFIT CAPTURE WINDOWS

- **0-10 seconds**: Most volatile, profits appear/disappear quickly
- **10-30 seconds**: Secondary moves
- **30-60 seconds**: Consolidation, harder to profit

## EXAMPLE OF PERFECT EXECUTION

```
08:52:27 - Fill confirmed at $2.17
08:52:28 - Start monitoring loop
08:52:30 - See $2.18 (+$23.80 profit)
08:52:31 - SELL IMMEDIATELY
08:52:32 - Confirm profit captured
```

## REMEMBER: SPEED > PERFECTION

Better to capture $20 profit in 5 seconds than wait for $100 and lose it all.