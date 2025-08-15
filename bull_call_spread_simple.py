#!/usr/bin/env python3
"""
Automated Bull Call Spread Trading Algorithm - Simple Version
Uses MCP tools through direct calls
"""

import argparse
import sys
from datetime import datetime, timedelta
import asyncio

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

async def main():
    """Main entry point with CLI interface"""
    
    parser = argparse.ArgumentParser(
        description='Automated Bull Call Spread Trading Algorithm',
        epilog="""
Examples:
  %(prog)s                     # Trade SPY with default parameters
  %(prog)s -s AAPL             # Trade AAPL spreads
  %(prog)s --buy 2 --sell 3    # Custom strike percentages
  %(prog)s -w 3 -q 2           # 3 weeks expiration, 2 spreads
  %(prog)s --dry_run           # Show strategy without executing
        """
    )
    
    parser.add_argument('-s', '--symbol', default='SPY',
                       help='Underlying symbol (default: SPY)')
    parser.add_argument('--buy', type=float, default=3,
                       help='Percentage below for long call (default: 3)')
    parser.add_argument('--sell', type=float, default=5,
                       help='Percentage above for short call (default: 5)')
    parser.add_argument('-w', '--weeks', type=int, default=2,
                       help='Weeks until expiration (default: 2)')
    parser.add_argument('-q', '--quantity', type=int, default=1,
                       help='Number of spreads (default: 1)')
    parser.add_argument('--dry_run', action='store_true',
                       help='Show strategy without executing')
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.buy <= 0 or args.sell <= 0:
        print("Error: Percentages must be positive")
        sys.exit(1)
    
    print(f"\n{'='*50}")
    print(f"Bull Call Spread Strategy for {args.symbol}")
    print(f"{'='*50}\n")
    
    # Import MCP tools
    from alpaca_mcp_server.tools.market_data_tools import get_stock_quote
    from alpaca_mcp_server.tools.options_tools import get_option_contracts
    from alpaca_mcp_server.tools.order_tools import place_option_market_order
    
    # Step 1: Get current price
    print(f"Getting current price for {args.symbol}...")
    quote_result = await get_stock_quote(symbol=args.symbol)
    
    # Parse price from result
    current_price = None
    if 'Ask Price: $' in quote_result:
        price_str = quote_result.split('Ask Price: $')[1].split('\n')[0]
        current_price = float(price_str)
    elif 'Bid Price: $' in quote_result:
        price_str = quote_result.split('Bid Price: $')[1].split('\n')[0]
        current_price = float(price_str)
    
    if not current_price:
        print(f"Error: Unable to get price for {args.symbol}")
        sys.exit(1)
    
    print(f"Current Price: ${current_price:.2f}")
    
    # Step 2: Calculate strikes
    buy_strike = round(current_price * (1 - args.buy / 100))
    sell_strike = round(current_price * (1 + args.sell / 100))
    
    print(f"Buy Call Strike: ${buy_strike} ({args.buy}% below)")
    print(f"Sell Call Strike: ${sell_strike} ({args.sell}% above)")
    
    # Step 3: Calculate expiration
    expiration_date = (datetime.now() + timedelta(weeks=args.weeks)).strftime('%Y-%m-%d')
    print(f"Target Expiration: {expiration_date} (~{args.weeks} weeks)")
    
    # Step 4: Find option contracts
    print(f"\nSearching for option contracts...")
    
    # Get buy contract
    buy_contracts = await get_option_contracts(
        underlying_symbol=args.symbol,
        type='call',
        strike_price_gte=str(buy_strike - 0.5),
        strike_price_lte=str(buy_strike + 0.5),
        expiration_date=expiration_date,
        limit=1
    )
    
    # Get sell contract
    sell_contracts = await get_option_contracts(
        underlying_symbol=args.symbol,
        type='call',
        strike_price_gte=str(sell_strike - 0.5),
        strike_price_lte=str(sell_strike + 0.5),
        expiration_date=expiration_date,
        limit=1
    )
    
    # Parse contract symbols
    buy_symbol = None
    sell_symbol = None
    
    # Look for Contract: line and verify it's a CALL
    if 'Contract:' in buy_contracts:
        for line in buy_contracts.split('\n'):
            if 'Contract:' in line:
                contract = line.split('Contract:')[1].strip()
                # Verify it's a call option (has 'C' in symbol)
                if 'C' in contract:
                    buy_symbol = contract
                    break
    
    if 'Contract:' in sell_contracts:
        for line in sell_contracts.split('\n'):
            if 'Contract:' in line:
                contract = line.split('Contract:')[1].strip()
                # Verify it's a call option (has 'C' in symbol)
                if 'C' in contract:
                    sell_symbol = contract
                    break
    
    if not buy_symbol or not sell_symbol:
        print("Error: Unable to find matching option contracts")
        print(f"Buy contract result: {buy_contracts[:200]}")
        print(f"Sell contract result: {sell_contracts[:200]}")
        sys.exit(1)
    
    print(f"Buy Contract: {buy_symbol}")
    print(f"Sell Contract: {sell_symbol}")
    
    # Step 5: Display summary
    print(f"\n{'='*50}")
    print("Strategy Summary:")
    print(f"{'='*50}")
    print(f"Type: Bull Call Spread (Debit Spread)")
    print(f"Underlying: {args.symbol}")
    print(f"Quantity: {args.quantity} spread(s)")
    print(f"Max Risk: Net debit paid")
    print(f"Max Profit: ${(sell_strike - buy_strike) * 100 * args.quantity}")
    
    if args.dry_run:
        print(f"\n[DRY RUN - No order will be placed]")
        print("Run without --dry_run to execute")
        return
    
    # Step 6: Execute order
    print(f"\nPlacing multi-leg order...")
    
    try:
        result = await place_option_market_order(
            legs=[
                {"symbol": buy_symbol, "side": "buy", "ratio": args.quantity},
                {"symbol": sell_symbol, "side": "sell", "ratio": args.quantity}
            ],
            order_class='bracket'
        )
        
        if 'success' in str(result).lower() or 'placed' in str(result).lower():
            print("✅ Order placed successfully!")
        else:
            if 'market hours' in str(result).lower():
                print("⚠️ Market closed - Options trade 9:30 AM - 4:00 PM ET")
            else:
                print(f"Order result: {result}")
    except Exception as e:
        if 'market hours' in str(e).lower():
            print("⚠️ Market closed - Options trade 9:30 AM - 4:00 PM ET")
        else:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())