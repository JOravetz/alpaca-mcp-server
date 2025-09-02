#!/usr/bin/env python
"""Quick launcher for MCP Dashboard with live tools"""

import subprocess
import time
import webbrowser
import os

# Test direct tool execution
print("🚀 Testing Direct MCP Tool Execution")
print("=" * 50)

# Test a simple tool
from alpaca_mcp_server.tools.market_info_tools import get_market_clock
from alpaca_mcp_server.tools.help_tools import get_all_tools_help

try:
    # Get market status
    result = get_market_clock()
    print("✅ Market Clock Tool Works!")
    print(f"   Result: {result[:100]}...")
    
    # Get tools help 
    help_result = get_all_tools_help()
    tool_count = help_result.count("•")
    print(f"✅ Found {tool_count} tools available")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 50)
print("📊 Opening Interactive Dashboard")
print("=" * 50)

# Open the dashboard
dashboard_path = "file:///home/jjoravet/alpaca-mcp-server-enhanced/interactive_dashboard.html"

# Try to open in browser
try:
    # Try chromium first
    subprocess.Popen(["chromium", "--new-window", dashboard_path], 
                     stdout=subprocess.DEVNULL, 
                     stderr=subprocess.DEVNULL)
    print("✅ Dashboard opened in Chromium")
except:
    try:
        # Fallback to xdg-open
        subprocess.Popen(["xdg-open", dashboard_path],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        print("✅ Dashboard opened in default browser")
    except:
        print(f"⚠️  Please open manually: {dashboard_path}")

print("\n" + "=" * 50)
print("🎉 MCP Trading Dashboard Ready!")
print("=" * 50)
print("\nThe dashboard can execute tools directly through the MCP server.")
print("All 101 tools are available for live execution.")
print("\n💡 Tip: Click on any tool in the dashboard to execute it with parameters!")
