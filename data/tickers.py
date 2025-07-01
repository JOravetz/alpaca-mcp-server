import os
import sys
import argparse
import pandas as pd
import re
from alpaca_trade_api.rest import REST

# Pre-compile regex pattern for symbol validation
SYMBOL_PATTERN = re.compile('^[A-Z]+$')

class TickerList:
    """Fetches a list of tradable assets from the Alpaca API with specific filtering criteria"""
    
    def __init__(self):
        """Initializes the Alpaca API credentials from environment variables"""
        # Get API credentials from environment variables
        self.api_key = os.environ.get('APCA_API_KEY_ID')
        self.secret_key = os.environ.get('APCA_API_SECRET_KEY')
        
        if not self.api_key or not self.secret_key:
            raise ValueError("API keys not found in environment variables APCA_API_KEY_ID and APCA_API_SECRET_KEY")
            
        # Initialize REST API client lazily
        self._rest_api = None

    @property
    def rest_api(self):
        """Lazy initialization of the REST API client"""
        if self._rest_api is None:
            self._rest_api = REST(
                key_id=self.api_key,
                secret_key=self.secret_key,
                base_url='https://paper-api.alpaca.markets'
            )
        return self._rest_api
            
    def is_valid_symbol(self, symbol):
        """
        Validates if a symbol meets our criteria:
        - 4 or fewer characters
        - No special characters
        - Not containing 'TEST'
        """
        # Check length first (fastest check)
        if len(symbol) > 4:
            return False
            
        # Check for TEST substring before regex (string operations are faster than regex)
        if 'TEST' in symbol:
            return False
            
        # Run regex check last (most expensive operation)
        if not SYMBOL_PATTERN.match(symbol):
            return False
            
        return True
        
    def fetch_and_save(self, file_name):
        """
        Fetches the list of active assets, filters based on criteria, 
        and saves to a text file with the provided file name
        """
        try:
            # Fetch the list of active assets from Alpaca API
            assets = self.rest_api.list_assets(status="active")
            
            # Filter assets based on criteria
            valid_assets = [
                asset for asset in assets 
                if (asset.tradable and 
                    self.is_valid_symbol(asset.symbol))
            ]
            
            # Extract symbols and names directly into lists
            symbols = []
            names = []
            for asset in valid_assets:
                symbols.append(asset.symbol)
                names.append(asset.name)
            
            # Create a DataFrame directly from a dictionary
            df = pd.DataFrame({"symbol": symbols, "name": names})
            
            # Sort by symbol
            df.sort_values("symbol", inplace=True)
            
            # Ensure the file has a .txt extension
            if not file_name.endswith('.txt'):
                file_name += '.txt'
                
            # Save the DataFrame directly to a file
            df.to_csv(file_name, sep="|", header=None, index=False, columns=["symbol", "name"])
                
            print(f"Successfully saved {len(symbols)} tradable assets to {file_name}")
            
        except Exception as e:
            print(f"Error: {str(e)}")
            raise

if __name__ == "__main__":
    # Define command-line arguments and parse them
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        default="tickers",
        help="The name of the output file (without extension) to store the fetched list output (default: 'tickers')",
    )
    
    args = parser.parse_args()
    
    try:
        # Create a TickerList object and fetch the list of active assets
        ticker_list = TickerList()
        ticker_list.fetch_and_save(args.file)
    except Exception as e:
        print(f"Failed to fetch and save tickers: {str(e)}")
        sys.exit(1)
