#!/bin/bash

# Simple minute reporter that outputs directly to console
while true; do
    # Get watchlist status
    WATCHLIST_STATUS=$(curl -s http://localhost:8001/status | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(f\"Size:{data.get('monitoring_status', {}).get('watchlist_size', 0)}\")
except:
    print('ERROR')
")
    
    # Get signals
    SIGNALS=$(curl -s http://localhost:8001/signals | python3 -c "
import json
import sys
from datetime import datetime, timezone
try:
    data = json.load(sys.stdin)
    fresh_count = 0
    if 'current_signals' in data:
        now = datetime.now(timezone.utc)
        for signal in data['current_signals']:
            if signal.get('signal_type') == 'fresh_trough' and signal.get('bars_ago', 999) <= 2:
                try:
                    detected_time = datetime.fromisoformat(signal['detected_at'].replace('Z', '+00:00'))
                    age_seconds = (now - detected_time).total_seconds()
                    if age_seconds <= 120:
                        fresh_count += 1
                except:
                    pass
    print(f\"Fresh:{fresh_count}\")
except:
    print('ERROR')
")
    
    # Get positions
    POSITIONS=$(curl -s http://localhost:8001/positions | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    pos_count = data.get('position_count', 0)
    print(f\"Positions:{pos_count}\")
except:
    print('ERROR')
")
    
    echo "**MINUTE REPORT $(date '+%H:%M:%S')**: Watchlist: $WATCHLIST_STATUS | Signals: $SIGNALS | $POSITIONS | Monitoring active"
    
    sleep 60
done