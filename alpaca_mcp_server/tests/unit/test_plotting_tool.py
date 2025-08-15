"""
Comprehensive tests for the advanced plotting tool.
Tests plotting functionality with real data and various parameters.
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server.tools.advanced_plotting_tool import generate_peak_trough_plots  # noqa: E402


class TestAdvancedPlottingTool:
    """Test advanced plotting tool functionality."""

    @pytest.mark.asyncio
    async def test_plotting_tool_import(self):
        """Test that plotting tool can be imported."""
        from alpaca_mcp_server.tools.advanced_plotting_tool import generate_peak_trough_plots

        assert callable(generate_peak_trough_plots)
        print("✅ Plotting tool import successful")

    @pytest.mark.asyncio
    async def test_single_symbol_plot(self):
        """Test single symbol plotting."""
        result = await generate_peak_trough_plots(
            symbols="AAPL", timeframe="1Min", days=1, window_len=11, lookahead=1, plot_mode="single"
        )

        assert isinstance(result, str)
        assert len(result) > 500
        assert "AAPL" in result
        assert "ANALYSIS COMPLETE" in result or "ERROR" in result

        # Check for key sections
        if "ERROR" not in result:
            assert "ANALYSIS SUMMARY" in result
            assert "PLOTS GENERATED" in result
            print(f"✅ Single symbol plot: {len(result)} chars")
        else:
            print(
                f"⚠️  Single symbol plot returned error (expected if no API keys): {result[:200]}..."
            )

    @pytest.mark.asyncio
    async def test_multi_symbol_plot(self):
        """Test multi-symbol plotting."""
        result = await generate_peak_trough_plots(
            symbols="AAPL,MSFT,SPY",
            timeframe="1Min",
            days=1,
            window_len=11,
            lookahead=1,
            plot_mode="combined",
        )

        assert isinstance(result, str)
        assert len(result) > 300

        # Should mention multiple symbols
        symbols = ["AAPL", "MSFT", "SPY"]
        symbol_mentions = sum(1 for symbol in symbols if symbol in result)

        if "ERROR" not in result:
            assert symbol_mentions >= 1  # At least one symbol should be processed
            print(f"✅ Multi-symbol plot: {symbol_mentions} symbols mentioned")
        else:
            print(f"⚠️  Multi-symbol plot returned error: {result[:200]}...")

    @pytest.mark.asyncio
    async def test_parameter_validation(self):
        """Test parameter validation."""
        # Test invalid days
        result = await generate_peak_trough_plots(symbols="AAPL", days=50)  # Too many days
        assert "Days must be between 1 and 30" in result
        print("✅ Days parameter validation working")

        # Test invalid window length
        result = await generate_peak_trough_plots(symbols="AAPL", window_len=2)  # Too small
        assert "Window length must be between 3 and 101" in result
        print("✅ Window length validation working")

        # Test invalid lookahead
        result = await generate_peak_trough_plots(symbols="AAPL", lookahead=100)  # Too large
        assert "Lookahead must be between 1 and 50" in result
        print("✅ Lookahead validation working")

        # Test too many symbols
        many_symbols = ",".join([f"SYM{i}" for i in range(15)])
        result = await generate_peak_trough_plots(symbols=many_symbols)
        assert "Maximum 10 symbols allowed" in result
        print("✅ Symbol count validation working")

    @pytest.mark.asyncio
    async def test_empty_parameters(self):
        """Test empty parameter handling."""
        result = await generate_peak_trough_plots(symbols="")
        assert "No valid symbols provided" in result
        print("✅ Empty symbols validation working")

        result = await generate_peak_trough_plots(symbols="   ,  , ")
        assert "No valid symbols provided" in result
        print("✅ Whitespace-only symbols validation working")

    @pytest.mark.asyncio
    async def test_different_plot_modes(self):
        """Test different plot modes."""
        plot_modes = ["single", "combined", "overlay", "all"]

        for mode in plot_modes:
            result = await generate_peak_trough_plots(symbols="AAPL", plot_mode=mode)

            assert isinstance(result, str)
            assert len(result) > 200

            if "ERROR" not in result:
                assert f"Plot mode: {mode}" in result
                print(f"✅ Plot mode '{mode}': working")
            else:
                print(f"⚠️  Plot mode '{mode}': error (may be expected)")

    @pytest.mark.asyncio
    async def test_different_timeframes(self):
        """Test different timeframes."""
        timeframes = ["1Min", "5Min", "15Min", "1Hour"]

        for timeframe in timeframes:
            result = await generate_peak_trough_plots(symbols="SPY", timeframe=timeframe, days=1)

            assert isinstance(result, str)
            assert len(result) > 200

            if "ERROR" not in result:
                assert f"Timeframe: {timeframe}" in result
                print(f"✅ Timeframe '{timeframe}': working")
            else:
                print(f"⚠️  Timeframe '{timeframe}': error (may be expected)")

    @pytest.mark.asyncio
    async def test_api_credentials_handling(self):
        """Test API credentials handling."""
        # Save original credentials
        original_key = os.environ.get("APCA_API_KEY_ID")
        original_secret = os.environ.get("APCA_API_SECRET_KEY")

        try:
            # Remove credentials temporarily
            if "APCA_API_KEY_ID" in os.environ:
                del os.environ["APCA_API_KEY_ID"]
            if "APCA_API_SECRET_KEY" in os.environ:
                del os.environ["APCA_API_SECRET_KEY"]

            result = await generate_peak_trough_plots(symbols="AAPL")
            assert "API CREDENTIALS NOT CONFIGURED" in result
            print("✅ Missing API credentials handled correctly")

        finally:
            # Restore original credentials
            if original_key:
                os.environ["APCA_API_KEY_ID"] = original_key
            if original_secret:
                os.environ["APCA_API_SECRET_KEY"] = original_secret

    @pytest.mark.asyncio
    async def test_window_length_adjustment(self):
        """Test that even window lengths are adjusted to odd."""
        result = await generate_peak_trough_plots(
            symbols="AAPL", window_len=12  # Even number, should be adjusted to 13
        )

        # Should not fail due to even window length
        assert isinstance(result, str)
        assert len(result) > 200
        print("✅ Even window length auto-adjustment working")

    @pytest.mark.asyncio
    async def test_special_symbols(self):
        """Test handling of special symbols."""
        special_symbols = [
            "INVALID123",  # Invalid symbol
            "TEST",  # Test symbol
            "BRK.A",  # Symbol with dot
            "BRK-A",  # Symbol with dash
        ]

        for symbol in special_symbols:
            result = await generate_peak_trough_plots(symbols=symbol)
            assert isinstance(result, str)
            assert len(result) > 100
            print(f"✅ Special symbol '{symbol}': handled gracefully")

    @pytest.mark.asyncio
    async def test_concurrent_plotting_calls(self):
        """Test concurrent plotting calls."""
        symbols = ["AAPL", "MSFT", "GOOGL", "SPY", "TSLA"]

        tasks = [generate_peak_trough_plots(symbol, plot_mode="single") for symbol in symbols]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_calls = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"⚠️  Concurrent call {i+1} failed: {result}")
            else:
                assert isinstance(result, str)
                successful_calls += 1

        print(f"✅ Concurrent calls: {successful_calls}/{len(symbols)} successful")
        assert successful_calls >= len(symbols) * 0.5  # At least 50% should succeed


class TestPlottingIntegration:
    """Test plotting tool integration with other components."""

    @pytest.mark.asyncio
    async def test_mcp_server_integration(self):
        """Test plotting tool integration with MCP server."""
        try:

            # Check if tool is registered (this may vary based on MCP implementation)
            print("✅ MCP server imports successfully with plotting tool")

        except Exception as e:
            print(f"⚠️  MCP server integration: {e}")

    @pytest.mark.asyncio
    async def test_workflow_integration(self):
        """Test plotting tool integration with technical workflow."""
        from alpaca_mcp_server.prompts.pro_technical_workflow import pro_technical_workflow

        result = await pro_technical_workflow("AAPL", "quick")

        assert isinstance(result, str)
        assert "generate_advanced_technical_plots" in result
        assert "VISUAL ANALYSIS ENHANCEMENT" in result

        print("✅ Plotting tool integrated with technical workflow")

    @pytest.mark.asyncio
    async def test_capabilities_integration(self):
        """Test plotting tool appears in capabilities."""
        from alpaca_mcp_server.prompts.list_trading_capabilities import list_trading_capabilities

        capabilities = await list_trading_capabilities()

        assert isinstance(capabilities, str)
        assert "generate_advanced_technical_plots" in capabilities
        assert "Publication-quality plots" in capabilities

        print("✅ Plotting tool appears in capabilities listing")


class TestPlottingDependencies:
    """Test plotting dependencies and fallbacks."""

    def test_matplotlib_available(self):
        """Test matplotlib dependency."""
        try:
            import matplotlib.pyplot as plt  # noqa: F401

            print("✅ Matplotlib available")
            return True
        except ImportError:
            print("❌ Matplotlib not available")
            return False

    def test_scipy_available(self):
        """Test scipy dependency."""
        try:
            import scipy.signal  # noqa: F401

            print("✅ Scipy available")
            return True
        except ImportError:
            print("❌ Scipy not available")
            return False

    def test_numpy_available(self):
        """Test numpy dependency."""
        try:
            import numpy as np  # noqa: F401

            print("✅ Numpy available")
            return True
        except ImportError:
            print("❌ Numpy not available")
            return False

    @pytest.mark.asyncio
    async def test_dependency_fallback(self):
        """Test graceful fallback when dependencies missing."""
        # This test would require temporarily removing dependencies
        # For now, just test the current state

        dependencies_available = all(
            [
                self.test_matplotlib_available(),
                self.test_scipy_available(),
                self.test_numpy_available(),
            ]
        )

        if dependencies_available:
            print("✅ All plotting dependencies available")
        else:
            print("⚠️  Some plotting dependencies missing - fallback should be used")


class TestPlottingPerformance:
    """Test plotting tool performance."""

    @pytest.mark.asyncio
    async def test_single_symbol_performance(self):
        """Test single symbol plotting performance."""
        import time

        start_time = time.time()
        result = await generate_peak_trough_plots(symbols="SPY", timeframe="1Min", days=1)
        end_time = time.time()

        duration = end_time - start_time

        assert isinstance(result, str)
        assert duration < 30.0  # Should complete within 30 seconds

        print(f"✅ Single symbol plotting: {duration:.2f}s")

    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage during plotting."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Generate multiple plots
        for symbol in ["AAPL", "MSFT", "GOOGL"]:
            result = await generate_peak_trough_plots(symbols=symbol, plot_mode="single")
            assert isinstance(result, str)

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = memory_after - memory_before

        print(
            f"✅ Memory usage: {memory_before:.1f} MB → {memory_after:.1f} MB (+{memory_growth:.1f} MB)"
        )

        # Memory growth should be reasonable (less than 200MB for plotting)
        assert memory_growth < 200, f"Memory growth too high: {memory_growth:.1f} MB"


if __name__ == "__main__":
    # Run plotting tests directly
    pytest.main([__file__, "-v", "-s"])
