# Server Management Commands

## restart-server
Restart the Alpaca MCP server
```bash
cd /home/jjoravet/alpaca-mcp-server-enhanced
echo "🔄 Restarting Alpaca MCP Server..."
pkill -f "alpaca_mcp_server" 2>/dev/null || true
sleep 2
./scripts/start_mcp_server.sh
echo "✅ Server restart complete!"
