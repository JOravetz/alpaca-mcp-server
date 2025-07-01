#!/bin/bash

# CERO Automated Trading Monitor
# Checks for fresh trough signals every 30 seconds
# Executes $50,000 buy when signal detected
# Uses real-time streaming for profit exit

# Configuration
SYMBOL="CERO"
POSITION_SIZE="50000"
FRESH_SIGNAL_MAX_AGE=5  # bars
TIMEFRAME="1Min"
WINDOW=11
LOOKAHEAD=1
FEED="sip"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="/home/jjoravet/alpaca-mcp-server-enhanced/cero_trading.log"
POSITION_FILE="/home/jjoravet/alpaca-mcp-server-enhanced/cero_position.txt"

# Initialize
echo "$(date '+%Y-%m-%d %H:%M:%S') - CERO Automated Trading Monitor Started" | tee -a "$LOG_FILE"
echo "Position Size: \$${POSITION_SIZE}" | tee -a "$LOG_FILE"
echo "Fresh Signal Max Age: ${FRESH_SIGNAL_MAX_AGE} bars" | tee -a "$LOG_FILE"
echo "----------------------------------------" | tee -a "$LOG_FILE"

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check for fresh trough signal
check_trough_signal() {
    local output
    local signal_type
    local signal_age
    local signal_price
    local current_price
    local change_pct
    
    # Run the MCP analysis (no plot generation)
    output=$(python3 -c "
import subprocess
import json
import sys

try:
    # Call the MCP tool via the alpaca-mcp-server
    result = subprocess.run([
        'python3', '-c', '''
import asyncio
import sys
sys.path.append(\"/home/jjoravet/alpaca-mcp-server-enhanced\")
from alpaca_mcp_server.tools.plot_py_tool import generate_stock_plot

async def main():
    result = await generate_stock_plot(
        symbols=\"${SYMBOL}\",
        timeframe=\"${TIMEFRAME}\", 
        days=1,
        window=${WINDOW},
        lookahead=${LOOKAHEAD},
        feed=\"${FEED}\",
        verbose=False,
        no_plot=True
    )
    print(result)

asyncio.run(main())
'''
    ], capture_output=True, text=True, timeout=30)
    
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f\"ERROR: {result.stderr}\", file=sys.stderr)
        sys.exit(1)
        
except Exception as e:
    print(f\"ERROR: {str(e)}\", file=sys.stderr)
    sys.exit(1)
")
    
    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to get signal analysis"
        return 1
    fi
    
    # Parse the output for signal information
    signal_type=$(echo "$output" | grep -oP '(?<=Signal    Ago       Signal)[^|]*' | grep -oP '^[^T]*[T|P]' | tail -1)
    signal_age=$(echo "$output" | grep -oP '(?<=CERO\s+)[^T]*T\s+\K\d+' | tail -1)
    
    if [[ -z "$signal_age" ]]; then
        signal_age=$(echo "$output" | grep -oP '(?<=CERO\s+)[^P]*P\s+\K\d+' | tail -1)
        signal_type="P"
    else
        signal_type="T"
    fi
    
    # Extract current price and signal price
    current_price=$(echo "$output" | grep -oP 'Current \$\s*\K[\d.]+' | tail -1)
    signal_price=$(echo "$output" | grep -oP 'Signal \$\s*\K[\d.]+' | tail -1)
    change_pct=$(echo "$output" | grep -oP 'Change%\s*\K[-+]?[\d.]+' | tail -1)
    
    # Return the parsed data
    echo "${signal_type}|${signal_age}|${signal_price}|${current_price}|${change_pct}"
}

# Function to execute buy order
execute_buy_order() {
    local entry_price=$1
    local shares=$(echo "scale=0; $POSITION_SIZE / $entry_price" | bc)
    
    log_message "🚀 EXECUTING BUY ORDER: $shares shares at \$$entry_price"
    
    # Calculate limit price (slightly above current for quick fill)
    local limit_price=$(echo "scale=4; $entry_price * 1.001" | bc)
    
    # Execute buy order via MCP
    local order_result
    order_result=$(python3 -c "
import asyncio
import sys
sys.path.append('/home/jjoravet/alpaca-mcp-server-enhanced')
from alpaca_mcp_server.tools.order_tools import place_stock_order

async def main():
    result = await place_stock_order(
        symbol='${SYMBOL}',
        side='buy',
        quantity=${shares},
        order_type='limit',
        limit_price=${limit_price},
        time_in_force='day'
    )
    print(result)

asyncio.run(main())
")
    
    if [[ $order_result == *"successfully"* ]]; then
        log_message "✅ BUY ORDER PLACED: $order_result"
        echo "${SYMBOL}|${shares}|${limit_price}|$(date '+%Y-%m-%d %H:%M:%S')" > "$POSITION_FILE"
        return 0
    else
        log_message "❌ BUY ORDER FAILED: $order_result"
        return 1
    fi
}

# Function to monitor position for profit exit
monitor_position_for_exit() {
    local entry_price=$1
    local shares=$2
    
    log_message "📊 Starting real-time monitoring for profit exit..."
    
    # Start streaming monitoring in background
    python3 -c "
import asyncio
import sys
import time
sys.path.append('/home/jjoravet/alpaca-mcp-server-enhanced')
from alpaca_mcp_server.tools.streaming_tools import stream_aware_price_monitor

async def monitor_exit():
    while True:
        try:
            result = await stream_aware_price_monitor(
                symbol='${SYMBOL}',
                analysis_seconds=10
            )
            
            # Check for profit conditions in the streaming data
            if 'spike' in result.lower() or 'profit' in result.lower():
                print('PROFIT_SIGNAL_DETECTED')
                break
                
            time.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f'Monitoring error: {e}')
            time.sleep(10)

asyncio.run(monitor_exit())
" &
    
    local monitor_pid=$!
    echo $monitor_pid > "/tmp/cero_monitor.pid"
    
    log_message "📈 Position monitoring started (PID: $monitor_pid)"
}

# Function to execute sell order
execute_sell_order() {
    if [[ ! -f "$POSITION_FILE" ]]; then
        log_message "❌ No position file found"
        return 1
    fi
    
    local position_data=$(cat "$POSITION_FILE")
    local shares=$(echo "$position_data" | cut -d'|' -f2)
    
    log_message "💰 EXECUTING SELL ORDER: $shares shares"
    
    # Get current price for limit order
    local current_price
    current_price=$(python3 -c "
import asyncio
import sys
sys.path.append('/home/jjoravet/alpaca-mcp-server-enhanced')
from alpaca_mcp_server.tools.market_data_tools import get_stock_quote

async def main():
    result = await get_stock_quote('${SYMBOL}')
    print(result)

asyncio.run(main())
" | grep -oP 'Ask: \$\K[\d.]+' | head -1)
    
    # Set limit price slightly below current ask for quick fill
    local limit_price=$(echo "scale=4; $current_price * 0.999" | bc)
    
    # Execute sell order
    local order_result
    order_result=$(python3 -c "
import asyncio
import sys
sys.path.append('/home/jjoravet/alpaca-mcp-server-enhanced')
from alpaca_mcp_server.tools.order_tools import place_stock_order

async def main():
    result = await place_stock_order(
        symbol='${SYMBOL}',
        side='sell',
        quantity=${shares},
        order_type='limit',
        limit_price=${limit_price},
        time_in_force='day'
    )
    print(result)

asyncio.run(main())
")
    
    if [[ $order_result == *"successfully"* ]]; then
        log_message "✅ SELL ORDER PLACED: $order_result"
        rm -f "$POSITION_FILE"
        
        # Kill monitoring process
        if [[ -f "/tmp/cero_monitor.pid" ]]; then
            local monitor_pid=$(cat "/tmp/cero_monitor.pid")
            kill $monitor_pid 2>/dev/null
            rm -f "/tmp/cero_monitor.pid"
        fi
        
        return 0
    else
        log_message "❌ SELL ORDER FAILED: $order_result"
        return 1
    fi
}

# Main monitoring loop
main_loop() {
    local cycle=0
    local in_position=false
    
    while true; do
        cycle=$((cycle + 1))
        
        echo -e "${CYAN}=== MONITORING CYCLE $cycle - $(date '+%H:%M:%S') ===${NC}"
        
        # Check if we have an open position
        if [[ -f "$POSITION_FILE" ]]; then
            in_position=true
            echo -e "${YELLOW}📊 In position - monitoring for exit...${NC}"
            
            # Check if profit signal detected
            if [[ -f "/tmp/cero_profit_signal" ]]; then
                echo -e "${GREEN}💰 PROFIT SIGNAL DETECTED!${NC}"
                execute_sell_order
                in_position=false
                rm -f "/tmp/cero_profit_signal"
            fi
        else
            in_position=false
            
            # Check for fresh trough signal
            echo -e "${BLUE}🔍 Checking for fresh trough signal...${NC}"
            
            local signal_data
            signal_data=$(check_trough_signal)
            
            if [ $? -eq 0 ]; then
                IFS='|' read -r signal_type signal_age signal_price current_price change_pct <<< "$signal_data"
                
                echo -e "${PURPLE}Signal: $signal_type | Age: ${signal_age} bars | Signal: \$${signal_price} | Current: \$${current_price} | Change: ${change_pct}%${NC}"
                
                if [[ "$signal_type" == "T" ]] && [[ "$signal_age" -le "$FRESH_SIGNAL_MAX_AGE" ]]; then
                    echo -e "${GREEN}🚀 FRESH TROUGH SIGNAL DETECTED!${NC}"
                    echo -e "${GREEN}   Age: ${signal_age} bars (≤${FRESH_SIGNAL_MAX_AGE})${NC}"
                    echo -e "${GREEN}   Trough: \$${signal_price} | Current: \$${current_price}${NC}"
                    
                    execute_buy_order "$current_price"
                    
                    if [ $? -eq 0 ]; then
                        monitor_position_for_exit "$current_price" "$(echo "scale=0; $POSITION_SIZE / $current_price" | bc)"
                        in_position=true
                    fi
                else
                    if [[ "$signal_type" == "P" ]]; then
                        echo -e "${RED}❌ PEAK signal detected - waiting for trough (${signal_age} bars old)${NC}"
                    else
                        echo -e "${RED}❌ Trough signal too old (${signal_age} > ${FRESH_SIGNAL_MAX_AGE} bars)${NC}"
                    fi
                fi
            else
                echo -e "${RED}❌ Failed to get signal data${NC}"
            fi
        fi
        
        # Wait 30 seconds with status update
        echo -e "${CYAN}⏳ Waiting 30 seconds... (Monitor active - $(date '+%H:%M:%S'))${NC}"
        echo ""
        sleep 30
    done
}

# Cleanup function
cleanup() {
    log_message "🛑 Shutting down CERO monitor..."
    
    # Kill monitoring process if running
    if [[ -f "/tmp/cero_monitor.pid" ]]; then
        local monitor_pid=$(cat "/tmp/cero_monitor.pid")
        kill $monitor_pid 2>/dev/null
        rm -f "/tmp/cero_monitor.pid"
    fi
    
    # Clean up temp files
    rm -f "/tmp/cero_profit_signal"
    
    log_message "👋 CERO monitor stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check dependencies
if ! command -v bc &> /dev/null; then
    echo "Error: bc calculator not found. Install with: sudo apt-get install bc"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# Start the main loop
echo -e "${GREEN}🚀 CERO Automated Trading Monitor Started${NC}"
echo -e "${GREEN}   Symbol: $SYMBOL${NC}"
echo -e "${GREEN}   Position Size: \$${POSITION_SIZE}${NC}"
echo -e "${GREEN}   Fresh Signal Max Age: ${FRESH_SIGNAL_MAX_AGE} bars${NC}"
echo -e "${GREEN}   Check Interval: 30 seconds${NC}"
echo -e "${GREEN}   Log File: $LOG_FILE${NC}"
echo ""

main_loop