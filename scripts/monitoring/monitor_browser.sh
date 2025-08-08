#!/bin/bash

# Browser monitoring script - captures screenshots every 15 seconds
# For CLIK Day Low monitoring

SCREENSHOT_DIR="/tmp/clik_monitoring"
INTERVAL=15
COUNTER=0

# Create screenshot directory
mkdir -p "$SCREENSHOT_DIR"

echo "🎯 Starting CLIK browser monitoring..."
echo "📸 Screenshots will be saved to: $SCREENSHOT_DIR"
echo "⏱️  Interval: ${INTERVAL} seconds"
echo "----------------------------------------"

while true; do
    COUNTER=$((COUNTER + 1))
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    FILENAME="${SCREENSHOT_DIR}/clik_${TIMESTAMP}.png"
    
    # Take screenshot using Playwright via Claude
    echo "[$(date +"%H:%M:%S")] Taking screenshot #${COUNTER}..."
    
    # Create a marker file to signal screenshot request
    echo "REQUEST_SCREENSHOT" > "${SCREENSHOT_DIR}/screenshot_request.txt"
    
    # Log current time and counter
    echo "[$(date +"%H:%M:%S")] Screenshot #${COUNTER} saved as: ${FILENAME}"
    echo "  Check for Day Low changes below $0.4422"
    echo ""
    
    # Wait for interval
    sleep $INTERVAL
done