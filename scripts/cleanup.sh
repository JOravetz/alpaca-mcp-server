#!/bin/bash
# Cleanup script - preserves compiled binaries in bin/

echo "🧹 Starting cleanup of alpaca-mcp-server-enhanced..."

# Python cache directories (regenerated automatically)
echo "Removing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Backup files
echo "Removing backup files..."
rm -f combined.lis.bak.*
rm -f combined.sorted.*.lis
rm -f output.avo.2*.dat  # Keep the latest symlinked one
rm -f real_time_analysis_2*.json  # Keep the base one if exists

# Log files (archive them)
echo "Archiving log files..."
mkdir -p logs/archive
mv analyzer_stderr*.log logs/archive/ 2>/dev/null
mv fastapi_monitoring.log logs/archive/ 2>/dev/null

# Test/temporary JSON files
echo "Removing temporary JSON files..."
rm -f proof_test.json
rm -f tesla_proof.json
rm -f previous_results.json
rm -f stock_analyzer_json.json
rm -f momentum_rss.json
rm -f market_analysis.json

# Old documentation (review first)
echo "Removing old documentation..."
# rm -rf docs_old  # After reviewing if anything needs to be kept

echo "✅ Cleanup complete!"
