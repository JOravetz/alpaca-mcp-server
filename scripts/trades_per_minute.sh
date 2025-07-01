#!/bin/bash

# Parse command line arguments with prefixes
SYMBOLS_FILE="combined.lis"
TRADES_THRESHOLD="1000"

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            SYMBOLS_FILE="$2"
            shift 2
            ;;
        -t|--threshold)
            TRADES_THRESHOLD="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [-f|--file symbols_file] [-t|--threshold trades_threshold]"
            echo "Defaults: -f combined.lis -t 1000"
            echo "Examples:"
            echo "  $0                             # Use defaults"
            echo "  $0 -f test.lis                 # Custom file, default threshold"
            echo "  $0 -t 1000                     # Default file, custom threshold"
            echo "  $0 -f test.lis -t 1000         # Custom file and threshold"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Check if symbols file exists
if [ ! -f "$SYMBOLS_FILE" ]; then
    echo "Error: Symbols file '$SYMBOLS_FILE' not found"
    exit 1
fi

# Check if threshold is a number
if ! [[ "$TRADES_THRESHOLD" =~ ^[0-9]+$ ]]; then
    echo "Error: Trades threshold must be a positive integer"
    exit 1
fi

curl -s -H "APCA-API-KEY-ID: $APCA_API_KEY_ID" -H "APCA-API-SECRET-KEY: $APCA_API_SECRET_KEY" "https://data.alpaca.markets/v2/stocks/snapshots?symbols=$(paste -sd, "$SYMBOLS_FILE")" | jq -r --arg threshold "$TRADES_THRESHOLD" '
[["Symbol", "Trades/Min", "Change%"], 
 ["------", "---------", "-------"]] + 
(to_entries | 
 map(select(.value.minuteBar.n > ($threshold | tonumber))) | 
 map([
   .key, 
   (.value.minuteBar.n | tostring),
   (if .value.prevDailyBar.c and .value.latestTrade.p then
     (((.value.latestTrade.p - .value.prevDailyBar.c) / .value.prevDailyBar.c) * 100 | . * 100 | round | . / 100 | tostring) + "%"
   else
     "N/A"
   end)
 ]) | 
 sort_by(.[1] | tonumber) | 
 reverse) | 
.[] | 
@tsv' | column -t -s $'\t' -R 2,3
