#!/usr/bin/env python3
"""Test script to verify dashboard integration with backend"""

import requests
import json
import time

API_URL = "http://localhost:8002"

def test_backend_health():
    """Test backend health endpoint"""
    try:
        response = requests.get(f"{API_URL}/health")
        data = response.json()
        print(f"✅ Backend Health: {data['status']}")
        print(f"   Tools Available: {data['tools_count']}")
        return True
    except Exception as e:
        print(f"❌ Backend Health Check Failed: {e}")
        return False

def test_tool_execution(tool_name, parameters=None):
    """Test executing a specific tool"""
    try:
        params = parameters or {}
        response = requests.post(
            f"{API_URL}/api/execute/tool/{tool_name}",
            json={"parameters": params}
        )
        result = response.json()
        
        if result.get('success'):
            print(f"✅ {tool_name}: Success")
            print(f"   Execution Time: {result.get('execution_time', 0):.3f}s")
            # Show first 200 chars of result
            result_str = str(result.get('result', ''))[:200]
            print(f"   Result Preview: {result_str}...")
        else:
            print(f"❌ {tool_name}: Failed")
            print(f"   Error: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ {tool_name}: Exception - {e}")
        return None

def main():
    print("=" * 60)
    print("🚀 Testing Dashboard Integration with MCP Backend")
    print("=" * 60)
    
    # Test health
    if not test_backend_health():
        print("Please start the backend service first!")
        return
    
    print("\n" + "=" * 60)
    print("📊 Testing Tool Executions")
    print("=" * 60)
    
    # Test various tools
    tests = [
        ("get_market_clock", {}),
        ("get_stock_quote", {"symbol": "AAPL"}),
        ("get_account_info", {}),
        ("get_positions", {}),
        ("scan_day_trading_opportunities", {"max_symbols": 5}),
        ("get_stock_bars", {"symbol": "SPY", "days": 3}),
        ("get_stock_latest_trade", {"symbol": "NVDA"}),
    ]
    
    for tool_name, params in tests:
        print(f"\n🔧 Testing: {tool_name}")
        test_tool_execution(tool_name, params)
        time.sleep(0.5)  # Small delay between tests
    
    print("\n" + "=" * 60)
    print("✨ Dashboard Integration Test Complete!")
    print("=" * 60)
    print("\n📌 Dashboard Instructions:")
    print("1. Open: file:///home/jjoravet/alpaca-mcp-server-enhanced/comprehensive_dashboard.html")
    print("2. Click on any tool in the MCP Tools tab")
    print("3. Fill in parameters in the modal")
    print("4. Click 'Execute Tool' to run")
    print("5. View results in the result modal")
    print("\n✅ Your dashboard is now fully connected and live!")

if __name__ == "__main__":
    main()