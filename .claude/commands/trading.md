# Day Trading Tools Quick Reference

Show the essential tools for day trading workflows with the Alpaca MCP Server.

## Core Day Trading Tools

**Market Analysis:**
- `get_market_clock()` - Check if market is open
- `get_stock_snapshots("SYMBOL1,SYMBOL2")` - Quick market overview
- `get_stock_peak_trough_analysis("SYMBOL")` - **NEW** Technical analysis for entry/exit points

**Real-time Data:**
- `start_global_stock_stream(["SYMBOL"], ["trades", "quotes"])` - Start live data
- `get_stock_stream_data("SYMBOL", "trades", recent_seconds=60)` - Monitor activity

**Order Management:**
- `place_stock_order("SYMBOL", "buy", quantity, "limit", limit_price=X.XX)` - **USE LIMIT ORDERS**
- `get_orders("open")` - Check open orders
- `cancel_all_orders()` - Cancel all if needed

**Position Monitoring:**
- `get_positions()` - Check current positions
- `close_position("SYMBOL", percentage="100")` - Exit position

## Trading Lesson Integration

Following yesterday's lessons:
1. **"SCAN LONGER before entry"** → Use `get_stock_peak_trough_analysis()` to find precise entry levels
2. **"Use limit orders exclusively"** → Always use `order_type="limit"` 
3. **"React within 2-3 seconds"** → Have streaming data ready with `start_global_stock_stream()`
4. **"Monitor every 1-3 seconds"** → Use `get_stock_stream_data()` for real-time updates

## Example Day Trading Workflow

```
1. get_market_clock()
2. get_stock_snapshots("CGTL,HCTI,KLTO") 
3. get_stock_peak_trough_analysis("CGTL", timeframe="1Min")
4. start_global_stock_stream(["CGTL"], ["trades", "quotes"])
5. place_stock_order("CGTL", "buy", 1000, "limit", limit_price=1.25)
6. get_stock_stream_data("CGTL", "trades", recent_seconds=30)
7. close_position("CGTL", percentage="100") when profitable
```

Show practical examples for the current market session.