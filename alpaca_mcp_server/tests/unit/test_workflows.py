"""
Comprehensive unit tests for advanced agentic workflows.
Tests use real data and actual API connections.
"""

import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server  # noqa: E402.prompts.day_trading_workflow import day_trading_workflow
from alpaca_mcp_server  # noqa: E402.prompts.list_trading_capabilities import list_trading_capabilities
from alpaca_mcp_server  # noqa: E402.prompts.market_session_workflow import market_session_workflow
from alpaca_mcp_server  # noqa: E402.prompts.master_scanning_workflow import master_scanning_workflow
from alpaca_mcp_server  # noqa: E402.prompts.pro_technical_workflow import pro_technical_workflow


class TestMasterScanningWorkflow:
    """Test master scanning workflow with real market data."""

    @pytest.mark.asyncio
    async def test_master_scan_quick(self):
        """Test quick scan mode execution."""
        result = await master_scanning_workflow("quick")

        assert isinstance(result, str)
        assert len(result) > 500  # Ensure substantial output
        assert "MASTER SCANNER WORKFLOW" in result
        assert "OPERATIONAL" in result or "Ready" in result
        print(f"✅ Quick scan: {len(result)} characters")

    @pytest.mark.asyncio
    async def test_master_scan_comprehensive(self):
        """Test comprehensive scan mode execution."""
        result = await master_scanning_workflow("comprehensive")

        assert isinstance(result, str)
        assert len(result) > 1000  # More detailed output
        assert "SCANNER 1" in result
        assert "SCANNER 2" in result
        assert "SYNTHESIZED OPPORTUNITIES" in result
        print(f"✅ Comprehensive scan: {len(result)} characters")

    @pytest.mark.asyncio
    async def test_master_scan_extended_hours(self):
        """Test extended hours scan mode execution."""
        result = await master_scanning_workflow("extended_hours")

        assert isinstance(result, str)
        assert "AFTER HOURS" in result or "extended_hours" in result
        print(f"✅ Extended hours scan: {len(result)} characters")


class TestProTechnicalWorkflow:
    """Test professional technical analysis workflow with real symbols."""

    @pytest.mark.asyncio
    async def test_technical_analysis_aapl(self):
        """Test technical analysis for AAPL."""
        symbol = "AAPL"
        result = await pro_technical_workflow(symbol, "quick")

        assert isinstance(result, str)
        assert len(result) > 1000
        assert symbol.upper() in result
        assert "PROFESSIONAL TECHNICAL ANALYSIS" in result
        assert "ALGORITHMIC" in result or "Peak/Trough" in result
        print(f"✅ Technical analysis {symbol}: {len(result)} characters")

    @pytest.mark.asyncio
    async def test_technical_analysis_comprehensive(self):
        """Test comprehensive technical analysis."""
        result = await pro_technical_workflow("TSLA", "comprehensive")

        assert isinstance(result, str)
        assert "TSLA" in result
        assert "MULTI-TIMEFRAME" in result or "timeframe" in result
        assert "TRADING LEVELS" in result or "SIGNALS" in result
        print(f"✅ Comprehensive technical: {len(result)} characters")

    @pytest.mark.asyncio
    async def test_technical_analysis_deep(self):
        """Test deep technical analysis mode."""
        result = await pro_technical_workflow("SPY", "deep")

        assert isinstance(result, str)
        assert "SPY" in result
        print(f"✅ Deep technical analysis: {len(result)} characters")


class TestMarketSessionWorkflow:
    """Test market session strategy workflow with real timing."""

    @pytest.mark.asyncio
    async def test_session_full_day(self):
        """Test full day session strategy."""
        result = await market_session_workflow("full_day")

        assert isinstance(result, str)
        assert len(result) > 1500
        assert "MARKET SESSION STRATEGY" in result
        assert "PRE-MARKET" in result
        assert "POWER HOUR" in result
        print(f"✅ Full day session: {len(result)} characters")

    @pytest.mark.asyncio
    async def test_session_market_open(self):
        """Test market open session strategy."""
        result = await market_session_workflow("market_open")

        assert isinstance(result, str)
        assert "MARKET OPEN" in result
        assert "volatility" in result.lower() or "momentum" in result.lower()
        print(f"✅ Market open session: {len(result)} characters")

    @pytest.mark.asyncio
    async def test_session_pre_market(self):
        """Test pre-market session strategy."""
        result = await market_session_workflow("pre_market")

        assert isinstance(result, str)
        assert "PRE-MARKET" in result
        print(f"✅ Pre-market session: {len(result)} characters")

    @pytest.mark.asyncio
    async def test_session_power_hour(self):
        """Test power hour session strategy."""
        result = await market_session_workflow("power_hour")

        assert isinstance(result, str)
        assert "POWER HOUR" in result
        print(f"✅ Power hour session: {len(result)} characters")

    @pytest.mark.asyncio
    async def test_session_after_hours(self):
        """Test after hours session strategy."""
        result = await market_session_workflow("after_hours")

        assert isinstance(result, str)
        assert "AFTER-HOURS" in result or "after_hours" in result
        print(f"✅ After hours session: {len(result)} characters")


class TestDayTradingWorkflow:
    """Test day trading workflow with real symbols."""

    @pytest.mark.asyncio
    async def test_day_trading_workflow_aapl(self):
        """Test day trading workflow for AAPL."""
        result = await day_trading_workflow("AAPL")

        assert isinstance(result, str)
        assert len(result) > 800
        assert "AAPL" in result
        print(f"✅ Day trading AAPL: {len(result)} characters")

    @pytest.mark.asyncio
    async def test_day_trading_workflow_no_symbol(self):
        """Test day trading workflow without symbol."""
        result = await day_trading_workflow()

        assert isinstance(result, str)
        assert "DAY TRADING" in result or "trading" in result.lower()
        print(f"✅ Day trading (no symbol): {len(result)} characters")

    @pytest.mark.asyncio
    async def test_day_trading_workflow_multiple_symbols(self):
        """Test day trading workflow with multiple symbols."""
        test_symbols = ["AAPL", "MSFT", "NVDA"]  # High-liquidity symbols
        for symbol in test_symbols:
            result = await day_trading_workflow(symbol)
            assert isinstance(result, str)
            assert symbol in result
            print(f"✅ Day trading {symbol}: {len(result)} characters")


class TestListTradingCapabilities:
    """Test enhanced discovery and capabilities listing."""

    @pytest.mark.asyncio
    async def test_list_capabilities(self):
        """Test capabilities listing functionality."""
        result = await list_trading_capabilities()

        assert isinstance(result, str)
        assert len(result) > 2000  # Comprehensive output
        assert "ALPACA TRADING MCP SERVER" in result
        assert "ADVANCED AGENTIC WORKFLOWS" in result
        assert "master_scanning_workflow" in result
        assert "pro_technical_workflow" in result
        assert "market_session_workflow" in result
        print(f"✅ Capabilities listing: {len(result)} characters")

    @pytest.mark.asyncio
    async def test_capabilities_structure(self):
        """Test capabilities output structure."""
        result = await list_trading_capabilities()

        # Check for key sections
        assert "QUICK START WORKFLOWS" in result
        assert "ADVANCED AGENTIC WORKFLOWS" in result
        assert "COMPREHENSIVE TOOL CATEGORIES" in result
        assert "ACCOUNT & PORTFOLIO" in result
        assert "MARKET DATA" in result
        print("✅ Capabilities structure validated")


class TestWorkflowIntegration:
    """Test workflow integration and composition."""

    @pytest.mark.asyncio
    async def test_workflow_composition(self):
        """Test that workflows can be composed together."""
        # Test basic composition: capabilities -> scanner -> technical
        capabilities = await list_trading_capabilities()
        assert "master_scanning_workflow" in capabilities

        scanner_result = await master_scanning_workflow("quick")
        assert len(scanner_result) > 0

        technical_result = await pro_technical_workflow("AAPL", "quick")
        assert "AAPL" in technical_result

        print("✅ Workflow composition working")

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test workflow error handling with invalid inputs."""
        # Test invalid scan type
        result = await master_scanning_workflow("invalid_type")
        assert isinstance(result, str)
        assert len(result) > 0  # Should still return something

        # Test invalid symbol (should handle gracefully)
        result = await pro_technical_workflow("INVALIDXYZ", "quick")
        assert isinstance(result, str)
        assert len(result) > 0

        print("✅ Error handling validated")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])
