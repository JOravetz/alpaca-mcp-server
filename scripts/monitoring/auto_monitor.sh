#!/bin/bash

# Automated CLIK monitoring with screenshot analysis
# This script coordinates with Claude to take and analyze screenshots

INTERVAL=15
TRIGGER="0.4422"
COUNT=0

echo "🎯 CLIK AUTO-MONITOR STARTED"
echo "📊 Buy Trigger: Day Low < \$$TRIGGER"
echo "⏱️  Interval: $INTERVAL seconds"
echo "======================================"

# Function to request analysis
request_analysis() {
    local count=$1
    local timestamp=$(date +"%H:%M:%S")
    
    echo ""
    echo "[$timestamp] Analysis #$count"
    echo "----------------------------"
    echo "ACTION: TAKE_SCREENSHOT_AND_ANALYZE"
    echo "TARGET: Day Low value"
    echo "TRIGGER: < \$$TRIGGER"
    echo ""
    
    # Create marker file for Claude to detect
    echo "$count" > /tmp/analyze_now.txt
    
    # Wait a moment for analysis
    sleep 2
    
    # Check for result (Claude will write this)
    if [ -f "/tmp/analysis_result.txt" ]; then
        cat /tmp/analysis_result.txt
        rm /tmp/analysis_result.txt
    else
        echo "⏳ Awaiting analysis..."
    fi
}

# Main loop
while true; do
    COUNT=$((COUNT + 1))
    request_analysis $COUNT
    
    echo "Next check in $INTERVAL seconds..."
    echo ""
    
    sleep $INTERVAL
done