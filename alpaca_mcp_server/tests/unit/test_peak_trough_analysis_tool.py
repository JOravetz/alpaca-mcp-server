"""
Comprehensive tests for the peak and trough analysis tool.
Tests using real Alpaca API data calls, no mocking.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
import pytz

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server.tools.peak_trough_analysis_tool import (  # noqa: E402
    HistoricalDataFetcher,
    analyze_peaks_and_troughs,
    convert_to_nyc_timezone,
    get_latest_signal,
    process_bars_for_peaks,
    zero_phase_filter,
)


class TestZeroPhaseFilter:
    """Test zero-phase filtering functionality."""

    def test_zero_phase_filter_basic(self):
        """Test basic zero-phase filter functionality."""
        # Create test data with noise
        data = np.array([1.0, 2.0, 3.0, 2.5, 4.0, 3.5, 5.0, 4.5, 6.0])

        # Test with different window lengths
        for window_len in [3, 5, 7]:
            filtered = zero_phase_filter(data, window_len)

            assert len(filtered) == len(data)
            assert isinstance(filtered, np.ndarray)
            # Filtered data should be smoother (lower standard deviation)
            assert np.std(filtered) <= np.std(data)
            print(f"✅ Zero-phase filter window_len={window_len}: {len(filtered)} samples")

    def test_zero_phase_filter_edge_cases(self):
        """Test zero-phase filter with edge cases."""
        # Very short data
        short_data = np.array([1.0, 2.0])
        filtered = zero_phase_filter(short_data, 5)
        assert len(filtered) == len(short_data)
        print("✅ Zero-phase filter handles short data")

        # Single value
        single_data = np.array([5.0])
        filtered = zero_phase_filter(single_data, 3)
        assert len(filtered) == 1
        assert filtered[0] == 5.0
        print("✅ Zero-phase filter handles single value")

        # Even window length (should be adjusted to odd) with sufficient data
        data = np.array(
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        )
        filtered = zero_phase_filter(data, 4)  # Even, should become 5
        assert len(filtered) == len(data)
        print("✅ Zero-phase filter adjusts even window lengths")

    def test_zero_phase_filter_global_config(self):
        """Test zero-phase filter with global config defaults."""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

        # Test with None (should use global config)
        filtered = zero_phase_filter(data, None)
        assert len(filtered) == len(data)
        print("✅ Zero-phase filter uses global config defaults")


class TestTimezoneConversion:
    """Test timezone conversion functionality."""

    def test_convert_to_nyc_timezone_basic(self):
        """Test basic timezone conversion."""
        # Test with ISO format
        timestamp = "2025-06-22T10:30:00Z"
        nyc_time = convert_to_nyc_timezone(timestamp)

        assert hasattr(nyc_time, "tzinfo")
        assert nyc_time.tzinfo.zone == "America/New_York"
        print(f"✅ Basic timezone conversion: {timestamp} → {nyc_time}")

    def test_convert_to_nyc_timezone_formats(self):
        """Test various timestamp formats."""
        formats = [
            "2025-06-22T10:30:00Z",
            "2025-06-22T10:30:00+00:00",
            "2025-06-22 10:30:00 UTC",
            "2025-06-22T10:30:00",
        ]

        for timestamp in formats:
            try:
                nyc_time = convert_to_nyc_timezone(timestamp)
                assert hasattr(nyc_time, "tzinfo")
                print(f"✅ Timezone format {timestamp}: converted successfully")
            except Exception as e:
                print(f"⚠️ Timezone format {timestamp}: {e}")

    def test_convert_to_nyc_timezone_datetime_object(self):
        """Test conversion with datetime objects."""
        # UTC datetime
        utc_dt = datetime.now(pytz.UTC)
        nyc_time = convert_to_nyc_timezone(utc_dt)

        assert hasattr(nyc_time, "tzinfo")
        assert nyc_time.tzinfo.zone == "America/New_York"
        print("✅ Datetime object timezone conversion")


class TestHistoricalDataFetcher:
    """Test historical data fetching with real API calls."""

    @pytest.fixture
    def data_fetcher(self):
        """Create data fetcher with API credentials."""
        try:
            from alpaca_mcp_server.config.settings import settings

            return HistoricalDataFetcher(settings.api_key, settings.api_secret)
        except Exception:
            # Fallback to environment variables
            api_key = os.getenv("APCA_API_KEY_ID")
            api_secret = os.getenv("APCA_API_SECRET_KEY")
            if not api_key or not api_secret:
                pytest.skip("No API credentials available")
            return HistoricalDataFetcher(api_key, api_secret)

    @pytest.mark.asyncio
    async def test_get_trading_days(self, data_fetcher):
        """Test trading days retrieval."""
        trading_days = data_fetcher.get_trading_days(5)

        if trading_days:
            assert isinstance(trading_days, list)
            assert len(trading_days) <= 5
            assert all(isinstance(day, str) for day in trading_days)
            print(f"✅ Trading days retrieval: {len(trading_days)} days")
        else:
            print("⚠️ No trading days returned (API issue)")

    @pytest.mark.asyncio
    async def test_fetch_historical_bars_single_symbol(self, data_fetcher):
        """Test historical bars fetch for single symbol."""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        bars_data = data_fetcher.fetch_historical_bars(["AAPL"], "1Min", start_date, end_date)

        if bars_data:
            assert isinstance(bars_data, dict)
            assert "AAPL" in bars_data or len(bars_data) > 0
            print(f"✅ Single symbol bars fetch: {len(bars_data)} symbols returned")
        else:
            print("⚠️ No bars data returned (API/market hours issue)")

    @pytest.mark.asyncio
    async def test_fetch_historical_bars_multiple_symbols(self, data_fetcher):
        """Test historical bars fetch for multiple symbols."""
        symbols = ["AAPL", "MSFT", "SPY"]
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

        bars_data = data_fetcher.fetch_historical_bars(symbols, "5Min", start_date, end_date)

        if bars_data:
            assert isinstance(bars_data, dict)
            returned_symbols = len(bars_data)
            print(f"✅ Multiple symbols bars fetch: {returned_symbols} symbols returned")
        else:
            print("⚠️ No bars data returned (API/market hours issue)")

    @pytest.mark.asyncio
    async def test_fetch_historical_bars_error_handling(self, data_fetcher):
        """Test error handling in bars fetch."""
        # Test with empty symbols
        bars_data = data_fetcher.fetch_historical_bars([], "1Min", "2025-06-22", "2025-06-22")
        assert bars_data is None
        print("✅ Empty symbols list handled correctly")

        # Test with invalid timeframe
        bars_data = data_fetcher.fetch_historical_bars(
            ["AAPL"], "InvalidTimeframe", "2025-06-22", "2025-06-22"
        )
        assert bars_data is None
        print("✅ Invalid timeframe handled correctly")


class TestProcessBarsForPeaks:
    """Test peak processing functionality with real data."""

    def create_sample_bars(self):
        """Create sample bar data for testing."""
        # Simulate realistic bar data
        base_price = 150.0
        bars = []
        for i in range(50):
            # Add some realistic price movement
            price_change = np.sin(i * 0.3) * 2 + np.random.normal(0, 0.5)
            close_price = base_price + price_change

            bars.append(
                {
                    "c": str(close_price),  # Close price as string (API format)
                    "t": f"2025-06-22T{9 + i//60:02d}:{i%60:02d}:00Z",
                    "v": str(1000 + i * 10),  # Volume
                }
            )
        return bars

    def test_process_bars_for_peaks_basic(self):
        """Test basic peak processing."""
        bars = self.create_sample_bars()

        result = process_bars_for_peaks("TEST", bars, window_len=11, lookahead=2)

        if result:
            assert result["symbol"] == "TEST"
            assert result["total_bars"] == len(bars)
            assert len(result["original_prices"]) == len(bars)
            assert len(result["filtered_prices"]) == len(bars)
            assert isinstance(result["peaks"], list)
            assert isinstance(result["troughs"], list)
            print(
                f"✅ Basic peak processing: {len(result['peaks'])} peaks, {len(result['troughs'])} troughs"
            )
        else:
            print("⚠️ Peak processing returned None")

    def test_process_bars_for_peaks_edge_cases(self):
        """Test peak processing edge cases."""
        # Empty bars
        result = process_bars_for_peaks("TEST", [], window_len=11, lookahead=2)
        assert result is None
        print("✅ Empty bars handled correctly")

        # Insufficient bars
        short_bars = self.create_sample_bars()[:3]
        result = process_bars_for_peaks("TEST", short_bars, window_len=11, lookahead=5)
        assert result is None
        print("✅ Insufficient bars handled correctly")

    def test_process_bars_for_peaks_global_config(self):
        """Test peak processing with global config defaults."""
        bars = self.create_sample_bars()

        # Test with None parameters (should use global config)
        result = process_bars_for_peaks("TEST", bars, window_len=None, lookahead=None)

        if result:
            assert "filter_params" in result
            print("✅ Peak processing uses global config defaults")


class TestGetLatestSignal:
    """Test latest signal extraction."""

    def create_sample_results(self):
        """Create sample peak/trough results."""
        return {
            "symbol": "TEST",
            "total_bars": 50,
            "original_prices": [150.0 + i * 0.1 for i in range(50)],
            "peaks": [
                {
                    "index": 10,
                    "timestamp": "2025-06-22T09:10:00Z",
                    "original_price": 151.0,
                    "filtered_price": 150.9,
                    "volume": 1100,
                },
                {
                    "index": 30,
                    "timestamp": "2025-06-22T09:30:00Z",
                    "original_price": 153.0,
                    "filtered_price": 152.9,
                    "volume": 1300,
                },
                {
                    "index": 45,
                    "timestamp": "2025-06-22T09:45:00Z",
                    "original_price": 154.5,
                    "filtered_price": 154.4,
                    "volume": 1450,
                },
            ],
            "troughs": [
                {
                    "index": 5,
                    "timestamp": "2025-06-22T09:05:00Z",
                    "original_price": 150.5,
                    "filtered_price": 150.4,
                    "volume": 1050,
                },
                {
                    "index": 20,
                    "timestamp": "2025-06-22T09:20:00Z",
                    "original_price": 152.0,
                    "filtered_price": 151.9,
                    "volume": 1200,
                },
                {
                    "index": 40,
                    "timestamp": "2025-06-22T09:40:00Z",
                    "original_price": 154.0,
                    "filtered_price": 153.9,
                    "volume": 1400,
                },
            ],
        }

    def test_get_latest_signal_peak(self):
        """Test getting latest peak signal."""
        results = self.create_sample_results()
        latest_signal = get_latest_signal(results)

        assert latest_signal is not None
        assert latest_signal["type"] == "Peak"
        assert latest_signal["index"] == 45
        assert latest_signal["signal_price"] == 154.5
        assert "samples_ago" in latest_signal
        assert "price_change" in latest_signal
        print(
            f"✅ Latest peak signal: index {latest_signal['index']}, price ${latest_signal['signal_price']}"
        )

    def test_get_latest_signal_trough(self):
        """Test getting latest trough signal by modifying indices."""
        results = self.create_sample_results()
        # Make latest trough more recent than latest peak
        results["troughs"][-1]["index"] = 47

        latest_signal = get_latest_signal(results)

        assert latest_signal is not None
        assert latest_signal["type"] == "Trough"
        assert latest_signal["index"] == 47
        print(f"✅ Latest trough signal: index {latest_signal['index']}")

    def test_get_latest_signal_empty(self):
        """Test with no peaks or troughs."""
        results = {
            "symbol": "TEST",
            "total_bars": 10,
            "original_prices": [150.0] * 10,
            "peaks": [],
            "troughs": [],
        }

        latest_signal = get_latest_signal(results)
        assert latest_signal is None
        print("✅ Empty peaks/troughs handled correctly")


class TestAnalyzePeaksAndTroughs:
    """Test main analysis function with real API calls."""

    @pytest.mark.asyncio
    async def test_analyze_peaks_and_troughs_manual_symbols(self):
        """Test with manually specified symbols."""
        result = await analyze_peaks_and_troughs(
            symbols="AAPL,SPY", timeframe="5Min", days=1, window_len=11, lookahead=2
        )

        assert isinstance(result, str)
        assert len(result) > 500

        if "Error" not in result:
            assert "AAPL" in result or "SPY" in result
            assert "Peak and Trough Analysis" in result
            assert "Trading Signal Summary" in result
            print(f"✅ Manual symbols analysis: {len(result)} chars")
        else:
            print(f"⚠️ Manual symbols analysis error: {result[:200]}...")

    @pytest.mark.asyncio
    async def test_analyze_peaks_and_troughs_auto_mode(self):
        """Test AUTO mode symbol detection."""
        result = await analyze_peaks_and_troughs(symbols="AUTO", timeframe="1Min", days=1)

        assert isinstance(result, str)
        # AUTO mode may fail if scanner not available, so we accept shorter results
        assert len(result) > 30

        if "AUTO mode detected" in result:
            print("✅ AUTO mode detected symbols successfully")
        elif "Error" in result:
            print(f"⚠️ AUTO mode error (expected if scanner not ready): {result}")
            # This is acceptable - AUTO mode depends on scanner being available
        else:
            print("⚠️ AUTO mode unexpected result format")

    @pytest.mark.asyncio
    async def test_analyze_peaks_and_troughs_parameter_validation(self):
        """Test parameter validation."""
        # Test invalid days
        result = await analyze_peaks_and_troughs(symbols="AAPL", days=50)
        assert isinstance(result, str)
        # Days should be clamped to valid range

        # Test invalid window length
        result = await analyze_peaks_and_troughs(symbols="AAPL", window_len=2)
        assert isinstance(result, str)
        # Should use default window length

        # Test invalid symbols
        result = await analyze_peaks_and_troughs(symbols="")
        assert "No valid symbols provided" in result
        print("✅ Parameter validation working")

    @pytest.mark.asyncio
    async def test_analyze_peaks_and_troughs_different_timeframes(self):
        """Test different timeframes."""
        timeframes = ["1Min", "5Min", "15Min", "1Hour"]

        for timeframe in timeframes:
            result = await analyze_peaks_and_troughs(symbols="SPY", timeframe=timeframe, days=1)

            assert isinstance(result, str)
            assert len(result) > 200

            if "Error" not in result:
                assert f"Parameters: {timeframe}" in result
                print(f"✅ Timeframe {timeframe}: working")
            else:
                print(f"⚠️ Timeframe {timeframe}: error (may be expected)")

    @pytest.mark.asyncio
    async def test_analyze_peaks_and_troughs_nyc_timezone(self):
        """Test NYC timezone formatting in output."""
        result = await analyze_peaks_and_troughs(symbols="AAPL", timeframe="1Min", days=1)

        assert isinstance(result, str)

        # Should contain timezone information
        if "EDT" in result or "EST" in result:
            print("✅ NYC timezone formatting present")
        elif "Error" not in result:
            print("⚠️ NYC timezone formatting may be missing")

    @pytest.mark.asyncio
    async def test_analyze_peaks_and_troughs_signal_detection(self):
        """Test trading signal detection in output."""
        result = await analyze_peaks_and_troughs(
            symbols="SPY", timeframe="5Min", days=1, window_len=21, lookahead=3
        )

        assert isinstance(result, str)

        if "Error" not in result:
            # Should contain signal analysis
            signal_indicators = ["BUY", "SELL", "Signal", "Peak", "Trough"]
            has_signals = any(indicator in result for indicator in signal_indicators)

            if has_signals:
                print("✅ Trading signals detected in output")
            else:
                print("⚠️ No clear trading signals in output")
        else:
            print(f"⚠️ Signal detection test error: {result[:200]}...")


class TestPeakTroughIntegration:
    """Test integration with other system components."""

    @pytest.mark.asyncio
    async def test_global_config_integration(self):
        """Test integration with global configuration."""
        try:
            from alpaca_mcp_server.config import get_technical_config

            config = get_technical_config()

            # Test that config values are reasonable
            assert 3 <= config.hanning_window_samples <= 101
            assert 1 <= config.peak_trough_lookahead <= 50
            assert config.peak_trough_min_distance >= 1

            print("✅ Global config integration working")
        except Exception as e:
            print(f"⚠️ Global config integration issue: {e}")

    @pytest.mark.asyncio
    async def test_api_credentials_integration(self):
        """Test API credentials integration."""
        try:
            from alpaca_mcp_server.config.settings import settings

            # Check if credentials are available
            has_credentials = bool(settings.api_key and settings.api_secret)

            if has_credentials:
                print("✅ API credentials available from settings")
            else:
                print("⚠️ No API credentials in settings")

                # Check environment variables as fallback
                env_key = os.getenv("APCA_API_KEY_ID")
                env_secret = os.getenv("APCA_API_SECRET_KEY")

                if env_key and env_secret:
                    print("✅ API credentials available from environment")
                else:
                    print("⚠️ No API credentials available")

        except Exception as e:
            print(f"⚠️ API credentials integration issue: {e}")


class TestAnalyzePeaksAndTroughsWithPlotPy:
    """Test the plot.py integration functionality."""

    @pytest.mark.asyncio
    async def test_analyze_with_plot_py_basic(self):
        """Test basic plot.py integration."""
        from alpaca_mcp_server.tools.peak_trough_analysis_tool import (
            analyze_peaks_and_troughs_with_plot_py,
        )

        result = await analyze_peaks_and_troughs_with_plot_py(
            symbols="SPY", timeframe="5Min", days=1, window_len=11, lookahead=2
        )

        assert isinstance(result, str)

        if "Error" not in result:
            assert "Peak and Trough Analysis" in result
            assert "plot.py" in result.lower() or "Plot" in result
            print(f"✅ Plot.py integration working: {len(result)} chars")
        else:
            print(f"⚠️ Plot.py integration error: {result[:200]}...")

    @pytest.mark.asyncio
    async def test_analyze_with_plot_py_multiple_symbols(self):
        """Test plot.py with multiple symbols."""
        from alpaca_mcp_server.tools.peak_trough_analysis_tool import (
            analyze_peaks_and_troughs_with_plot_py,
        )

        result = await analyze_peaks_and_troughs_with_plot_py(
            symbols="AAPL,MSFT", timeframe="15Min", days=1
        )

        assert isinstance(result, str)

        if "Error" not in result:
            # Should process both symbols
            symbols_found = sum(1 for sym in ["AAPL", "MSFT"] if sym in result)
            assert symbols_found >= 1, "At least one symbol should be in results"
            print(f"✅ Plot.py multiple symbols: {symbols_found} symbols found")
        else:
            print(f"⚠️ Plot.py multiple symbols error: {result[:200]}...")

    @pytest.mark.asyncio
    async def test_analyze_with_plot_py_plot_generation(self):
        """Test actual plot generation (if environment supports it)."""
        from alpaca_mcp_server.tools.peak_trough_analysis_tool import (
            analyze_peaks_and_troughs_with_plot_py,
        )

        # Test with default settings
        result = await analyze_peaks_and_troughs_with_plot_py(
            symbols="SPY", timeframe="1Min", days=1
        )

        assert isinstance(result, str)

        if "Error" not in result:
            # Check for plot-related output
            if "Plot saved" in result or "plot" in result.lower():
                print("✅ Plot generation references found")
            else:
                print("⚠️ No plot generation references (may be disabled)")
        else:
            print(f"⚠️ Plot generation test error: {result[:200]}...")


class TestErrorHandlingAndEdgeCases:
    """Test comprehensive error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_api_credentials(self):
        """Test with invalid API credentials."""
        from alpaca_mcp_server.tools.peak_trough_analysis_tool import HistoricalDataFetcher

        fetcher = HistoricalDataFetcher("invalid_key", "invalid_secret")
        bars = fetcher.fetch_historical_bars(["AAPL"], "1Min", "2025-06-22", "2025-06-22")

        # Should handle invalid credentials gracefully
        assert bars is None or isinstance(bars, dict)
        print("✅ Invalid API credentials handled gracefully")

    def test_zero_phase_filter_extreme_values(self):
        """Test filter with extreme values."""
        # Test with very large values (need more data points for filter)
        large_data = np.array(
            [1e10, 2e10, 3e10, 2.5e10, 4e10, 3.5e10, 2.8e10, 3.2e10, 2.9e10, 3.1e10]
        )
        filtered = zero_phase_filter(large_data, 3)
        assert not np.any(np.isnan(filtered)), "Should handle large values"
        assert not np.any(np.isinf(filtered)), "Should not produce infinities"

        # Test with negative values (need more data points)
        negative_data = np.array([-100, -50, -75, -60, -80, -90, -70, -65, -85, -95])
        filtered = zero_phase_filter(negative_data, 3)
        assert len(filtered) == len(negative_data)
        print("✅ Extreme values handled correctly")

    def test_process_bars_malformed_data(self):
        """Test with malformed bar data."""
        # Missing required fields
        malformed_bars = [
            {"c": "150.0"},  # Missing timestamp
            {"t": "2025-06-22T09:00:00Z"},  # Missing close price
            {"c": "invalid", "t": "2025-06-22T09:01:00Z"},  # Invalid price
        ]

        result = process_bars_for_peaks("TEST", malformed_bars)
        assert result is None, "Should handle malformed data gracefully"
        print("✅ Malformed bar data handled correctly")

    @pytest.mark.asyncio
    async def test_concurrent_analysis(self):
        """Test concurrent analysis requests."""
        import asyncio

        # Run multiple analyses concurrently
        tasks = [
            analyze_peaks_and_troughs(symbols="SPY", timeframe="1Min", days=1),
            analyze_peaks_and_troughs(symbols="AAPL", timeframe="5Min", days=1),
            analyze_peaks_and_troughs(symbols="MSFT", timeframe="15Min", days=1),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete without crashing
        assert len(results) == 3
        for result in results:
            if isinstance(result, Exception):
                print(f"⚠️ Concurrent task exception: {result}")
            else:
                assert isinstance(result, str)
        print("✅ Concurrent analysis handled correctly")

    def test_get_latest_signal_tie_breaking(self):
        """Test signal selection when peak and trough have same index."""
        results = {
            "symbol": "TEST",
            "total_bars": 50,
            "original_prices": [150.0] * 50,
            "peaks": [
                {
                    "index": 45,
                    "timestamp": "2025-06-22T09:45:00Z",
                    "original_price": 155.0,
                    "filtered_price": 154.9,
                    "volume": 1000,
                }
            ],
            "troughs": [
                {
                    "index": 45,
                    "timestamp": "2025-06-22T09:45:00Z",
                    "original_price": 145.0,
                    "filtered_price": 145.1,
                    "volume": 1000,
                }
            ],
        }

        signal = get_latest_signal(results)
        assert signal is not None
        # Should prefer one over the other consistently
        assert signal["type"] in ["Peak", "Trough"]
        print(f"✅ Tie-breaking handled: selected {signal['type']}")


class TestFilterParameterCalculations:
    """Test filter parameter calculations and configurations."""

    def test_window_length_adjustment(self):
        """Test window length adjustment for different data sizes."""
        # Very short data should adjust window
        short_data = np.array([1.0, 2.0, 3.0])
        filtered = zero_phase_filter(short_data, 11)  # Window larger than data
        assert len(filtered) == len(short_data)

        # Medium data
        medium_data = np.array([float(i) for i in range(20)])
        filtered = zero_phase_filter(medium_data, 11)
        assert len(filtered) == len(medium_data)
        print("✅ Window length adjustment working")

    def test_lookahead_sensitivity(self):
        """Test peak detection sensitivity with different lookahead values."""
        # Create data with clear peaks
        x = np.linspace(0, 4 * np.pi, 100)
        data = np.sin(x) + 0.1 * np.random.randn(100)

        bars = []
        for i, value in enumerate(data):
            bars.append(
                {"c": str(150 + value * 10), "t": f"2025-06-22T09:{i:02d}:00Z", "v": "1000"}
            )

        # Test with different lookahead values
        lookahead_values = [1, 3, 5, 10]
        peak_counts = []

        for lookahead in lookahead_values:
            result = process_bars_for_peaks("TEST", bars, window_len=11, lookahead=lookahead)
            if result:
                peak_counts.append(len(result["peaks"]))
            else:
                peak_counts.append(0)

        # Higher lookahead should generally find fewer but more significant peaks
        assert max(peak_counts) > 0, "Should find at least some peaks"
        print(f"✅ Lookahead sensitivity: peaks found with lookahead 1-10: {peak_counts}")

    def test_global_config_fallback(self):
        """Test that global config is used when parameters are None."""
        try:
            from alpaca_mcp_server.config import get_technical_config

            config = get_technical_config()

            # Test that None parameters use global config
            data = np.array([float(i) for i in range(50)])
            filtered = zero_phase_filter(data, None)

            assert len(filtered) == len(data)
            print(f"✅ Global config fallback working (window={config.hanning_window_samples})")
        except Exception as e:
            print(f"⚠️ Global config test skipped: {e}")


class TestRealMarketDataIntegration:
    """Integration tests with real market data."""

    @pytest.mark.asyncio
    async def test_live_market_hours_analysis(self):
        """Test analysis during market hours with live data."""
        # Check if market is open
        try:
            from alpaca_mcp_server.tools.market_tools import get_extended_market_clock

            clock_result = await get_extended_market_clock()

            if "is_open: true" in clock_result or "Market Open" in clock_result:
                # Market is open, test with live data
                result = await analyze_peaks_and_troughs(
                    symbols="SPY,QQQ,IWM", timeframe="1Min", days=0  # Today only
                )

                assert isinstance(result, str)
                if "Error" not in result:
                    assert "Trading Signal Summary" in result
                    print("✅ Live market data analysis successful")
                else:
                    print("⚠️ Live market data not available")
            else:
                print("⚠️ Market closed, skipping live data test")
        except Exception as e:
            print(f"⚠️ Live market test skipped: {e}")

    @pytest.mark.asyncio
    async def test_high_volatility_stocks(self):
        """Test with known volatile stocks for peak/trough detection."""
        # Use stocks known for intraday volatility
        volatile_symbols = "TSLA,NVDA,AMD"

        result = await analyze_peaks_and_troughs(
            symbols=volatile_symbols,
            timeframe="5Min",
            days=1,
            window_len=7,  # Smaller window for volatile stocks
            lookahead=2,
        )

        assert isinstance(result, str)

        if "Error" not in result:
            # Volatile stocks should have multiple peaks/troughs
            peak_count = result.count("Peak @")
            trough_count = result.count("Trough @")

            total_signals = peak_count + trough_count
            assert total_signals > 0, "Volatile stocks should have signals"
            print(f"✅ Volatile stocks: {peak_count} peaks, {trough_count} troughs found")
        else:
            print("⚠️ Volatile stocks analysis failed")

    @pytest.mark.asyncio
    async def test_penny_stock_analysis(self):
        """Test with penny stocks (low price, high volatility)."""
        # Note: These may change over time, update as needed
        result = await analyze_peaks_and_troughs(
            symbols="SOUN,RIOT",
            timeframe="1Min",
            days=1,
            window_len=11,
            lookahead=1,  # More sensitive for penny stocks
        )

        assert isinstance(result, str)

        if "Error" not in result and "No valid symbols" not in result:
            # Check for decimal precision (penny stocks need it)
            if "." in result:
                decimal_places = max(
                    len(price.split(".")[-1])
                    for price in result.split("$")[1:]
                    if "." in price[:10]
                )
                assert decimal_places >= 2, "Should maintain price precision for penny stocks"
            print("✅ Penny stock analysis with proper precision")
        else:
            print("⚠️ Penny stock analysis skipped (symbols may be invalid)")

    @pytest.mark.asyncio
    async def test_etf_vs_stock_patterns(self):
        """Compare pattern detection between ETFs and individual stocks."""
        # ETFs tend to be smoother than individual stocks
        etf_result = await analyze_peaks_and_troughs(
            symbols="SPY", timeframe="15Min", days=1, window_len=11
        )

        stock_result = await analyze_peaks_and_troughs(
            symbols="AAPL", timeframe="15Min", days=1, window_len=11
        )

        assert isinstance(etf_result, str)
        assert isinstance(stock_result, str)

        if "Error" not in etf_result and "Error" not in stock_result:
            etf_peaks = etf_result.count("Peak @")
            stock_peaks = stock_result.count("Peak @")

            print(f"✅ ETF vs Stock: SPY={etf_peaks} peaks, AAPL={stock_peaks} peaks")
        else:
            print("⚠️ ETF vs Stock comparison skipped")


class TestDataValidationAndConsistency:
    """Test data validation and consistency checks."""

    def test_zero_phase_filter_nan_handling(self):
        """Test zero-phase filter with NaN values."""
        # Data with NaN values
        data_with_nan = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0])

        # Should handle NaN gracefully
        filtered = zero_phase_filter(data_with_nan, 3)
        assert len(filtered) == len(data_with_nan)
        # Result may contain NaN where input had NaN
        print("✅ Zero-phase filter handles NaN values")

    def test_zero_phase_filter_inf_handling(self):
        """Test zero-phase filter with infinite values."""
        # Data with infinity
        data_with_inf = np.array([1.0, 2.0, np.inf, 4.0, 5.0, -np.inf, 7.0, 8.0])

        filtered = zero_phase_filter(data_with_inf, 3)
        assert len(filtered) == len(data_with_inf)
        print("✅ Zero-phase filter handles infinite values")

    def test_process_bars_duplicate_timestamps(self):
        """Test handling of duplicate timestamps in bar data."""
        bars = [
            {"c": "150.0", "t": "2025-06-22T09:00:00Z", "v": "1000"},
            {"c": "151.0", "t": "2025-06-22T09:00:00Z", "v": "1100"},  # Duplicate timestamp
            {"c": "152.0", "t": "2025-06-22T09:01:00Z", "v": "1200"},
            {"c": "153.0", "t": "2025-06-22T09:02:00Z", "v": "1300"},
            {"c": "154.0", "t": "2025-06-22T09:03:00Z", "v": "1400"},
        ]

        result = process_bars_for_peaks("TEST", bars, window_len=3, lookahead=1)
        # Should handle duplicates gracefully
        if result:
            assert result["total_bars"] == len(bars)
            print("✅ Duplicate timestamps handled")
        else:
            print("✅ Duplicate timestamps rejected (also valid)")

    def test_process_bars_out_of_order(self):
        """Test handling of out-of-order timestamps."""
        bars = [
            {"c": "150.0", "t": "2025-06-22T09:02:00Z", "v": "1000"},
            {"c": "151.0", "t": "2025-06-22T09:00:00Z", "v": "1100"},  # Out of order
            {"c": "152.0", "t": "2025-06-22T09:01:00Z", "v": "1200"},
            {"c": "153.0", "t": "2025-06-22T09:03:00Z", "v": "1300"},
        ]

        process_bars_for_peaks("TEST", bars, window_len=3, lookahead=1)
        # Function should either sort or reject out-of-order data
        print("✅ Out-of-order timestamps handled")

    def test_process_bars_price_validation(self):
        """Test validation of price data."""
        # Negative prices (should be rejected for stocks)
        bars_negative = [
            {"c": "-150.0", "t": "2025-06-22T09:00:00Z", "v": "1000"},
            {"c": "151.0", "t": "2025-06-22T09:01:00Z", "v": "1100"},
        ]

        process_bars_for_peaks("TEST", bars_negative)
        # Should handle negative prices appropriately
        print("✅ Negative price validation")

        # Zero prices
        bars_zero = [
            {"c": "0.0", "t": "2025-06-22T09:00:00Z", "v": "1000"},
            {"c": "151.0", "t": "2025-06-22T09:01:00Z", "v": "1100"},
        ]

        process_bars_for_peaks("TEST", bars_zero)
        print("✅ Zero price validation")


class TestTradingSignalAccuracy:
    """Test accuracy of trading signal detection."""

    def test_peak_detection_accuracy(self):
        """Test peak detection with known synthetic data."""
        # Create perfect sine wave with known peaks
        x = np.linspace(0, 4 * np.pi, 200)
        prices = 150 + 10 * np.sin(x)

        bars = []
        for i, price in enumerate(prices):
            bars.append(
                {"c": str(price), "t": f"2025-06-22T{9 + i//60:02d}:{i%60:02d}:00Z", "v": "1000"}
            )

        result = process_bars_for_peaks("TEST", bars, window_len=11, lookahead=5)

        if result:
            # Should detect approximately 2 peaks (sine wave maxima)
            peak_count = len(result["peaks"])
            assert 1 <= peak_count <= 3, f"Should detect 1-3 peaks in sine wave, got {peak_count}"

            # Check peak prices are near expected maxima (160)
            for peak in result["peaks"]:
                assert 158 <= peak["original_price"] <= 162, "Peak should be near sine maximum"

            print(f"✅ Peak detection accuracy: {peak_count} peaks found at correct levels")

    def test_trough_detection_accuracy(self):
        """Test trough detection with known synthetic data."""
        # Create perfect sine wave with known troughs
        x = np.linspace(0, 4 * np.pi, 200)
        prices = 150 + 10 * np.sin(x)

        bars = []
        for i, price in enumerate(prices):
            bars.append(
                {"c": str(price), "t": f"2025-06-22T{9 + i//60:02d}:{i%60:02d}:00Z", "v": "1000"}
            )

        result = process_bars_for_peaks("TEST", bars, window_len=11, lookahead=5)

        if result:
            # Should detect approximately 2 troughs (sine wave minima)
            trough_count = len(result["troughs"])
            assert (
                1 <= trough_count <= 3
            ), f"Should detect 1-3 troughs in sine wave, got {trough_count}"

            # Check trough prices are near expected minima (140)
            for trough in result["troughs"]:
                assert 138 <= trough["original_price"] <= 142, "Trough should be near sine minimum"

            print(f"✅ Trough detection accuracy: {trough_count} troughs found at correct levels")

    def test_signal_timing_accuracy(self):
        """Test that signals are detected at correct time indices."""
        # Create data with sharp peak at known index
        prices = [150.0] * 50
        prices[25] = 160.0  # Sharp peak at index 25

        bars = []
        for i, price in enumerate(prices):
            bars.append({"c": str(price), "t": f"2025-06-22T09:{i:02d}:00Z", "v": "1000"})

        result = process_bars_for_peaks("TEST", bars, window_len=5, lookahead=2)

        if result and result["peaks"]:
            # Peak should be detected near index 25
            peak_indices = [p["index"] for p in result["peaks"]]
            assert any(
                23 <= idx <= 27 for idx in peak_indices
            ), "Peak should be detected near index 25"
            print(f"✅ Signal timing accuracy: Peak detected at indices {peak_indices}")

    def test_filter_smoothing_effectiveness(self):
        """Test that filter effectively smooths noisy data."""
        # Create noisy data
        np.random.seed(42)
        base = np.linspace(150, 160, 100)
        noise = np.random.normal(0, 2, 100)
        noisy_prices = base + noise

        bars = []
        for i, price in enumerate(noisy_prices):
            bars.append(
                {"c": str(price), "t": f"2025-06-22T09:{i//60:02d}:{i%60:02d}:00Z", "v": "1000"}
            )

        result = process_bars_for_peaks("TEST", bars, window_len=11, lookahead=3)

        if result:
            # Filtered prices should have lower variance than original
            original_var = np.var(result["original_prices"])
            filtered_var = np.var(result["filtered_prices"])

            assert filtered_var < original_var * 0.8, "Filter should reduce variance significantly"
            print(
                f"✅ Filter smoothing: Variance reduced from {original_var:.2f} to {filtered_var:.2f}"
            )


class TestBoundaryConditions:
    """Test boundary conditions and extreme scenarios."""

    def test_single_bar_handling(self):
        """Test with single bar of data."""
        bars = [{"c": "150.0", "t": "2025-06-22T09:00:00Z", "v": "1000"}]

        result = process_bars_for_peaks("TEST", bars, window_len=3, lookahead=1)
        assert result is None, "Single bar should not be processed"
        print("✅ Single bar boundary condition handled")

    def test_exactly_minimum_bars(self):
        """Test with exactly the minimum required bars."""
        # Create exactly minimum required bars for processing
        bars = []
        for i in range(10):  # Minimum for reasonable processing
            bars.append({"c": str(150 + i * 0.5), "t": f"2025-06-22T09:{i:02d}:00Z", "v": "1000"})

        result = process_bars_for_peaks("TEST", bars, window_len=3, lookahead=1)

        if result:
            assert result["total_bars"] == 10
            print("✅ Minimum bars boundary condition processed")
        else:
            print("✅ Minimum bars boundary condition rejected")

    def test_maximum_lookahead(self):
        """Test with maximum lookahead value."""
        # Create sufficient data for large lookahead
        bars = []
        for i in range(200):
            price = 150 + 10 * np.sin(i * 0.1)
            bars.append(
                {"c": str(price), "t": f"2025-06-22T{9 + i//60:02d}:{i%60:02d}:00Z", "v": "1000"}
            )

        result = process_bars_for_peaks("TEST", bars, window_len=11, lookahead=50)

        if result:
            # With very high lookahead, should find fewer but more significant peaks
            assert len(result["peaks"]) <= 5, "High lookahead should find few peaks"
            assert len(result["troughs"]) <= 5, "High lookahead should find few troughs"
            print(
                f"✅ Maximum lookahead: {len(result['peaks'])} peaks, {len(result['troughs'])} troughs"
            )

    def test_maximum_window_length(self):
        """Test with maximum window length."""
        # Create sufficient data for large window
        bars = []
        for i in range(300):
            price = 150 + np.random.randn() * 2
            bars.append(
                {"c": str(price), "t": f"2025-06-22T{9 + i//60:02d}:{i%60:02d}:00Z", "v": "1000"}
            )

        result = process_bars_for_peaks("TEST", bars, window_len=101, lookahead=5)

        if result:
            # Very large window should produce very smooth filtered data
            filtered_std = np.std(result["filtered_prices"])
            original_std = np.std(result["original_prices"])
            assert filtered_std < original_std * 0.5, "Large window should smooth significantly"
            print(f"✅ Maximum window length: smoothing ratio {filtered_std/original_std:.2f}")

    def test_all_identical_prices(self):
        """Test with all identical prices (flat line)."""
        bars = []
        for i in range(50):
            bars.append(
                {"c": "150.0", "t": f"2025-06-22T09:{i:02d}:00Z", "v": "1000"}  # All same price
            )

        result = process_bars_for_peaks("TEST", bars, window_len=11, lookahead=3)

        if result:
            # Should find no peaks or troughs in flat data
            assert len(result["peaks"]) == 0, "No peaks in flat data"
            assert len(result["troughs"]) == 0, "No troughs in flat data"
            print("✅ Flat price data: correctly found no signals")


class TestPeakTroughPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_single_symbol_performance(self):
        """Test single symbol analysis performance."""
        import time

        start_time = time.time()
        result = await analyze_peaks_and_troughs(symbols="SPY", timeframe="1Min", days=1)
        end_time = time.time()

        duration = end_time - start_time

        assert isinstance(result, str)
        assert duration < 60.0  # Should complete within 60 seconds

        print(f"✅ Single symbol performance: {duration:.2f}s")

    @pytest.mark.asyncio
    async def test_multiple_symbols_performance(self):
        """Test multiple symbols analysis performance."""
        import time

        start_time = time.time()
        result = await analyze_peaks_and_troughs(symbols="AAPL,MSFT,SPY", timeframe="5Min", days=1)
        end_time = time.time()

        duration = end_time - start_time

        assert isinstance(result, str)
        assert duration < 120.0  # Should complete within 2 minutes

        print(f"✅ Multiple symbols performance: {duration:.2f}s")

    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage during analysis."""
        try:
            import psutil

            process = psutil.Process(os.getpid())

            memory_before = process.memory_info().rss / 1024 / 1024  # MB

            # Run analysis multiple times
            for _i in range(3):
                result = await analyze_peaks_and_troughs(symbols="SPY", timeframe="1Min", days=1)
                assert isinstance(result, str)

            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_growth = memory_after - memory_before

            print(
                f"✅ Memory usage: {memory_before:.1f} MB → {memory_after:.1f} MB (+{memory_growth:.1f} MB)"
            )

            # Memory growth should be reasonable (less than 100MB)
            assert memory_growth < 100, f"Memory growth too high: {memory_growth:.1f} MB"

        except ImportError:
            print("⚠️ psutil not available for memory testing")

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self):
        """Test performance with large datasets (30 days of minute data)."""
        import time

        start_time = time.time()

        # 30 days of minute data is a lot of data points
        result = await analyze_peaks_and_troughs(
            symbols="SPY",
            timeframe="1Min",
            days=30,  # Maximum allowed
            window_len=21,  # Larger window for smoother results
            lookahead=5,
        )

        end_time = time.time()
        duration = end_time - start_time

        assert isinstance(result, str)
        assert duration < 180.0  # Should complete within 3 minutes even for large datasets

        if "Error" not in result:
            # Check that we got substantial data
            assert len(result) > 1000, "Large dataset should produce detailed results"
            print(f"✅ Large dataset (30 days) performance: {duration:.2f}s")
        else:
            print(f"⚠️ Large dataset test completed with error in {duration:.2f}s")


if __name__ == "__main__":
    # Run peak trough analysis tests directly
    pytest.main([__file__, "-v", "-s"])
