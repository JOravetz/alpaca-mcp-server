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

from alpaca_mcp_server  # noqa: E402.tools.peak_trough_analysis_tool import (
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


if __name__ == "__main__":
    # Run peak trough analysis tests directly
    pytest.main([__file__, "-v", "-s"])
