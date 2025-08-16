#!/bin/bash
# Pre-analyze hook - validate symbols and prepare environment
# Receives JSON via stdin with symbols list

# Read JSON from stdin
read -r json_input

# Extract symbols count
symbols_count=$(echo "$json_input" | jq '.symbols | length')

echo "🔍 Pre-analyze: Validating $symbols_count symbols"

# Check if market is open
market_status=$(curl -s "http://localhost:8000/market/status" 2>/dev/null || echo "offline")

# Log start time
echo "$(date '+%Y-%m-%d %H:%M:%S') - Analysis started: $symbols_count symbols" >> /tmp/analyze.log

# Validate symbols are tradeable (could check against Alpaca API)
# For now, just ensure they're uppercase
echo "$json_input" | jq -r '.symbols[]' | while read symbol; do
    if [[ ! "$symbol" =~ ^[A-Z]+$ ]]; then
        echo "⚠️  Warning: Invalid symbol format: $symbol"
    fi
done

# Clear any stale cache
rm -f /tmp/peaks_cache_*.json 2>/dev/null

echo "✅ Pre-analyze complete"