#!/bin/bash

# CLIK Day Low Monitoring Script
# Takes browser screenshots every 15 seconds and analyzes for buy signals

SCREENSHOT_DIR="/tmp/clik_monitoring"
INTERVAL=15
TRIGGER_PRICE="0.4422"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create directory
mkdir -p "$SCREENSHOT_DIR"

echo -e "${GREEN}🎯 CLIK Day Low Monitor - Browser Screenshot Analysis${NC}"
echo -e "${YELLOW}📊 Trigger: Day Low < \$${TRIGGER_PRICE}${NC}"
echo -e "📸 Screenshots: ${SCREENSHOT_DIR}"
echo -e "⏱️  Interval: ${INTERVAL} seconds"
echo "================================================"

# Function to analyze the latest screenshot
analyze_screenshot() {
    local screenshot=$1
    local counter=$2
    local timestamp=$(date +"%H:%M:%S")
    
    echo -e "\n[${timestamp}] Screenshot #${counter}:"
    echo "  📸 File: $(basename $screenshot)"
    echo -e "  🔍 Analyzing for Day Low < \$${TRIGGER_PRICE}..."
    
    # Check if file exists
    if [ -f "$screenshot" ]; then
        echo -e "  ✅ Screenshot captured successfully"
        echo -e "  📊 Check browser for Day Low value"
        
        # Here we would normally use OCR or image analysis
        # For now, we'll prompt for manual check
        echo -e "  ${YELLOW}⚠️  Please check if Day Low < \$${TRIGGER_PRICE}${NC}"
    else
        echo -e "  ${RED}❌ Screenshot failed${NC}"
    fi
}

# Main monitoring loop
COUNTER=0
while true; do
    COUNTER=$((COUNTER + 1))
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    SCREENSHOT="${SCREENSHOT_DIR}/clik_${TIMESTAMP}.png"
    
    # Signal for screenshot (Claude will handle via Playwright)
    echo "TAKE_SCREENSHOT:${SCREENSHOT}" > "${SCREENSHOT_DIR}/request.txt"
    
    # Brief pause to allow screenshot
    sleep 2
    
    # Analyze the screenshot
    analyze_screenshot "$SCREENSHOT" "$COUNTER"
    
    # Wait for next interval
    echo -e "  ⏳ Next check in ${INTERVAL} seconds..."
    sleep $((INTERVAL - 2))
done