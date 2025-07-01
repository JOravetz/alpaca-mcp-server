#!/bin/bash

# Continuous FastAPI Signal Monitor for Fresh Trough Trading
# Checks every 60 seconds for fresh buy signals

LOG_FILE="/tmp/signal_monitor.log"
SIGNAL_FILE="/tmp/latest_signals.json"

echo "$(date): Starting continuous FastAPI signal monitor..." >> "$LOG_FILE"

while true; do
    echo "$(date): Checking FastAPI signals..." >> "$LOG_FILE"
    
    # Get current signals from FastAPI
    curl -s http://localhost:8001/signals > "$SIGNAL_FILE" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        # Extract fresh trough signals from last 2 minutes (120 seconds)
        FRESH_TROUGHS=$(python3 -c "
import json
import sys
from datetime import datetime, timezone

try:
    with open('$SIGNAL_FILE', 'r') as f:
        data = json.load(f)
    
    if 'current_signals' in data:
        fresh_signals = []
        now = datetime.now(timezone.utc)
        
        for signal in data['current_signals']:
            if signal.get('signal_type') == 'fresh_trough' and signal.get('bars_ago', 999) <= 2:
                # Check if detected within last 2 minutes
                try:
                    detected_time = datetime.fromisoformat(signal['detected_at'].replace('Z', '+00:00'))
                    age_seconds = (now - detected_time).total_seconds()
                    if age_seconds <= 120:  # Fresh within 2 minutes
                        fresh_signals.append(f\"{signal['symbol']}@{signal['price']}\")
                except:
                    pass
        
        if fresh_signals:
            print('FRESH_TROUGHS:' + ','.join(fresh_signals))
        else:
            print('NO_FRESH_TROUGHS')
    else:
        print('NO_DATA')
except Exception as e:
    print('ERROR:' + str(e))
")
        
        if [[ "$FRESH_TROUGHS" == FRESH_TROUGHS:* ]]; then
            SIGNALS="${FRESH_TROUGHS#FRESH_TROUGHS:}"
            echo "$(date): FRESH TROUGH SIGNALS DETECTED: $SIGNALS" >> "$LOG_FILE"
            echo "ALERT: Fresh trough signals found: $SIGNALS"
        else
            echo "$(date): No fresh trough signals found" >> "$LOG_FILE"
        fi
    else
        echo "$(date): ERROR: Could not reach FastAPI service" >> "$LOG_FILE"
    fi
    
    # Wait 60 seconds before next check
    sleep 60
done