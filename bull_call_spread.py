#!/usr/bin/env python3
"""
Automated Bull Call Spread Trading Algorithm using Alpaca MCP Server
Simple, functional implementation of a debit spread strategy
"""

import argparse
import sys
from datetime import datetime, timedelta
import subprocess
import json
from pathlib import Path

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except PermissionError:
    print("Warning: Permission error loading .env file, continuing with system environment")
except ImportError:
    print("Warning: python-dotenv not installed, using system environment variables")

def get_current_price(symbol):
    """Get current price for the underlying symbol"""
    try:
        # Import the MCP server tools directly
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from alpaca_mcp_server.tools.market_data_tools import get_stock_quote
        
        result = get_stock_quote(symbol=symbol)
        
        # Parse the result string to extract price
        if 'Ask Price: $' in result:
            price_str = result.split('Ask Price: $')[1].split('\n')[0]
            return float(price_str)
        elif 'Bid Price: $' in result:
            price_str = result.split('Bid Price: $')[1].split('\n')[0]
            return float(price_str)
        
        print(f"Error: Unable to parse price from: {result}")
        return None
    except ImportError:
        # Fallback to subprocess if direct import fails
        try:
            import requests
            # Try using the Alpaca API directly
            import os
            api_key = os.getenv('APCA_API_KEY_ID')
            api_secret = os.getenv('APCA_API_SECRET_KEY')
            
            if api_key and api_secret:
                headers = {
                    'APCA-API-KEY-ID': api_key,
                    'APCA-API-SECRET-KEY': api_secret
                }
                url = f'https://data.alpaca.markets/v2/stocks/{symbol}/quotes/latest'
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if 'quote' in data:
                        return float(data['quote'].get('ap', data['quote'].get('bp', 0)))
        except:
            pass
        
        print(f"Error fetching current price for {symbol}")
        return None
    except Exception as e:
        print(f"Error fetching current price: {e}")
        return None

def calculate_strikes(current_price, buy_pct, sell_pct):
    """Calculate strike prices based on percentages"""
    # Buy call strike: below current price (lower strike)
    buy_strike = current_price * (1 - buy_pct / 100)
    # Sell call strike: above current price (higher strike)
    sell_strike = current_price * (1 + sell_pct / 100)
    
    # Round to nearest dollar for standard strikes
    buy_strike = round(buy_strike)
    sell_strike = round(sell_strike)
    
    return buy_strike, sell_strike

def get_expiration_date(weeks_ahead):
    """Calculate target expiration date"""
    target_date = datetime.now() + timedelta(weeks=weeks_ahead)
    # Format as YYYY-MM-DD
    return target_date.strftime('%Y-%m-%d')

def find_option_contracts(symbol, strike, expiration_date, option_type='call'):
    """Find option contracts matching our criteria"""
    try:
        # Import the MCP server tools directly
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from alpaca_mcp_server.tools.options_tools import get_option_contracts
        
        result = get_option_contracts(
            underlying_symbol=symbol,
            type=option_type,
            strike_price_gte=str(strike - 0.5),
            strike_price_lte=str(strike + 0.5),
            expiration_date=expiration_date,
            limit=1
        )
        
        # Parse the result to extract contract info
        if 'Option Contracts for' in result:
            lines = result.split('\n')
            for i, line in enumerate(lines):
                if 'Symbol:' in line:
                    contract_symbol = line.split('Symbol:')[1].strip()
                    # Build contract dict from parsed data
                    contract = {'symbol': contract_symbol}
                    
                    # Look for strike price in next lines
                    for j in range(i+1, min(i+5, len(lines))):
                        if 'Strike:' in lines[j]:
                            contract['strike'] = lines[j].split('Strike:')[1].strip()
                        elif 'Expiration:' in lines[j]:
                            contract['expiration'] = lines[j].split('Expiration:')[1].strip()
                    
                    return contract
        
        print(f"No contracts found for strike {strike}")
        return None
    except ImportError:
        print(f"Error: Unable to import MCP tools")
        return None
    except Exception as e:
        print(f"Error finding option contracts: {e}")
        return None

def execute_bull_call_spread(symbol, buy_pct, sell_pct, weeks_ahead, quantity, dry_run=False):
    """Execute the bull call spread strategy"""
    
    print(f"\n{'='*50}")
    print(f"Bull Call Spread Strategy for {symbol}")
    print(f"{'='*50}\n")
    
    # Step 1: Get current price
    current_price = get_current_price(symbol)
    if not current_price or current_price <= 0:
        print(f"Error: Unable to get valid price for {symbol}")
        return False
    
    print(f"Current {symbol} Price: ${current_price:.2f}")
    
    # Step 2: Calculate strikes
    buy_strike, sell_strike = calculate_strikes(current_price, buy_pct, sell_pct)
    print(f"Buy Call Strike (long): ${buy_strike} ({buy_pct}% below)")
    print(f"Sell Call Strike (short): ${sell_strike} ({sell_pct}% above)")
    
    # Step 3: Get expiration date
    expiration_date = get_expiration_date(weeks_ahead)
    print(f"Target Expiration: {expiration_date} (~{weeks_ahead} weeks)")
    
    # Step 4: Find option contracts
    print(f"\nSearching for option contracts...")
    
    buy_contract = find_option_contracts(symbol, buy_strike, expiration_date, 'call')
    sell_contract = find_option_contracts(symbol, sell_strike, expiration_date, 'call')
    
    if not buy_contract or not sell_contract:
        print("Error: Unable to find matching option contracts")
        return False
    
    # Extract contract symbols
    buy_symbol = buy_contract.get('symbol') or buy_contract.get('contract_symbol')
    sell_symbol = sell_contract.get('symbol') or sell_contract.get('contract_symbol')
    
    print(f"Buy Contract: {buy_symbol}")
    print(f"Sell Contract: {sell_symbol}")
    
    # Step 5: Display strategy summary
    print(f"\n{'='*50}")
    print("Strategy Summary:")
    print(f"{'='*50}")
    print(f"Strategy Type: Bull Call Spread (Debit Spread)")
    print(f"Underlying: {symbol}")
    print(f"Quantity: {quantity} spread(s)")
    print(f"Max Risk: Net debit paid (premium)")
    print(f"Max Profit: Strike difference - Net debit")
    print(f"Breakeven: Buy strike + Net debit")
    
    if dry_run:
        print(f"\n[DRY RUN MODE - No order will be placed]")
        print("\nTo execute this trade, run without --dry_run flag")
        return True
    
    # Step 6: Execute multi-leg order
    print(f"\nExecuting multi-leg order...")
    
    try:
        # Import the MCP server tools directly
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from alpaca_mcp_server.tools.options_tools import place_option_market_order
        
        result = place_option_market_order(
            legs=[
                {"symbol": buy_symbol, "side": "buy", "ratio": quantity},
                {"symbol": sell_symbol, "side": "sell", "ratio": quantity}
            ],
            order_class='bracket'
        )
        
        if 'Order placed successfully' in str(result):
            print("✅ Order placed successfully!")
            return True
        else:
            error_msg = str(result)
            if 'market hours' in error_msg.lower():
                print("⚠️ Market hours error: Options only trade during regular market hours")
                print("   Please try again during market hours (9:30 AM - 4:00 PM ET)")
            else:
                print(f"❌ Order failed: {error_msg}")
            return False
            
    except ImportError:
        print("Error: Unable to import MCP tools for order placement")
        return False
    except Exception as e:
        error_msg = str(e)
        if 'market hours' in error_msg.lower():
            print("⚠️ Market hours error: Options only trade during regular market hours")
            print("   Please try again during market hours (9:30 AM - 4:00 PM ET)")
        else:
            print(f"Error executing order: {e}")
        return False

def main():
    """Main entry point with CLI interface"""
    
    parser = argparse.ArgumentParser(
        description='Automated Bull Call Spread Trading Algorithm',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Trade SPY with default parameters
  %(prog)s -s AAPL             # Trade AAPL spreads
  %(prog)s --buy 2 --sell 3    # Custom strike percentages
  %(prog)s -w 3 -q 2           # 3 weeks expiration, 2 spreads
  %(prog)s --dry_run           # Show strategy without executing
        """
    )
    
    parser.add_argument('-s', '--symbol', 
                       default='SPY',
                       help='Underlying symbol to trade (default: SPY)')
    
    parser.add_argument('--buy', 
                       type=float,
                       default=3,
                       help='Percentage below current price for long call (default: 3)')
    
    parser.add_argument('--sell', 
                       type=float,
                       default=5,
                       help='Percentage above current price for short call (default: 5)')
    
    parser.add_argument('-w', '--weeks',
                       type=int,
                       default=2,
                       help='Weeks until expiration (default: 2)')
    
    parser.add_argument('-q', '--quantity',
                       type=int,
                       default=1,
                       help='Number of spreads to trade (default: 1)')
    
    parser.add_argument('--dry_run',
                       action='store_true',
                       help='Show strategy parameters without executing')
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.buy <= 0 or args.sell <= 0:
        print("Error: Percentages must be positive numbers")
        sys.exit(1)
    
    if args.weeks <= 0:
        print("Error: Weeks must be a positive number")
        sys.exit(1)
    
    if args.quantity <= 0:
        print("Error: Quantity must be a positive number")
        sys.exit(1)
    
    # Check if we're in the same directory as .env
    if not Path('.env').exists() and not args.dry_run:
        print("Warning: .env file not found in current directory")
        print("Make sure to run this script from the same directory as your .env file")
    
    # Execute the strategy
    success = execute_bull_call_spread(
        symbol=args.symbol,
        buy_pct=args.buy,
        sell_pct=args.sell,
        weeks_ahead=args.weeks,
        quantity=args.quantity,
        dry_run=args.dry_run
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()