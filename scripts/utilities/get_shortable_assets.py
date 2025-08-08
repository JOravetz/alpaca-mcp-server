#!/usr/bin/env python3
"""Get all shortable assets from Alpaca."""

import asyncio
from alpaca_mcp_server.config.settings import get_trading_client
from alpaca.trading.enums import AssetStatus


async def get_shortable_assets():
    """Get all shortable assets."""
    try:
        client = get_trading_client()
        
        # Get all assets
        assets = client.get_all_assets()
        
        # Filter for shortable assets
        shortable_assets = [
            asset for asset in assets 
            if asset.tradable and asset.shortable and asset.status == AssetStatus.ACTIVE
        ]
        
        # Sort by symbol
        shortable_assets.sort(key=lambda x: x.symbol)
        
        print(f"Total shortable assets found: {len(shortable_assets)}")
        print("=" * 80)
        
        # Save to file for easier viewing
        with open("shortable_assets.txt", "w") as f:
            f.write(f"Total shortable assets: {len(shortable_assets)}\n")
            f.write("=" * 80 + "\n\n")
            
            for asset in shortable_assets:
                f.write(f"Symbol: {asset.symbol}\n")
                f.write(f"  Name: {asset.name}\n")
                f.write(f"  Exchange: {asset.exchange}\n")
                f.write(f"  Easy to Borrow: {'Yes' if asset.easy_to_borrow else 'No'}\n")
                f.write("-" * 40 + "\n")
        
        # Display first 50 in console
        print("First 50 shortable assets:")
        print("-" * 80)
        
        for asset in shortable_assets[:50]:
            print(f"{asset.symbol:6} | {asset.name[:50]:50} | {asset.exchange}")
        
        print(f"\nFull list saved to: shortable_assets.txt")
        
        # Show some statistics
        exchanges = {}
        easy_to_borrow_count = 0
        
        for asset in shortable_assets:
            exchange = str(asset.exchange).split('.')[-1]
            exchanges[exchange] = exchanges.get(exchange, 0) + 1
            if asset.easy_to_borrow:
                easy_to_borrow_count += 1
        
        print("\nStatistics:")
        print("-" * 40)
        print(f"Total shortable: {len(shortable_assets)}")
        print(f"Easy to borrow: {easy_to_borrow_count}")
        print("\nBy exchange:")
        for exchange, count in sorted(exchanges.items(), key=lambda x: x[1], reverse=True):
            print(f"  {exchange}: {count}")
        
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(get_shortable_assets())