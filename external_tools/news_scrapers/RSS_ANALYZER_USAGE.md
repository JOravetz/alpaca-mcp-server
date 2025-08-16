# RSS Feed Analyzer - File Input Enhancement

## Overview
Enhanced Yahoo Finance RSS feed fetcher with file input capability for batch processing of stock symbols.

## New Features
- **File Input Support** (`-i/--input-file`): Read symbols from a text file
- **Flexible Format**: Supports one symbol per line or comma-separated
- **Comment Support**: Lines starting with `#` are treated as comments
- **Batch Processing**: Efficiently fetches RSS feeds for multiple stocks in parallel

## Usage Examples

### Read from File
```bash
# Basic file input
python yf_rss.py -i ~/autotrade/momentum.lis

# Compact format with limited articles
python yf_rss.py -i watchlist.txt -f compact -n 5

# Combine file and command-line symbols
python yf_rss.py AAPL MSFT -i more_symbols.txt

# Save results to JSON
python yf_rss.py -i symbols.txt -o results.json
```

### File Format
```text
# Tech stocks
AAPL
MSFT, GOOGL
NVDA

# Energy sector
XOM
CVX
```

## Analysis Results (2025-08-16)

### Top 5 Stock Picks from 52 Analyzed
Based on RSS feed analysis with inverse Cramer filter applied:

1. **ASTS** - Space/5G play with Trump deregulation catalyst (+20.86% on satellite news)
2. **DAVE** - 416% YTD gain with $125M buyback expansion
3. **VST** - Jefferies PT raised from $145 to $241 (66% upside)
4. **CVNA** - "Next 100X stock" per successful hedge fund manager
5. **RKLB** - Rocket Lab acquiring Geost for defense contracts

### Stocks to Avoid (Cramer Cursed)
- **EAT** - Cramer called it a "winner" (inverse signal)
- **CLS** - Cramer "Strong Buy" (typically marks the top)
- **QBTS** - Cramer "believer" in quantum (bubble indicator)

### Key Themes Identified
- **Space/Defense Momentum**: ASTS, RKLB benefiting from regulatory tailwinds
- **AI/Tech Surge**: NVDA, PLTR with significant developments
- **Crypto Exposure**: MSTR with Bitcoin holdings, ARKW accumulating
- **Dead Stocks**: ATFV, SPBC with zero news coverage

## Implementation Details

### New Function: `read_symbols_from_file()`
- Reads symbols from text file
- Handles comments and empty lines
- Supports both single and comma-separated formats
- Returns deduplicated list of symbols

### Modified Argument Parser
- Added `-i/--input-file` option
- Updated help text with file format examples
- Combines file and CLI symbols seamlessly

## Testing
Successfully tested with `~/autotrade/momentum.lis`:
- Processed 52 unique symbols
- Fetched 245 total articles
- Identified high-momentum opportunities
- Applied inverse Cramer filter for contrarian signals