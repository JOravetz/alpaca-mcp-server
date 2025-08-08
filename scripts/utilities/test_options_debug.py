#!/usr/bin/env python3
"""Standalone test for options functionality."""

import os
import asyncio
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest

async def test_options():
    """Test options functionality directly."""
    try:
        # Create client
        client = OptionHistoricalDataClient(
            api_key=os.getenv('APCA_API_KEY_ID'),
            secret_key=os.getenv('APCA_API_SECRET_KEY')
        )
        print(f"✓ Client created: {type(client)}")
        
        # Test request creation
        request = OptionChainRequest(underlying_symbol="AAPL")
        print(f"✓ Request created: {type(request)}")
        
        # Test API call
        result = client.get_option_chain(request)
        print(f"✓ API call successful: {type(result)}")
        print(f"Result preview: {str(result)[:200]}")
        
    except Exception as e:
        import traceback
        print(f"✗ Error: {e}")
        print(f"Traceback:\n{traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_options())