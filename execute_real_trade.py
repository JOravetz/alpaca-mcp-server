#!/usr/bin/env python3
"""
REAL Trade Executor - Actually places orders with Alpaca
WARNING: This will use REAL MONEY
"""

import asyncio
import sys
from datetime import datetime

async def place_real_trade():
    """Place a REAL trade on Alpaca"""
    
    print("=" * 60)
    print("PLACING REAL TRADE - NO DRY RUN")
    print("=" * 60)
    
    # Import the actual MCP tools
    from alpaca_mcp_server.tools.order_tools import place_stock_order
    from alpaca_mcp_server.tools.market_data import get_stock_quote
    from alpaca_mcp_server.tools.account_tools import get_positions
    
    # Get current SPY price
    print("\n1. Getting current SPY price...")
    quote_result = await get_stock_quote(symbol="SPY")
    print(quote_result)
    
    # Check current positions before trade
    print("\n2. Current positions before trade:")
    positions_before = await get_positions()
    print(positions_before)
    
    # Place a SMALL REAL order (1 share to prove it works)
    print("\n3. PLACING REAL ORDER: Buy 1 share of SPY")
    print("   This is a REAL order that will use REAL money!")
    
    try:
        order_result = await place_stock_order(
            symbol="SPY",
            side="buy",
            quantity=1,
            order_type="market",
            time_in_force="day"
        )
        
        print("\n✅ ORDER PLACED SUCCESSFULLY!")
        print(order_result)
        
        # Wait for order to fill
        print("\n4. Waiting 5 seconds for order to fill...")
        await asyncio.sleep(5)
        
        # Check positions after trade
        print("\n5. Positions AFTER trade:")
        positions_after = await get_positions()
        print(positions_after)
        
        print("\n" + "=" * 60)
        print("REAL TRADE EXECUTED - CHECK YOUR ALPACA ACCOUNT")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ORDER FAILED: {e}")
        return False

async def place_small_option_order():
    """Place a small options order"""
    
    print("=" * 60)
    print("PLACING REAL OPTIONS ORDER")
    print("=" * 60)
    
    from alpaca_mcp_server.tools.options_tools import place_option_market_order
    
    # Place a REAL options order
    print("\nPlacing REAL options order...")
    
    try:
        # Buy 1 SPY call option
        legs = [{
            "symbol": "SPY250822C00620000",  # SPY call expiring 8/22, $620 strike
            "side": "buy",
            "quantity": 1
        }]
        
        order_result = await place_option_market_order(
            legs=legs,
            quantity=1
        )
        
        print("\n✅ OPTIONS ORDER PLACED!")
        print(order_result)
        
        return True
        
    except Exception as e:
        print(f"\n❌ OPTIONS ORDER FAILED: {e}")
        print("Note: Options trading may require additional permissions")
        return False

if __name__ == "__main__":
    
    if len(sys.argv) < 2:
        print("WARNING: This will place REAL trades with REAL money!")
        print("\nUsage:")
        print("  python3 execute_real_trade.py stock    # Buy 1 share of SPY")
        print("  python3 execute_real_trade.py option   # Buy 1 SPY call option")
        print("\nType 'YES' to confirm you want to trade with REAL money: ", end="")
        
        confirm = input().strip()
        if confirm != "YES":
            print("Cancelled.")
            sys.exit(0)
        
        trade_type = "stock"
    else:
        trade_type = sys.argv[1]
    
    # Execute the trade
    if trade_type == "stock":
        asyncio.run(place_real_trade())
    elif trade_type == "option":
        asyncio.run(place_small_option_order())
    else:
        print(f"Unknown trade type: {trade_type}")