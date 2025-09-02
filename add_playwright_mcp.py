#!/usr/bin/env python3
"""
Script to add Playwright MCP server to Claude configuration
"""
import json
import os
from pathlib import Path

def add_playwright_mcp():
    """Add Playwright MCP server to Claude configuration"""
    
    # Path to Claude config
    claude_config_path = Path.home() / ".claude.json"
    
    # Read current configuration
    with open(claude_config_path, 'r') as f:
        config = json.load(f)
    
    # Define Playwright MCP server configuration
    playwright_config = {
        "command": "npx",
        "args": ["-y", "@playwright/mcp"],
        "capabilities": {
            "tools": {"listChanged": True}
        }
    }
    
    # Add to mcpServers at the root level (not project-specific)
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Add playwright server
    config["mcpServers"]["playwright"] = playwright_config
    
    # Also ensure the alpaca-trading and sec-edgar servers are at root level
    alpaca_config = {
        "command": "/home/jjoravet/.local/bin/uv",
        "args": [
            "--directory", 
            "/home/jjoravet/alpaca-mcp-server-enhanced",
            "run",
            "python",
            "-m",
            "alpaca_mcp_server"
        ],
        "env": {
            "ALPACA_API_KEY_ID": "${APCA_API_KEY_ID}",
            "ALPACA_API_SECRET_KEY": "${APCA_API_SECRET_KEY}",
            "ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
            "LOG_LEVEL": "INFO",
            "MCP_DEBUG": "1",
            "CLAUDE_CODE_TOOL_DISCOVERY": "1",
            "PYTHONPATH": "/home/jjoravet/alpaca-mcp-server-enhanced"
        },
        "capabilities": {
            "tools": {"listChanged": True},
            "resources": {"subscribe": True},
            "prompts": {"listChanged": True}
        }
    }
    
    sec_edgar_config = {
        "command": "bash",
        "args": ["-c", "cd /home/jjoravet/claude_stock_analyzer/sec-edgar-mcp && ~/.local/bin/uv run python -m sec_edgar_mcp.server"],
        "env": {
            "SEC_EDGAR_USER_AGENT": "Joe O (jjoravet@yahoo.com)"
        }
    }
    
    # Add all servers
    config["mcpServers"]["alpaca-trading"] = alpaca_config
    config["mcpServers"]["sec-edgar"] = sec_edgar_config
    
    # Backup the original file
    backup_path = claude_config_path.with_suffix('.json.backup')
    with open(backup_path, 'w') as f:
        with open(claude_config_path, 'r') as original:
            f.write(original.read())
    
    # Write updated configuration
    with open(claude_config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Successfully added Playwright MCP server to Claude configuration")
    print(f"📁 Backup saved to: {backup_path}")
    print("\n🔄 Please restart Claude Code for the changes to take effect:")
    print("   1. Press Esc to exit Claude Code")
    print("   2. Run 'claude' to restart")
    print("\nThe Playwright server will connect automatically when you restart.")

if __name__ == "__main__":
    add_playwright_mcp()