#!/bin/bash

# Start MCP Execution Service
# This service provides REST API endpoints for executing MCP tools, resources, and prompts
# Runs on port 8002 (different from monitoring service on 8001)

echo "🚀 Starting MCP Execution Service on port 8002..."

# Change to project directory
cd "$(dirname "$0")/.."

# Start the service
uv run python -m alpaca_mcp_server.web.mcp_execution_service

echo "✅ MCP Execution Service started successfully"
echo "📊 API Documentation: http://localhost:8002/docs"
echo "🌐 Service Homepage: http://localhost:8002/"