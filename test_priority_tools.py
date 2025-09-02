#!/usr/bin/env python3
"""
Priority MCP Tools Testing
Tests the most important MCP tools through direct API calls
"""

import asyncio
import json
import time
from datetime import datetime
import subprocess

class PriorityToolsTester:
    def __init__(self):
        self.test_results = []
        self.backend_url = "http://localhost:8002"
        
    def test_tool(self, tool_name, params=None):
        """Test a tool using direct MCP invocation"""
        start_time = time.time()
        result = {
            "tool": tool_name,
            "params": params or {},
            "success": False,
            "response": "",
            "error": "",
            "execution_time": 0
        }
        
        try:
            # Prepare the command
            cmd = ["uv", "run", "python", "-c", 
                   f"""
import asyncio
from alpaca_mcp_server.tools import *
from alpaca_mcp_server.tools.market_data_tools import *
from alpaca_mcp_server.tools.scanner_tools import *
from alpaca_mcp_server.tools.technical_analysis_tools import *
from alpaca_mcp_server.tools.trading_tools import *
from alpaca_mcp_server.tools.account_tools import *
from alpaca_mcp_server.tools.monitoring_tools import *
from alpaca_mcp_server.tools.system_tools import *

async def test():
    try:
        result = await {tool_name}({', '.join([f'{k}={repr(v)}' for k, v in (params or {}).items()])})
        print(result[:1000] if isinstance(result, str) else str(result)[:1000])
    except Exception as e:
        print(f"ERROR: {{e}}")

asyncio.run(test())
"""]
            
            # Execute the command
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if process.returncode == 0:
                result["success"] = True
                result["response"] = process.stdout.strip()
            else:
                result["error"] = process.stderr.strip()
                
        except subprocess.TimeoutExpired:
            result["error"] = "Tool execution timed out"
        except Exception as e:
            result["error"] = str(e)
            
        result["execution_time"] = time.time() - start_time
        self.test_results.append(result)
        return result
    
    def run_priority_tests(self):
        """Run tests on priority tools"""
        print("\n🎯 Testing Priority MCP Tools")
        print("=" * 60)
        
        # Define priority tools to test
        priority_tools = [
            # Market Data Tools
            ("get_stock_quote", {"symbol": "AAPL"}),
            ("get_stock_snapshots", {"symbols": "AAPL,MSFT"}),
            ("get_stock_bars_intraday", {"symbol": "SPY", "days": 1}),
            ("get_stock_latest_bar", {"symbol": "AAPL"}),
            
            # Scanning Tools
            ("scan_day_trading_opportunities", {}),
            ("scan_explosive_momentum", {"min_percent_change": 10}),
            ("analyze_market_activity_fast", {}),
            
            # Technical Analysis
            ("get_stock_peak_trough_analysis", {"symbols": "AAPL"}),
            ("generate_stock_plot", {"symbols": "SPY", "no_plot": True}),
            
            # Account & Portfolio
            ("get_account_info", {}),
            ("get_positions", {}),
            ("get_orders", {}),
            
            # Market Info
            ("get_market_clock", {}),
            ("get_extended_market_clock", {}),
            ("resource_market_conditions", {}),
            
            # System & Health
            ("health_check", {}),
            ("resource_server_health", {}),
            ("resource_api_status", {}),
        ]
        
        # Test each tool
        for i, (tool_name, params) in enumerate(priority_tools, 1):
            print(f"\n[{i}/{len(priority_tools)}] Testing {tool_name}...")
            print(f"  Parameters: {params}")
            
            result = self.test_tool(tool_name, params)
            
            if result["success"]:
                print(f"  ✅ Success ({result['execution_time']:.2f}s)")
                if result["response"]:
                    preview = result["response"][:200] + "..." if len(result["response"]) > 200 else result["response"]
                    print(f"  Response: {preview}")
            else:
                print(f"  ❌ Failed: {result['error'][:200]}")
                
        # Generate summary
        self.generate_summary()
        
    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total = len(self.test_results)
        successful = sum(1 for r in self.test_results if r["success"])
        failed = total - successful
        
        print(f"\nTotal Tools Tested: {total}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(successful/total*100):.1f}%")
        
        # List failed tools
        if failed > 0:
            print("\n❌ Failed Tools:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['tool']}: {result['error'][:100]}")
                    
        # Save results
        with open("priority_tools_test_results.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "successful": successful,
                    "failed": failed,
                    "success_rate": successful/total*100
                },
                "results": self.test_results
            }, f, indent=2)
            
        print(f"\n💾 Results saved to: priority_tools_test_results.json")

if __name__ == "__main__":
    tester = PriorityToolsTester()
    tester.run_priority_tests()