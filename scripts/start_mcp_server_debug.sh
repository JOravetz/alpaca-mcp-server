#!/bin/bash
# Debug wrapper script to start the Alpaca MCP server

# Set up environment
export PYTHONPATH="/home/jjoravet/alpaca-mcp-server-enhanced:$PYTHONPATH"
export MCP_DEBUG=1
export CLAUDE_CODE_TOOL_DISCOVERY=1
export PYTHONUNBUFFERED=1

# Create a log file for debugging
LOG_FILE="/tmp/alpaca_mcp_server_debug.log"

# Log startup
echo "=== Starting Alpaca MCP Server at $(date) ===" >> "$LOG_FILE"
echo "Python path: $PYTHONPATH" >> "$LOG_FILE"
echo "Working directory: $(pwd)" >> "$LOG_FILE"
echo "Environment variables:" >> "$LOG_FILE"
env | grep -E "(MCP|CLAUDE|ALPACA|APCA)" | sed 's/SECRET[^=]*=.*/SECRET=***/' >> "$LOG_FILE"

# Start the server with error logging
cd /home/jjoravet/alpaca-mcp-server-enhanced
exec /home/jjoravet/.local/bin/uv run python -m alpaca_mcp_server 2>> "$LOG_FILE"