#!/usr/bin/env python3
"""Test if the new MCP tools are available"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_direct_import():
    """Test direct import and execution"""
    print("Testing direct import...")
    
    from alpaca_mcp_server.tools.c_stock_analyzer_wrapper import analyze_market_activity_fast
    
    result = await analyze_market_activity_fast(
        symbols="PMNT,PPSI,DFLI",
        max_results=3,
        max_price=100.0,
        min_percent_change=0.0,
        min_trades=0,
        sort_by="percent_change"
    )
    
    print("✅ Direct import works!")
    print(result)
    return True

async def test_mcp_registration():
    """Test if tool is registered in MCP"""
    print("\nTesting MCP registration...")
    
    try:
        # Import the server module
        from alpaca_mcp_server.server import create_server
        from fastmcp import FastMCP
        
        # Create MCP instance
        mcp = FastMCP("alpaca-trading")
        
        # Import registration functions
        from alpaca_mcp_server.server_components.tool_registrations import register_scanner_tools
        
        # Register the tools
        register_scanner_tools(mcp)
        
        # Check if tool exists
        tools = mcp.list_tools()
        
        found_tools = [t for t in tools if 'analyze_market' in str(t).lower() or 'fast' in str(t).lower()]
        
        if found_tools:
            print(f"✅ Found {len(found_tools)} matching tools in MCP!")
            for tool in found_tools[:3]:
                print(f"  - {tool}")
        else:
            print("❌ Tools not found in MCP registration")
            print(f"Total tools registered: {len(tools)}")
            
    except Exception as e:
        print(f"❌ Error testing MCP: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_direct_import()
    await test_mcp_registration()

if __name__ == "__main__":
    asyncio.run(main())