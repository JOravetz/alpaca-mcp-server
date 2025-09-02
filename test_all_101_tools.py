#!/usr/bin/env python3
"""
Live Testing Script for All 101 MCP Tools
Executes each tool with real parameters and validates responses
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import sys
import os

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Complete list of all 101 tools with test parameters
TOOL_TEST_CASES = {
    # Account & Portfolio (10 tools)
    "check_positions_after_order": [{}],
    "check_positions_after_order_fastapi": [{}],
    "close_all_positions": [],  # Skip - modifies account
    "close_position": [],  # Skip - modifies account
    "get_account_info": [{}],
    "get_fastapi_positions": [{}],
    "get_open_position": [{"symbol": "AAPL"}],
    "get_positions": [{}],
    "resource_account_status": [{}],
    "resource_current_positions": [{}],
    
    # Assets & Organization (10 tools)
    "add_symbols_to_fastapi_watchlist": [{"symbols": ["AAPL", "SPY"]}],
    "add_symbols_to_watchlist": [{"symbols": ["AAPL", "SPY"]}],
    "create_watchlist": [],  # Skip - creates permanent watchlist
    "get_all_assets": [{"max_symbol_length": 4, "tradable_only": True}],
    "get_asset_info": [{"symbol": "AAPL"}],
    "get_current_watchlist": [{}],
    "get_watchlists": [{}],
    "remove_symbols_from_fastapi_watchlist": [{"symbols": ["AAPL"]}],
    "remove_symbols_from_watchlist": [{"symbols": ["AAPL"]}],
    "update_watchlist": [],  # Skip - needs watchlist ID
    
    # Help & Debugging (6 tools)
    "cc_debug_tools": [{}],
    "debug_mcp_tools": [{}],
    "get_all_prompts_help": [{}],
    "get_all_tools_help": [{}],
    "get_prompt_help": [{"prompt_name": "startup_prompt"}],
    "get_tool_help": [{"tool_name": "get_stock_quote"}],
    
    # Market Data (22 tools)
    "add_symbols_to_stock_stream": [],  # Requires active stream
    "clear_stock_stream_buffers": [{}],
    "compare_bar_types": [{"symbol": "AAPL", "days": 1}],
    "generate_stock_plot": [{"symbols": "AAPL", "days": 1, "no_plot": True}],
    "get_option_latest_quote": [{"symbol": "AAPL250117C00230000"}],
    "get_stock_bars": [{"symbol": "AAPL", "days": 1}],
    "get_stock_bars_intraday": [{"symbol": "AAPL", "timeframe": "1Min", "days": 1}],
    "get_stock_latest_bar": [{"symbol": "AAPL"}],
    "get_stock_latest_trade": [{"symbol": "AAPL"}],
    "get_stock_peak_trough_analysis": [{"symbols": "AAPL", "days": 1}],
    "get_stock_quote": [{"symbol": "AAPL"}, {"symbol": "SPY"}],
    "get_stock_snapshots": [{"symbols": "AAPL,SPY"}],
    "get_stock_stream_buffer_stats": [{}],
    "get_stock_stream_data": [],  # Requires active stream
    "get_stock_trades": [{"symbol": "AAPL", "days": 1, "limit": 10}],
    "get_volume_bar_stats": [{}],
    "get_volume_bars_from_history": [{"symbol": "AAPL", "days": 1}],
    "list_active_stock_streams": [{}],
    "scan_explosive_stocks_fast": [{"max_results": 5}],
    "start_global_stock_stream": [],  # Skip - starts persistent stream
    "start_volume_bar_streaming": [],  # Skip - starts persistent stream
    "stop_global_stock_stream": [{}],
    
    # Market Info (6 tools)
    "analyze_market_activity_fast": [{"max_results": 5}],
    "get_extended_market_clock": [{}],
    "get_market_calendar": [{"start_date": "2025-01-20", "end_date": "2025-01-24"}],
    "get_market_clock": [{}],
    "resource_market_conditions": [{}],
    "resource_market_momentum": [{"symbol": "SPY"}],
    
    # Monitoring Services (10 tools)
    "get_fastapi_monitoring_status": [{}],
    "get_fastapi_signals": [{}],
    "get_hybrid_monitoring_status": [{}],
    "get_monitoring_alerts": [{"count": 5}],
    "ping_monitoring_service": [{}],
    "start_fastapi_monitoring_service": [],  # Skip - starts service
    "start_hybrid_monitoring": [],  # Skip - starts service
    "stop_fastapi_monitoring_service": [{}],
    "stop_hybrid_monitoring": [{}],
    "verify_monitoring_active": [{}],
    
    # Options Trading (2 tools)
    "get_option_contracts": [{"underlying_symbol": "AAPL", "limit": 5}],
    "get_option_snapshot": [{"symbol": "AAPL250117C00230000"}],
    
    # Order Management (8 tools)
    "cancel_all_orders": [],  # Skip - cancels real orders
    "cancel_order_by_id": [],  # Skip - needs order ID
    "get_orders": [{"status": "all", "limit": 5}],
    "place_extended_hours_order": [],  # Skip - places real order
    "place_option_market_order": [],  # Skip - places real order
    "place_stock_order": [],  # Skip - places real order
    "stream_optimized_order_placement": [],  # Skip - places real order
    "validate_extended_hours_order": [{"symbol": "AAPL", "order_type": "limit"}],
    
    # Technical Analysis (4 tools)
    "analyze_peaks_troughs_fast": [{"symbols": "AAPL", "days": 1}],
    "compare_analyzer_performance": [{"test_symbols": "AAPL,SPY"}],
    "compare_peak_trough_implementations": [{"symbol": "AAPL", "days": 1}],
    "generate_advanced_technical_plots": [{"symbols": "AAPL", "days": 1, "display_plots": False}],
    
    # Real-time Streaming (2 tools)
    "get_enhanced_streaming_analytics": [{"symbol": "AAPL", "analysis_minutes": 5}],
    "stream_aware_price_monitor": [],  # Requires active stream
    
    # Scanners & Analysis (3 tools)
    "scan_after_hours_opportunities": [{"max_symbols": 5}],
    "scan_day_trading_opportunities": [{"max_symbols": 5}],
    "scan_explosive_momentum": [{"min_percent_change": 5}],
    
    # System & Utilities (18 tools)
    "cc_force_refresh": [{}],
    "cc_test_simple": [{}],
    "cleanup": [{"dry_run": True}],  # Dry run only
    "export_mcp_tools_list": [{}],
    "get_corporate_announcements": [{"symbol": "AAPL", "ca_types": ["dividend"], "since": "2025-01-01", "until": "2025-01-31"}],
    "get_current_trading_signals": [{}],
    "get_extended_hours_info": [{}],
    "get_mcp_tool_schema": [{"tool_name": "get_stock_quote"}],
    "get_profit_spike_alerts": [{"count": 5}],
    "get_single_day_pnl": [{"date": "2025-01-23"}],
    "health_check": [{}],
    "list_cleanup_candidates": [{}],
    "resource_api_status": [{}],
    "resource_data_quality": [{}],
    "resource_intraday_pnl": [{}],
    "resource_server_health": [{}],
    "resource_session_status": [{}],
    "search_tools": [{"query": "stock"}]
}


class LiveMCPTester:
    """Execute and validate all 101 MCP tools"""
    
    def __init__(self):
        self.results = {}
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
        
    async def test_tool(self, tool_name: str, test_params: List[Dict]) -> Dict:
        """Test a single tool with given parameters"""
        
        # Handle empty test cases (tools to skip)
        if not test_params:
            self.skipped += 1
            return {
                "tool": tool_name,
                "status": "skipped",
                "reason": "Modifies account or requires specific conditions"
            }
        
        result = {
            "tool": tool_name,
            "status": "pending",
            "test_cases": [],
            "execution_times": []
        }
        
        for params in test_params:
            start_time = time.time()
            
            try:
                # Import the tool dynamically
                if tool_name.startswith("mcp__alpaca-trading__"):
                    # Already prefixed
                    full_tool_name = tool_name
                else:
                    full_tool_name = f"mcp__alpaca-trading__{tool_name}"
                
                # Get the tool function
                module_name = "alpaca_mcp_server.server_components.tool_registrations"
                
                # Try to execute the tool
                try:
                    # Direct execution through MCP
                    import importlib
                    module = importlib.import_module(module_name)
                    
                    # Get all registered tools
                    tools = {}
                    for attr_name in dir(module):
                        if attr_name.startswith("mcp__alpaca_trading__"):
                            tools[attr_name.replace("mcp__alpaca_trading__", "")] = getattr(module, attr_name)
                    
                    if tool_name in tools:
                        tool_func = tools[tool_name]
                        
                        # Execute the tool
                        if asyncio.iscoroutinefunction(tool_func):
                            response = await tool_func(**params)
                        else:
                            response = tool_func(**params)
                        
                        execution_time = time.time() - start_time
                        
                        result["test_cases"].append({
                            "params": params,
                            "success": True,
                            "response_preview": str(response)[:200] if response else "Empty response",
                            "execution_time": execution_time
                        })
                        result["execution_times"].append(execution_time)
                        
                    else:
                        # Tool not found in registered tools
                        result["test_cases"].append({
                            "params": params,
                            "success": False,
                            "error": f"Tool {tool_name} not found in registered tools",
                            "execution_time": 0
                        })
                        
                except ImportError as e:
                    # Try alternative import path
                    result["test_cases"].append({
                        "params": params,
                        "success": False,
                        "error": f"Import error: {str(e)}",
                        "execution_time": 0
                    })
                    
            except Exception as e:
                execution_time = time.time() - start_time
                result["test_cases"].append({
                    "params": params,
                    "success": False,
                    "error": str(e),
                    "execution_time": execution_time
                })
                self.errors.append(f"{tool_name}: {str(e)}")
        
        # Determine overall status
        if all(tc.get("success", False) for tc in result["test_cases"]):
            result["status"] = "passed"
            self.passed += 1
        elif any(tc.get("success", False) for tc in result["test_cases"]):
            result["status"] = "partial"
        else:
            result["status"] = "failed"
            self.failed += 1
        
        # Calculate average execution time
        if result["execution_times"]:
            result["avg_execution_time"] = sum(result["execution_times"]) / len(result["execution_times"])
        
        return result
    
    async def run_all_tests(self):
        """Execute tests for all 101 tools"""
        print("\n" + "="*80)
        print("TESTING ALL 101 MCP TOOLS")
        print("="*80)
        
        total_tools = len(TOOL_TEST_CASES)
        current = 0
        
        for tool_name, test_params in TOOL_TEST_CASES.items():
            current += 1
            print(f"\n[{current}/{total_tools}] Testing: {tool_name}")
            
            result = await self.test_tool(tool_name, test_params)
            self.results[tool_name] = result
            
            # Print status
            status_icon = "✅" if result["status"] == "passed" else \
                         "⚠️" if result["status"] == "partial" else \
                         "❌" if result["status"] == "failed" else \
                         "⏭️"
            
            print(f"  {status_icon} Status: {result['status']}")
            
            if result.get("avg_execution_time"):
                print(f"  ⚡ Avg time: {result['avg_execution_time']:.3f}s")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        
        return self.results
    
    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tools: 101")
        print(f"Tested: {self.passed + self.failed}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Skipped: {self.skipped} ⏭️")
        
        if self.errors:
            print("\nTop Errors:")
            for error in self.errors[:5]:
                print(f"  • {error}")
        
        # Save results to file
        with open("test_results_101_tools.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": 101,
                    "passed": self.passed,
                    "failed": self.failed,
                    "skipped": self.skipped
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\nResults saved to: test_results_101_tools.json")


async def main():
    """Main execution"""
    tester = LiveMCPTester()
    
    # First verify server health
    try:
        from alpaca_mcp_server.tools.debug_tools import health_check
        health = health_check()
        print(f"Server Health Check: {health[:50]}...")
    except Exception as e:
        print(f"Warning: Could not verify server health: {e}")
    
    # Run all tests
    await tester.run_all_tests()
    
    # Generate summary
    tester.generate_summary()
    
    print("\n✅ Testing complete!")


if __name__ == "__main__":
    asyncio.run(main())