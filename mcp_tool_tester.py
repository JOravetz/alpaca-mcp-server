#!/usr/bin/env python3
"""
MCP Tool Testing Framework for Alpaca Trading Server
Tests all 101 available MCP tools with comprehensive validation
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_tool_tests.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Complete inventory of all 101 MCP tools organized by category
TOOL_INVENTORY = {
    "Account & Portfolio": [
        "check_positions_after_order",
        "check_positions_after_order_fastapi", 
        "close_all_positions",
        "close_position",
        "get_account_info",
        "get_fastapi_positions",
        "get_open_position",
        "get_positions",
        "resource_account_status",
        "resource_current_positions"
    ],
    "Assets & Organization": [
        "add_symbols_to_fastapi_watchlist",
        "add_symbols_to_watchlist",
        "create_watchlist",
        "get_all_assets",
        "get_asset_info",
        "get_current_watchlist",
        "get_watchlists",
        "remove_symbols_from_fastapi_watchlist",
        "remove_symbols_from_watchlist",
        "update_watchlist"
    ],
    "Help & Debugging": [
        "cc_debug_tools",
        "debug_mcp_tools",
        "get_all_prompts_help",
        "get_all_tools_help",
        "get_prompt_help",
        "get_tool_help"
    ],
    "Market Data": [
        "add_symbols_to_stock_stream",
        "clear_stock_stream_buffers",
        "compare_bar_types",
        "generate_stock_plot",
        "get_option_latest_quote",
        "get_stock_bars",
        "get_stock_bars_intraday",
        "get_stock_latest_bar",
        "get_stock_latest_trade",
        "get_stock_peak_trough_analysis",
        "get_stock_quote",
        "get_stock_snapshots",
        "get_stock_stream_buffer_stats",
        "get_stock_stream_data",
        "get_stock_trades",
        "get_volume_bar_stats",
        "get_volume_bars_from_history",
        "list_active_stock_streams",
        "scan_explosive_stocks_fast",
        "start_global_stock_stream",
        "start_volume_bar_streaming",
        "stop_global_stock_stream"
    ],
    "Market Info": [
        "analyze_market_activity_fast",
        "get_extended_market_clock",
        "get_market_calendar",
        "get_market_clock",
        "resource_market_conditions",
        "resource_market_momentum"
    ],
    "Monitoring Services": [
        "get_fastapi_monitoring_status",
        "get_fastapi_signals",
        "get_hybrid_monitoring_status",
        "get_monitoring_alerts",
        "ping_monitoring_service",
        "start_fastapi_monitoring_service",
        "start_hybrid_monitoring",
        "stop_fastapi_monitoring_service",
        "stop_hybrid_monitoring",
        "verify_monitoring_active"
    ],
    "Options Trading": [
        "get_option_contracts",
        "get_option_snapshot"
    ],
    "Order Management": [
        "cancel_all_orders",
        "cancel_order_by_id",
        "get_orders",
        "place_extended_hours_order",
        "place_option_market_order",
        "place_stock_order",
        "stream_optimized_order_placement",
        "validate_extended_hours_order"
    ],
    "Technical Analysis": [
        "analyze_peaks_troughs_fast",
        "compare_analyzer_performance",
        "compare_peak_trough_implementations",
        "generate_advanced_technical_plots"
    ],
    "Real-time Streaming": [
        "get_enhanced_streaming_analytics",
        "stream_aware_price_monitor"
    ],
    "Scanners & Analysis": [
        "scan_after_hours_opportunities",
        "scan_day_trading_opportunities",
        "scan_explosive_momentum"
    ],
    "System & Utilities": [
        "cc_force_refresh",
        "cc_test_simple",
        "cleanup",
        "export_mcp_tools_list",
        "get_corporate_announcements",
        "get_current_trading_signals",
        "get_extended_hours_info",
        "get_mcp_tool_schema",
        "get_profit_spike_alerts",
        "get_single_day_pnl",
        "health_check",
        "list_cleanup_candidates",
        "resource_api_status",
        "resource_data_quality",
        "resource_intraday_pnl",
        "resource_server_health",
        "resource_session_status",
        "search_tools"
    ]
}

# Tool parameter definitions for testing
TOOL_PARAMETERS = {
    # Market Data Tools
    "get_stock_quote": {
        "required": ["symbol"],
        "optional": [],
        "test_cases": [
            {"symbol": "AAPL"},
            {"symbol": "SPY"},
            {"symbol": "INVALID_SYMBOL"}  # Error case
        ]
    },
    "get_stock_bars_intraday": {
        "required": ["symbol"],
        "optional": ["timeframe", "days", "limit"],
        "test_cases": [
            {"symbol": "AAPL", "timeframe": "1Min", "days": 1},
            {"symbol": "SPY", "timeframe": "5Min", "days": 2},
            {"symbol": "MSFT", "timeframe": "15Min", "days": 1}
        ]
    },
    "get_stock_peak_trough_analysis": {
        "required": ["symbols"],
        "optional": ["timeframe", "days", "window_len", "lookahead"],
        "test_cases": [
            {"symbols": "AAPL", "timeframe": "1Min", "days": 1},
            {"symbols": "SPY,QQQ", "timeframe": "5Min", "days": 1},
            {"symbols": "AUTO"}  # Use scanner results
        ]
    },
    "scan_day_trading_opportunities": {
        "required": [],
        "optional": ["symbols", "max_symbols", "sort_by"],
        "test_cases": [
            {"symbols": "ALL", "max_symbols": 10},
            {"symbols": "AAPL,MSFT,GOOGL", "max_symbols": 3},
            {"sort_by": "percent_change"}
        ]
    },
    "start_global_stock_stream": {
        "required": ["symbols"],
        "optional": ["data_types", "feed", "duration_seconds"],
        "test_cases": [
            {"symbols": ["SPY"], "data_types": ["trades", "quotes"]},
            {"symbols": ["AAPL", "MSFT"], "duration_seconds": 10}
        ]
    },
    "get_positions": {
        "required": [],
        "optional": [],
        "test_cases": [{}]
    },
    "get_account_info": {
        "required": [],
        "optional": [],
        "test_cases": [{}]
    },
    "analyze_market_activity_fast": {
        "required": [],
        "optional": ["symbols", "max_results", "min_percent_change", "max_price"],
        "test_cases": [
            {"max_results": 10, "min_percent_change": 5},
            {"max_price": 50, "min_percent_change": 10}
        ]
    },
    "get_volume_bars_from_history": {
        "required": ["symbol"],
        "optional": ["days", "volume_threshold", "auto_calculate_threshold"],
        "test_cases": [
            {"symbol": "AAPL", "days": 1, "auto_calculate_threshold": True},
            {"symbol": "SPY", "days": 2, "volume_threshold": 100000}
        ]
    },
    "place_stock_order": {
        "required": ["symbol", "side", "quantity"],
        "optional": ["order_type", "limit_price", "time_in_force"],
        "test_cases": [
            # Paper trading only - safe test orders
            {"symbol": "AAPL", "side": "buy", "quantity": 1, "order_type": "limit", "limit_price": 150}
        ]
    }
}

# Priority tools for Phase 1 testing
PRIORITY_TOOLS = [
    "get_stock_quote",
    "get_stock_snapshots", 
    "get_stock_bars_intraday",
    "start_global_stock_stream",
    "scan_day_trading_opportunities",
    "scan_explosive_momentum",
    "analyze_market_activity_fast",
    "get_stock_peak_trough_analysis",
    "generate_stock_plot",
    "get_volume_bars_from_history",
    "place_stock_order",
    "get_positions",
    "close_position"
]


class MCPToolTester:
    """Comprehensive testing framework for all 101 MCP tools"""
    
    def __init__(self):
        self.test_results = {}
        self.execution_times = {}
        self.error_log = []
        self.success_count = 0
        self.failure_count = 0
        self.total_tools = 101
        
        # Try to import MCP tools
        try:
            from alpaca_mcp_server.server_components import tool_registrations
            self.tools_available = True
            logger.info("✅ MCP tools imported successfully")
        except ImportError as e:
            self.tools_available = False
            logger.error(f"❌ Failed to import MCP tools: {e}")
    
    async def verify_connection(self) -> bool:
        """Verify MCP server connection and authentication"""
        try:
            from alpaca_mcp_server.tools.debug_tools import health_check
            result = health_check()
            if "healthy" in result.lower():
                logger.info("✅ MCP server connection verified")
                return True
            else:
                logger.error(f"❌ Server health check failed: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ Connection verification failed: {e}")
            return False
    
    async def test_tool(self, tool_name: str, test_cases: List[Dict]) -> Dict:
        """Test a single tool with multiple parameter combinations"""
        results = {
            "tool": tool_name,
            "status": "pending",
            "test_cases": [],
            "execution_times": [],
            "errors": []
        }
        
        logger.info(f"Testing tool: {tool_name}")
        
        for i, params in enumerate(test_cases):
            start_time = time.time()
            try:
                # Dynamic import and execution
                module_map = {
                    "get_stock_quote": "alpaca_mcp_server.tools.market_data_tools",
                    "scan_day_trading_opportunities": "alpaca_mcp_server.tools.scanning_tools",
                    "analyze_market_activity_fast": "alpaca_mcp_server.tools.c_stock_analyzer_wrapper",
                    "get_positions": "alpaca_mcp_server.tools.portfolio_tools",
                    "get_account_info": "alpaca_mcp_server.tools.account_tools",
                    "health_check": "alpaca_mcp_server.tools.debug_tools",
                    "get_stock_peak_trough_analysis": "alpaca_mcp_server.tools.technical_analysis_tools"
                }
                
                # Get the module for this tool
                module_name = module_map.get(tool_name)
                if module_name:
                    module = __import__(module_name, fromlist=[tool_name])
                    tool_func = getattr(module, tool_name)
                    
                    # Execute the tool
                    if asyncio.iscoroutinefunction(tool_func):
                        result = await tool_func(**params)
                    else:
                        result = tool_func(**params)
                    
                    execution_time = time.time() - start_time
                    
                    results["test_cases"].append({
                        "params": params,
                        "success": True,
                        "result_preview": str(result)[:200] if result else None,
                        "execution_time": execution_time
                    })
                    results["execution_times"].append(execution_time)
                    
                    logger.info(f"  ✅ Test case {i+1} passed ({execution_time:.2f}s)")
                else:
                    # Tool not mapped yet
                    results["test_cases"].append({
                        "params": params,
                        "success": False,
                        "error": "Tool not mapped for testing",
                        "execution_time": 0
                    })
                    logger.warning(f"  ⚠️ Tool {tool_name} not mapped for testing")
                    
            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = str(e)
                
                results["test_cases"].append({
                    "params": params,
                    "success": False,
                    "error": error_msg,
                    "execution_time": execution_time
                })
                results["errors"].append(error_msg)
                
                logger.error(f"  ❌ Test case {i+1} failed: {error_msg}")
        
        # Determine overall status
        successful_tests = sum(1 for tc in results["test_cases"] if tc["success"])
        if successful_tests == len(test_cases):
            results["status"] = "passed"
            self.success_count += 1
        elif successful_tests > 0:
            results["status"] = "partial"
        else:
            results["status"] = "failed"
            self.failure_count += 1
        
        # Calculate average execution time
        if results["execution_times"]:
            results["avg_execution_time"] = sum(results["execution_times"]) / len(results["execution_times"])
        
        return results
    
    async def run_phase1_tests(self):
        """Test priority tools first"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 1: Testing Priority Tools")
        logger.info("="*60)
        
        phase1_results = {}
        
        for tool_name in PRIORITY_TOOLS:
            if tool_name in TOOL_PARAMETERS:
                test_cases = TOOL_PARAMETERS[tool_name]["test_cases"]
            else:
                # Default test case
                test_cases = [{}]
            
            result = await self.test_tool(tool_name, test_cases)
            phase1_results[tool_name] = result
            self.test_results[tool_name] = result
            
            # Small delay between tools to avoid rate limiting
            await asyncio.sleep(0.5)
        
        return phase1_results
    
    async def run_phase2_tests(self):
        """Test all remaining tools"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 2: Testing All Remaining Tools")
        logger.info("="*60)
        
        phase2_results = {}
        tested_tools = set(self.test_results.keys())
        
        # Get all tools from inventory
        all_tools = []
        for category, tools in TOOL_INVENTORY.items():
            all_tools.extend(tools)
        
        remaining_tools = [tool for tool in all_tools if tool not in tested_tools]
        
        for tool_name in remaining_tools:
            if tool_name in TOOL_PARAMETERS:
                test_cases = TOOL_PARAMETERS[tool_name]["test_cases"]
            else:
                # Default test case for unmapped tools
                test_cases = [{}]
            
            result = await self.test_tool(tool_name, test_cases)
            phase2_results[tool_name] = result
            self.test_results[tool_name] = result
            
            # Small delay between tools
            await asyncio.sleep(0.5)
        
        return phase2_results
    
    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        report = []
        report.append("\n" + "="*80)
        report.append("MCP TOOL TESTING REPORT")
        report.append("="*80)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append(f"Total Tools: {self.total_tools}")
        report.append(f"Tools Tested: {len(self.test_results)}")
        report.append(f"Success: {self.success_count}")
        report.append(f"Failures: {self.failure_count}")
        report.append(f"Partial: {len([r for r in self.test_results.values() if r['status'] == 'partial'])}")
        
        # Category breakdown
        report.append("\n" + "-"*40)
        report.append("RESULTS BY CATEGORY")
        report.append("-"*40)
        
        for category, tools in TOOL_INVENTORY.items():
            tested = [t for t in tools if t in self.test_results]
            passed = [t for t in tested if self.test_results[t]["status"] == "passed"]
            
            report.append(f"\n{category}:")
            report.append(f"  Tested: {len(tested)}/{len(tools)}")
            report.append(f"  Passed: {len(passed)}/{len(tested) if tested else 0}")
            
            for tool in tools:
                if tool in self.test_results:
                    status = self.test_results[tool]["status"]
                    symbol = "✅" if status == "passed" else "⚠️" if status == "partial" else "❌"
                    avg_time = self.test_results[tool].get("avg_execution_time", 0)
                    report.append(f"    {symbol} {tool} ({avg_time:.2f}s)")
                else:
                    report.append(f"    ⏭️ {tool} (not tested)")
        
        # Performance metrics
        report.append("\n" + "-"*40)
        report.append("PERFORMANCE METRICS")
        report.append("-"*40)
        
        all_times = []
        for result in self.test_results.values():
            all_times.extend(result.get("execution_times", []))
        
        if all_times:
            report.append(f"Average execution time: {sum(all_times)/len(all_times):.3f}s")
            report.append(f"Fastest tool: {min(all_times):.3f}s")
            report.append(f"Slowest tool: {max(all_times):.3f}s")
        
        # Error summary
        if self.error_log:
            report.append("\n" + "-"*40)
            report.append("ERROR SUMMARY")
            report.append("-"*40)
            for error in self.error_log[:10]:  # Show first 10 errors
                report.append(f"  • {error}")
        
        return "\n".join(report)
    
    def save_results(self, filename: str = "mcp_test_results.json"):
        """Save test results to JSON file"""
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_tools": self.total_tools,
                    "tested": len(self.test_results),
                    "passed": self.success_count,
                    "failed": self.failure_count
                },
                "results": self.test_results
            }, f, indent=2)
        logger.info(f"Results saved to {filename}")


async def main():
    """Main test execution"""
    tester = MCPToolTester()
    
    # Verify connection
    if not await tester.verify_connection():
        logger.error("Failed to verify MCP server connection. Exiting.")
        return
    
    # Run Phase 1 tests
    phase1_results = await tester.run_phase1_tests()
    logger.info(f"\nPhase 1 Complete: {len(phase1_results)} priority tools tested")
    
    # Run Phase 2 tests
    phase2_results = await tester.run_phase2_tests()
    logger.info(f"\nPhase 2 Complete: {len(phase2_results)} additional tools tested")
    
    # Generate and print report
    report = tester.generate_report()
    print(report)
    
    # Save results
    tester.save_results()
    
    # Create dashboard HTML
    create_test_dashboard(tester.test_results)
    
    logger.info("\n✅ Testing complete! Check mcp_test_dashboard.html for interactive results.")


def create_test_dashboard(test_results: Dict):
    """Create an interactive HTML dashboard for test results"""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>MCP Tool Testing Dashboard - 101 Tools</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #667eea;
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 1.2em;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
            margin-top: 5px;
        }
        .category {
            margin-bottom: 30px;
        }
        .category-header {
            background: #f7f7f7;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .category-header:hover {
            background: #efefef;
        }
        .category-title {
            font-size: 1.3em;
            font-weight: 600;
            color: #333;
        }
        .category-stats {
            font-size: 0.9em;
            color: #666;
        }
        .tools-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
            padding: 10px;
        }
        .tool-card {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .tool-card:hover {
            border-color: #667eea;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.2);
            transform: translateY(-2px);
        }
        .tool-card.passed {
            border-left: 5px solid #4caf50;
        }
        .tool-card.failed {
            border-left: 5px solid #f44336;
        }
        .tool-card.partial {
            border-left: 5px solid #ff9800;
        }
        .tool-card.not-tested {
            border-left: 5px solid #9e9e9e;
        }
        .tool-name {
            font-weight: 600;
            margin-bottom: 5px;
            color: #333;
        }
        .tool-status {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 500;
            margin-bottom: 5px;
        }
        .status-passed {
            background: #e8f5e9;
            color: #2e7d32;
        }
        .status-failed {
            background: #ffebee;
            color: #c62828;
        }
        .status-partial {
            background: #fff3e0;
            color: #ef6c00;
        }
        .tool-time {
            font-size: 0.85em;
            color: #666;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
        }
        .modal-content {
            background: white;
            margin: 50px auto;
            padding: 30px;
            width: 80%;
            max-width: 800px;
            border-radius: 10px;
            max-height: 80vh;
            overflow-y: auto;
        }
        .close-modal {
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            color: #999;
        }
        .close-modal:hover {
            color: #333;
        }
        .test-case {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .test-params {
            background: #fff;
            padding: 10px;
            border-radius: 3px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 0.9em;
        }
        .execute-btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
            margin-top: 10px;
        }
        .execute-btn:hover {
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 MCP Tool Testing Dashboard</h1>
        <p class="subtitle">Comprehensive Testing of All 101 Alpaca Trading Tools</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">101</div>
                <div class="stat-label">Total Tools</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #4caf50, #45a049);">
                <div class="stat-value" id="passed-count">0</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #f44336, #e53935);">
                <div class="stat-value" id="failed-count">0</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #ff9800, #fb8c00);">
                <div class="stat-value" id="partial-count">0</div>
                <div class="stat-label">Partial</div>
            </div>
        </div>
        
        <div id="categories"></div>
    </div>
    
    <div id="modal" class="modal">
        <div class="modal-content">
            <span class="close-modal">&times;</span>
            <div id="modal-body"></div>
        </div>
    </div>
    
    <script>
        const testResults = """ + json.dumps(test_results) + """;
        const toolInventory = """ + json.dumps(TOOL_INVENTORY) + """;
        
        function init() {
            updateStats();
            renderCategories();
        }
        
        function updateStats() {
            let passed = 0, failed = 0, partial = 0;
            for (const result of Object.values(testResults)) {
                if (result.status === 'passed') passed++;
                else if (result.status === 'failed') failed++;
                else if (result.status === 'partial') partial++;
            }
            document.getElementById('passed-count').textContent = passed;
            document.getElementById('failed-count').textContent = failed;
            document.getElementById('partial-count').textContent = partial;
        }
        
        function renderCategories() {
            const container = document.getElementById('categories');
            
            for (const [category, tools] of Object.entries(toolInventory)) {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'category';
                
                const tested = tools.filter(t => testResults[t]).length;
                const passed = tools.filter(t => testResults[t]?.status === 'passed').length;
                
                categoryDiv.innerHTML = `
                    <div class="category-header" onclick="toggleCategory('${category}')">
                        <div class="category-title">${category}</div>
                        <div class="category-stats">
                            ${passed}/${tested} passed | ${tools.length} total
                        </div>
                    </div>
                    <div class="tools-grid" id="${category}-tools">
                        ${tools.map(tool => renderToolCard(tool)).join('')}
                    </div>
                `;
                
                container.appendChild(categoryDiv);
            }
        }
        
        function renderToolCard(toolName) {
            const result = testResults[toolName];
            const status = result?.status || 'not-tested';
            const statusClass = status === 'passed' ? 'passed' : 
                               status === 'failed' ? 'failed' :
                               status === 'partial' ? 'partial' : 'not-tested';
            
            const avgTime = result?.avg_execution_time 
                ? `⚡ ${result.avg_execution_time.toFixed(2)}s` 
                : '';
            
            return `
                <div class="tool-card ${statusClass}" onclick="showToolDetails('${toolName}')">
                    <div class="tool-name">${toolName}</div>
                    <div class="tool-status status-${status}">${status.toUpperCase()}</div>
                    <div class="tool-time">${avgTime}</div>
                </div>
            `;
        }
        
        function showToolDetails(toolName) {
            const result = testResults[toolName];
            const modal = document.getElementById('modal');
            const modalBody = document.getElementById('modal-body');
            
            if (!result) {
                modalBody.innerHTML = `
                    <h2>${toolName}</h2>
                    <p>This tool has not been tested yet.</p>
                    <button class="execute-btn" onclick="executeToolTest('${toolName}')">
                        Run Test Now
                    </button>
                `;
            } else {
                let testCasesHtml = '';
                if (result.test_cases) {
                    testCasesHtml = result.test_cases.map((tc, i) => `
                        <div class="test-case">
                            <h4>Test Case ${i + 1} - ${tc.success ? '✅ Passed' : '❌ Failed'}</h4>
                            <div class="test-params">
                                Parameters: ${JSON.stringify(tc.params, null, 2)}
                            </div>
                            ${tc.error ? `<div style="color: red;">Error: ${tc.error}</div>` : ''}
                            ${tc.result_preview ? `<div>Result: ${tc.result_preview}...</div>` : ''}
                            <div>Execution time: ${tc.execution_time.toFixed(3)}s</div>
                        </div>
                    `).join('');
                }
                
                modalBody.innerHTML = `
                    <h2>${toolName}</h2>
                    <p>Status: <span class="tool-status status-${result.status}">${result.status.toUpperCase()}</span></p>
                    <p>Average execution time: ${result.avg_execution_time?.toFixed(3) || 'N/A'}s</p>
                    <h3>Test Cases:</h3>
                    ${testCasesHtml}
                    <button class="execute-btn" onclick="executeToolTest('${toolName}')">
                        Re-run Test
                    </button>
                `;
            }
            
            modal.style.display = 'block';
        }
        
        function executeToolTest(toolName) {
            alert(`Executing test for ${toolName}...\\nThis would trigger the actual MCP tool execution.`);
            // Here you would make an API call to execute the tool
        }
        
        function toggleCategory(category) {
            const toolsDiv = document.getElementById(`${category}-tools`);
            toolsDiv.style.display = toolsDiv.style.display === 'none' ? 'grid' : 'none';
        }
        
        // Close modal
        document.querySelector('.close-modal').onclick = function() {
            document.getElementById('modal').style.display = 'none';
        }
        
        window.onclick = function(event) {
            const modal = document.getElementById('modal');
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        }
        
        // Initialize on load
        init();
    </script>
</body>
</html>"""
    
    with open("mcp_test_dashboard.html", "w") as f:
        f.write(html_content)
    
    logger.info("Interactive dashboard created: mcp_test_dashboard.html")


if __name__ == "__main__":
    asyncio.run(main())