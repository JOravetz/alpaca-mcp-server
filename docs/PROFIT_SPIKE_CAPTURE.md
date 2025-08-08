# IMMEDIATE PROFIT SPIKE CAPTURE STRATEGY

## THE PHENOMENON
Stocks with declining peaks/troughs often show a 1-5 cent profit spike IMMEDIATELY after purchase due to:
1. Market maker fills creating temporary imbalance
2. Other algorithms detecting new volume
3. Brief momentum from the buy order itself

## CRITICAL TIMING WINDOWS

### 🔴 0-3 SECONDS (ULTRA CRITICAL)
- Highest probability of spike
- Often 1-3 cents profit appears
- **ACTION**: Be ready to sell INSTANTLY

### 🟡 3-10 SECONDS (HIGH ALERT)
- Secondary spike possibility  
- Usually smaller than initial
- **ACTION**: Take ANY profit showing

### ⚫ 10+ SECONDS (DANGER ZONE)
- Spike usually gone
- Risk of decline begins
- **ACTION**: Consider exit even at breakeven

## AUTOMATED CAPTURE PROTOCOL

```python
# IMMEDIATELY after buy fill (within 0.5 seconds):
async def capture_profit_spike(symbol, quantity, entry_price):
    spike_window = 10  # seconds
    check_interval = 0.5  # check every 500ms
    
    start_time = time.time()
    
    while (time.time() - start_time) < spike_window:
        # Get real-time price
        current_data = get_stock_stream_data(symbol, "trades", recent_seconds=1)
        current_price = parse_last_price(current_data)
        
        # Calculate profit
        profit_per_share = current_price - entry_price
        total_profit = profit_per_share * quantity
        
        # IMMEDIATE SELL TRIGGERS
        if profit_per_share >= 0.01:  # Even 1 cent profit
            print(f"🔥 PROFIT SPIKE DETECTED: ${profit_per_share:.4f}/share")
            stream_optimized_order_placement(symbol, "sell", quantity)
            break
            
        await asyncio.sleep(check_interval)
    
    print("⚠️ No spike in window - monitor for reversal")
```

## DECLINING PEAKS STRATEGY

### IDENTIFY THE PATTERN
```
Peak 1: $2.40 ━━━━━┓
                    ┗━━ Trough: $2.26
Peak 2: $2.26 ━━━┓      (LOWER PEAK)
                 ┗━━━━ Trough: $2.19
Peak 3: $2.22 ━┓        (LOWER PEAK)  
              ┗━━━━━━ Trough: $2.11
```

### TRADING RULES FOR DECLINING PATTERNS

1. **NEVER HOLD FOR "RECOVERY"** - Each peak is lower
2. **TAKE 1-2 CENT PROFITS** - Don't wait for more
3. **EXIT SPEED IS CRITICAL** - Profits disappear in seconds
4. **AVOID RE-ENTRY** - Pattern continues declining

## REAL-TIME MONITORING CODE

```python
# Start this BEFORE placing buy order
start_global_stock_stream([symbol], ["trades", "quotes"])

# Place buy order
order = stream_optimized_order_placement(symbol, "buy", quantity)

# IMMEDIATELY monitor (no delay!)
while True:
    trades = get_stock_stream_data(symbol, "trades", recent_seconds=1)
    if profit_detected(trades, entry_price):
        # SELL WITHOUT HESITATION
        stream_optimized_order_placement(symbol, "sell", quantity)
        break
    time.sleep(0.5)  # 500ms checks
```

## MRM-SPECIFIC INSIGHTS

**Today's Pattern:**
- Entry: $2.17
- Likely spike: $2.18-2.19 (within 5 seconds)
- Current range: $2.11-2.17 (declining)
- **Action**: Should have sold at first $2.18 appearance

## KEY LESSONS

1. **Declining patterns = QUICK EXITS ONLY**
2. **First profit = BEST profit**
3. **Speed > Size** (Better $20 in 3 seconds than waiting for $100)
4. **Never fight the pattern** (Declining will continue)

## FAILURE MODES TO AVOID

❌ "It'll go higher" - NO, declining pattern won't reverse
❌ "I'll wait for $X profit" - Take what appears NOW
❌ "Let me check other things first" - FOCUS ONLY on position
❌ "The spread is tight, I'm safe" - Liquidity dries up fast

## SUCCESS METRICS

✅ Profit captured within 10 seconds = EXCELLENT
✅ Profit captured within 30 seconds = GOOD  
✅ Holding beyond 60 seconds = DANGER
✅ Any profit is good profit in declining pattern

## REMEMBER

**"The first profit spike is usually the ONLY profit spike"**

In declining patterns like MRM, that immediate 1-3 cent pop after your buy fill IS the opportunity - TAKE IT!