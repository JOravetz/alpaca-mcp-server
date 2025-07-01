#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime

from alpaca.data import StockHistoricalDataClient, StockSnapshotRequest


# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def main():
    parser = argparse.ArgumentParser(description="Fetch stock snapshot data")
    parser.add_argument("-s", "--symbol", required=True, help="Stock symbol to query")
    args = parser.parse_args()

    api_key = os.environ.get("APCA_API_KEY_ID")
    api_secret = os.environ.get("APCA_API_SECRET_KEY")

    if not api_key or not api_secret:
        raise ValueError("API key environment variables not set")

    client = StockHistoricalDataClient(api_key, api_secret)

    symbol = args.symbol.upper()
    request_params = StockSnapshotRequest(symbol_or_symbols=symbol)
    snapshot = client.get_stock_snapshot(request_params)

    # Convert the Snapshot object to a dictionary using model_dump
    if symbol in snapshot:
        # Use model_dump() instead of dict()
        try:
            snapshot_dict = snapshot[symbol].model_dump()
        except AttributeError:
            # Fallback for older versions of pydantic
            snapshot_dict = snapshot[symbol].dict()

        print(json.dumps(snapshot_dict, indent=2, cls=DateTimeEncoder))
    else:
        print(f"No data found for symbol: {symbol}")


if __name__ == "__main__":
    main()
