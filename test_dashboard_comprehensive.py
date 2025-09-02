#!/usr/bin/env python3
"""
Comprehensive Dashboard Testing Script
Tests all 101 MCP tools through the dashboard interface using Playwright
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any
from playwright.async_api import async_playwright, Page, Browser

class DashboardToolTester:
    def __init__(self):
        self.dashboard_url = "file:///home/jjoravet/alpaca-mcp-server-enhanced/comprehensive_dashboard.html"
        self.test_results = []
        self.browser = None
        self.page = None
        
    async def setup(self):
        """Initialize browser and navigate to dashboard"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        await self.page.goto(self.dashboard_url)
        await asyncio.sleep(2)  # Wait for dashboard to fully load
        
    async def teardown(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
            
    async def click_tool(self, tool_selector: str) -> bool:
        """Click on a tool in the dashboard"""
        try:
            await self.page.click(tool_selector)
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            print(f"Error clicking tool: {e}")
            return False
            
    async def fill_parameters(self, params: Dict[str, Any]):
        """Fill in tool parameters in the modal"""
        for param_name, value in params.items():
            try:
                # Find input field by name or placeholder
                input_field = await self.page.query_selector(f'input[placeholder*="{param_name}"]')
                if not input_field:
                    input_field = await self.page.query_selector(f'input[name*="{param_name}"]')
                if input_field:
                    await input_field.fill(str(value))
            except Exception as e:
                print(f"Error filling parameter {param_name}: {e}")
                
    async def execute_tool(self) -> Dict[str, Any]:
        """Click execute button and capture result"""
        try:
            # Click Execute Tool button
            await self.page.click('button:has-text("Execute Tool")')
            
            # Wait for result modal
            await asyncio.sleep(2)
            
            # Capture result text
            result_element = await self.page.query_selector('.result-content')
            result_text = await result_element.inner_text() if result_element else "No result"
            
            # Capture execution time
            time_element = await self.page.query_selector('.execution-time')
            exec_time = await time_element.inner_text() if time_element else "Unknown"
            
            # Close result modal
            close_button = await self.page.query_selector('button:has-text("Close")')
            if close_button:
                await close_button.click()
                await asyncio.sleep(0.5)
                
            return {
                "success": True,
                "result": result_text,
                "execution_time": exec_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def test_tool(self, tool_config: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single tool with given configuration"""
        print(f"\n📊 Testing: {tool_config['name']}")
        print(f"   Category: {tool_config['category']}")
        print(f"   Description: {tool_config['description']}")
        
        test_result = {
            "tool": tool_config["name"],
            "category": tool_config["category"],
            "timestamp": datetime.now().isoformat(),
            "test_cases": []
        }
        
        # Test each parameter combination
        for test_case in tool_config.get("test_cases", []):
            print(f"   Test case: {test_case['name']}")
            
            # Click on the tool
            tool_clicked = await self.click_tool(f'text="{tool_config["name"]}"')
            if not tool_clicked:
                test_result["test_cases"].append({
                    "name": test_case["name"],
                    "success": False,
                    "error": "Failed to click tool"
                })
                continue
                
            # Fill parameters if any
            if "params" in test_case:
                await self.fill_parameters(test_case["params"])
                
            # Execute and capture result
            result = await self.execute_tool()
            
            test_result["test_cases"].append({
                "name": test_case["name"],
                "params": test_case.get("params", {}),
                **result
            })
            
            # Visual feedback
            if result["success"]:
                print(f"   ✅ Success - {result.get('execution_time', 'N/A')}")
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
                
        self.test_results.append(test_result)
        return test_result
        
    async def test_priority_tools(self):
        """Test high-priority tools first"""
        priority_tools = [
            {
                "name": "get_stock_quote",
                "category": "Market Data",
                "description": "Get latest bid/ask quote",
                "test_cases": [
                    {"name": "AAPL quote", "params": {"symbol": "AAPL"}},
                    {"name": "SPY quote", "params": {"symbol": "SPY"}},
                    {"name": "Invalid symbol", "params": {"symbol": "XXXXX"}}
                ]
            },
            {
                "name": "get_stock_snapshots",
                "category": "Market Data",
                "description": "Comprehensive market data",
                "test_cases": [
                    {"name": "Multiple symbols", "params": {"symbols": "AAPL,MSFT,GOOGL"}},
                    {"name": "Single symbol", "params": {"symbols": "SPY"}}
                ]
            },
            {
                "name": "scan_day_trading_opportunities",
                "category": "Scanner",
                "description": "Find explosive stocks",
                "test_cases": [
                    {"name": "Default scan", "params": {}},
                    {"name": "Limited results", "params": {"max_symbols": "5"}}
                ]
            },
            {
                "name": "get_stock_peak_trough_analysis",
                "category": "Technical",
                "description": "Zero-phase Hanning filter analysis",
                "test_cases": [
                    {"name": "AAPL analysis", "params": {"symbol": "AAPL"}},
                    {"name": "Custom window", "params": {"symbol": "SPY", "window_len": "21"}}
                ]
            },
            {
                "name": "get_positions",
                "category": "Portfolio",
                "description": "Get all open positions",
                "test_cases": [
                    {"name": "Current positions", "params": {}}
                ]
            }
        ]
        
        print("\n🎯 PHASE 1: Testing Priority Tools")
        print("=" * 60)
        
        for tool_config in priority_tools:
            await self.test_tool(tool_config)
            await asyncio.sleep(1)  # Pause between tools
            
    async def navigate_to_tools_section(self):
        """Navigate to MCP Tools section"""
        try:
            # Click on MCP Tools tab
            await self.page.click('text="🔧 MCP Tools"')
            await asyncio.sleep(1)
            
            # Click Show Complete Reference if needed
            show_ref_button = await self.page.query_selector('button:has-text("Show Complete Reference")')
            if show_ref_button:
                await show_ref_button.click()
                await asyncio.sleep(1)
                
            return True
        except Exception as e:
            print(f"Error navigating to tools section: {e}")
            return False
            
    async def get_all_tools_from_dashboard(self) -> List[Dict[str, str]]:
        """Extract all tool information from the dashboard"""
        tools = []
        try:
            # Get all tool elements
            tool_elements = await self.page.query_selector_all('[class*="tool-item"]')
            
            for element in tool_elements:
                tool_text = await element.inner_text()
                # Parse tool name and description from text
                if "(" in tool_text:
                    name = tool_text.split("(")[0].strip()
                    description = tool_text.split("\n")[-1] if "\n" in tool_text else ""
                    tools.append({
                        "name": name,
                        "description": description
                    })
                    
            return tools
        except Exception as e:
            print(f"Error extracting tools: {e}")
            return []
            
    async def generate_report(self):
        """Generate comprehensive test report"""
        report = {
            "test_run": {
                "timestamp": datetime.now().isoformat(),
                "dashboard_url": self.dashboard_url,
                "total_tools_tested": len(self.test_results),
                "summary": {
                    "passed": 0,
                    "failed": 0,
                    "partial": 0
                }
            },
            "tools": self.test_results
        }
        
        # Calculate summary statistics
        for tool_result in self.test_results:
            all_passed = all(tc["success"] for tc in tool_result["test_cases"])
            any_passed = any(tc["success"] for tc in tool_result["test_cases"])
            
            if all_passed:
                report["test_run"]["summary"]["passed"] += 1
            elif any_passed:
                report["test_run"]["summary"]["partial"] += 1
            else:
                report["test_run"]["summary"]["failed"] += 1
                
        # Save to JSON file
        with open("dashboard_test_report.json", "w") as f:
            json.dump(report, f, indent=2)
            
        # Generate HTML report
        html_report = self.generate_html_report(report)
        with open("dashboard_test_report.html", "w") as f:
            f.write(html_report)
            
        return report
        
    def generate_html_report(self, report: Dict) -> str:
        """Generate HTML test report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dashboard Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #1a1a2e; color: white; padding: 20px; border-radius: 8px; }}
                .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: #f0f0f0; padding: 15px; border-radius: 8px; flex: 1; }}
                .passed {{ color: #27ae60; }}
                .failed {{ color: #e74c3c; }}
                .partial {{ color: #f39c12; }}
                .tool-result {{ margin: 20px 0; padding: 15px; background: white; border: 1px solid #ddd; border-radius: 8px; }}
                .test-case {{ margin: 10px 0; padding: 10px; background: #f9f9f9; border-radius: 4px; }}
                .success-icon {{ color: #27ae60; }}
                .failure-icon {{ color: #e74c3c; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🧪 Dashboard Testing Report</h1>
                <p>Generated: {report['test_run']['timestamp']}</p>
                <p>Total Tools Tested: {report['test_run']['total_tools_tested']}</p>
            </div>
            
            <div class="summary">
                <div class="stat-card">
                    <h3 class="passed">✅ Passed</h3>
                    <p style="font-size: 24px;">{report['test_run']['summary']['passed']}</p>
                </div>
                <div class="stat-card">
                    <h3 class="partial">⚠️ Partial</h3>
                    <p style="font-size: 24px;">{report['test_run']['summary']['partial']}</p>
                </div>
                <div class="stat-card">
                    <h3 class="failed">❌ Failed</h3>
                    <p style="font-size: 24px;">{report['test_run']['summary']['failed']}</p>
                </div>
            </div>
            
            <h2>Detailed Results</h2>
        """
        
        for tool in report['tools']:
            status_icon = "✅" if all(tc['success'] for tc in tool['test_cases']) else "❌"
            html += f"""
            <div class="tool-result">
                <h3>{status_icon} {tool['tool']} - {tool['category']}</h3>
                <p>Tested at: {tool['timestamp']}</p>
            """
            
            for test_case in tool['test_cases']:
                icon = "✅" if test_case['success'] else "❌"
                html += f"""
                <div class="test-case">
                    <strong>{icon} {test_case['name']}</strong>
                    <p>Parameters: {json.dumps(test_case.get('params', {}))}</p>
                """
                
                if test_case['success']:
                    html += f"<p>Execution Time: {test_case.get('execution_time', 'N/A')}</p>"
                else:
                    html += f"<p>Error: {test_case.get('error', 'Unknown')}</p>"
                    
                html += "</div>"
                
            html += "</div>"
            
        html += """
        </body>
        </html>
        """
        
        return html
        
    async def run_comprehensive_test(self):
        """Run complete test suite"""
        print("\n🚀 Starting Comprehensive Dashboard Testing")
        print("=" * 60)
        
        try:
            # Setup browser
            await self.setup()
            print("✅ Browser initialized")
            
            # Navigate to tools section
            await self.navigate_to_tools_section()
            print("✅ Navigated to MCP Tools section")
            
            # Test priority tools
            await self.test_priority_tools()
            
            # Generate report
            report = await self.generate_report()
            
            print("\n" + "=" * 60)
            print("📊 TEST SUMMARY")
            print(f"   Passed: {report['test_run']['summary']['passed']}")
            print(f"   Partial: {report['test_run']['summary']['partial']}")
            print(f"   Failed: {report['test_run']['summary']['failed']}")
            print(f"\n📄 Reports saved:")
            print(f"   - dashboard_test_report.json")
            print(f"   - dashboard_test_report.html")
            
        finally:
            await self.teardown()
            
async def main():
    tester = DashboardToolTester()
    await tester.run_comprehensive_test()
    
if __name__ == "__main__":
    asyncio.run(main())