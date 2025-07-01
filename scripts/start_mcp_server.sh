#!/bin/bash
# Wrapper script to start the Alpaca MCP server with proper environment

# Set up environment
export PYTHONPATH="/home/jjoravet/alpaca-mcp-server-enhanced:$PYTHONPATH"
export MCP_DEBUG=1
export CLAUDE_CODE_TOOL_DISCOVERY=1

# Log startup
echo "Starting Alpaca MCP Server at $(date)" >&2
echo "Python path: $PYTHONPATH" >&2
echo "Working directory: $(pwd)" >&2

# Start the server
cd /home/jjoravet/alpaca-mcp-server-enhanced
exec /home/jjoravet/.local/bin/uv run python -m alpaca_mcp_server