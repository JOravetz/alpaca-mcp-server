#!/bin/bash

# Enhanced FastAPI Signal Monitor with Real-time Position Tracking
# Monitors signals + positions + account changes every 30 seconds

LOG_FILE="/tmp/signal_monitor_enhanced.log"
SIGNAL_FILE="/tmp/latest_signals.json"
POSITION_FILE="/tmp/latest_positions.json"
ACCOUNT_FILE="/tmp/latest_account.json"

echo "$(date): Starting enhanced FastAPI signal monitor with streaming integration..." >> "$LOG_FILE"

while true; do
    echo "$(date): === MONITORING CYCLE START ===" >> "$LOG_FILE"
    
    # 1. GET FRESH SIGNALS
    curl -s http://localhost:8001/signals > "$SIGNAL_FILE" 2>/dev/null
    
    # 2. GET CURRENT POSITIONS 
    curl -s http://localhost:8001/positions > "$POSITION_FILE" 2>/dev/null
    
    # 3. GET FASTAPI SERVICE STATUS
    curl -s http://localhost:8001/status > "$ACCOUNT_FILE" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        # ANALYZE FRESH TROUGH SIGNALS (last 2 minutes)
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
        print('NO_SIGNAL_DATA')
except Exception as e:
    print('SIGNAL_ERROR:' + str(e))
")
        
        # ANALYZE CURRENT POSITIONS FOR PROFIT OPPORTUNITIES
        POSITION_ANALYSIS=$(python3 -c "
import json
import sys

try:
    with open('$POSITION_FILE', 'r') as f:
        data = json.load(f)
    
    if 'positions' in data and data['positions']:
        profit_alerts = []
        for pos in data['positions']:
            symbol = pos.get('symbol', 'UNKNOWN')
            unrealized_pl = float(pos.get('unrealized_pl', 0))
            percent_pl = float(pos.get('unrealized_plpc', 0)) * 100
            
            # Alert on any profit > $1000 or > 1%
            if unrealized_pl > 1000 or percent_pl > 1.0:
                profit_alerts.append(f\"{symbol}:+${unrealized_pl:.0f}({percent_pl:+.1f}%)\")
        
        if profit_alerts:
            print('PROFIT_ALERTS:' + ','.join(profit_alerts))
        else:
            print('NO_PROFITS')
    else:
        print('NO_POSITIONS')
except Exception as e:
    print('POSITION_ERROR:' + str(e))
")
        
        # WATCHLIST STATUS
        WATCHLIST_STATUS=$(python3 -c "
import json
try:
    with open('$ACCOUNT_FILE', 'r') as f:
        data = json.load(f)
    print(f\"WATCHLIST_SIZE:{data.get('watchlist_size', 0)}\")
except:
    print('WATCHLIST_ERROR')
")
        
        # LOG AND ALERT RESULTS
        echo "$(date): $WATCHLIST_STATUS" >> "$LOG_FILE"
        
        if [[ "$FRESH_TROUGHS" == FRESH_TROUGHS:* ]]; then
            SIGNALS="${FRESH_TROUGHS#FRESH_TROUGHS:}"
            echo "$(date): 🎯 FRESH TROUGH SIGNALS: $SIGNALS" >> "$LOG_FILE"
            echo "🎯 TRADE ALERT: Fresh trough signals: $SIGNALS"
        fi
        
        if [[ "$POSITION_ANALYSIS" == PROFIT_ALERTS:* ]]; then
            PROFITS="${POSITION_ANALYSIS#PROFIT_ALERTS:}"
            echo "$(date): 💰 PROFIT ALERTS: $PROFITS" >> "$LOG_FILE"
            echo "💰 SELL ALERT: Positions showing profit: $PROFITS"
        fi
        
        if [[ "$FRESH_TROUGHS" == NO_FRESH_TROUGHS && "$POSITION_ANALYSIS" == NO_POSITIONS ]]; then
            echo "$(date): ⭕ No signals, no positions - monitoring..." >> "$LOG_FILE"
            # Every minute (2 cycles), send user status report
            CYCLE_COUNT_FILE="/tmp/cycle_count.txt"
            if [ ! -f "$CYCLE_COUNT_FILE" ]; then
                echo "0" > "$CYCLE_COUNT_FILE"
            fi
            CURRENT_CYCLE=$(cat "$CYCLE_COUNT_FILE")
            NEXT_CYCLE=$((CURRENT_CYCLE + 1))
            echo "$NEXT_CYCLE" > "$CYCLE_COUNT_FILE"
            
            if [ $((NEXT_CYCLE % 2)) -eq 0 ]; then
                echo "**USER REPORT ($(date '+%H:%M %Z'))**: Watchlist: $WATCHLIST_STATUS | No fresh signals | No positions | Monitoring active"
            fi
        fi
        
    else
        echo "$(date): ❌ ERROR: Could not reach FastAPI service" >> "$LOG_FILE"
    fi
    
    echo "$(date): === MONITORING CYCLE END ===" >> "$LOG_FILE"
    
    # Wait 30 seconds for faster monitoring
    sleep 30
done