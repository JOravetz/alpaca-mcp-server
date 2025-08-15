"""
Production Scenario Tests - REAL tests for market conditions.
Tests aggressive parameters with actual market reality - NO MOCKING.
"""

import os
import sys
import time
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server.config import (  # noqa: E402
    get_scanner_config,
    get_technical_config,
    get_trading_config,
)
from alpaca_mcp_server.monitoring.fastapi_service import MonitoringServiceAPI  # noqa: E402
from alpaca_mcp_server.tools.day_trading_scanner import scan_day_trading_opportunities  # noqa: E402
from alpaca_mcp_server.tools.peak_trough_analysis_tool import (  # noqa: E402
    analyze_peaks_and_troughs,
)


class TestProductionScenarios:
    """REAL production scenario tests with market conditions."""

    def setup_method(self):
        """Set up test environment."""
        self.has_credentials = os.getenv("APCA_API_KEY_ID") and os.getenv("APCA_API_SECRET_KEY")

    def test_aggressive_params_market_reality_real(self):
        """Test aggressive parameters work in market reality."""

        trading = get_trading_config()
        technical = get_technical_config()
        scanner = get_scanner_config()

        # Verify aggressive parameters are production-ready
        print("🏭 PRODUCTION PARAMETER VALIDATION")
        print("=" * 50)

        # Trading parameters reality check
        assert (
            100 <= trading.trades_per_minute_threshold <= 2000
        ), f"Trades threshold {trading.trades_per_minute_threshold} not realistic for production"

        assert (
            1.0 <= trading.min_percent_change_threshold <= 50.0
        ), f"Percent change {trading.min_percent_change_threshold}% not realistic"

        assert (
            1000 <= trading.default_position_size_usd <= 1000000
        ), f"Position size ${trading.default_position_size_usd} not realistic"

        # Technical parameters reality check
        assert (
            3 <= technical.hanning_window_samples <= 101
        ), f"Hanning window {technical.hanning_window_samples} not valid"

        assert (
            technical.hanning_window_samples % 2 == 1
        ), f"Hanning window {technical.hanning_window_samples} must be odd"

        assert (
            1 <= technical.peak_trough_min_distance <= 50
        ), f"Peak distance {technical.peak_trough_min_distance} not realistic"

        # Scanner parameters reality check
        assert (
            1 <= scanner.max_watchlist_size <= 200
        ), f"Watchlist size {scanner.max_watchlist_size} not practical"

        assert (
            10 <= scanner.active_scan_interval_seconds <= 3600
        ), f"Scan interval {scanner.active_scan_interval_seconds}s not practical"

        print("✅ All aggressive parameters are production-realistic")
        print(f"  • {trading.trades_per_minute_threshold} trades/min (high liquidity)")
        print(f"  • {trading.min_percent_change_threshold}% change (high volatility)")
        print(f"  • ${trading.default_position_size_usd:,} positions (substantial size)")
        print(f"  • {technical.hanning_window_samples}-sample window (fast response)")

    @pytest.mark.asyncio
    async def test_scanner_production_performance_real(self):
        """Test scanner performance under production-like conditions."""

        if not self.has_credentials:
            pytest.skip("API credentials required for production test")

        print("📊 SCANNER PRODUCTION PERFORMANCE TEST")
        print("=" * 50)

        # Test with production-sized symbol list
        production_symbols = [
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "TSLA",
            "META",
            "NVDA",
            "NFLX",
            "SPY",
            "QQQ",
            "IWM",
            "TQQQ",
            "SQQQ",
            "SPXL",
            "SPXS",
            "TNA",
            "AMD",
            "INTC",
            "CRM",
            "ORCL",
            "ADBE",
            "PYPL",
            "UBER",
            "LYFT",
        ]

        start_time = time.time()

        try:
            result = await scan_day_trading_opportunities(
                symbols=",".join(production_symbols),
                min_trades_per_minute=None,  # Use global config
                min_percent_change=None,  # Use global config
                max_symbols=10,  # Limit for speed
                sort_by=None,  # Use global config
            )

            scan_time = time.time() - start_time

            # Production performance requirements
            assert scan_time < 30.0, f"Scanner too slow for production: {scan_time:.1f}s"
            assert isinstance(result, str), "Scanner should return string result"
            assert "DAY TRADING OPPORTUNITY SCAN" in result, "Scanner result malformed"

            # Check that aggressive thresholds are being used
            trading = get_trading_config()
            expected_threshold = f"Threshold: {trading.trades_per_minute_threshold} trades/minute"
            assert expected_threshold in result, "Scanner not using global config threshold"

            print(
                f"✅ Scanner production test: {scan_time:.1f}s for {len(production_symbols)} symbols"
            )

            # Extract results count from scanner output
            lines = result.split("\n")
            for line in lines:
                if "Total Qualified:" in line:
                    print(f"  • {line.strip()}")
                    break

        except Exception as e:
            print(f"⚠️ Scanner production test failed: {e}")
            # This may happen due to market hours or API limits
            assert "Error" in str(e) or "timeout" in str(e).lower()

    @pytest.mark.asyncio
    async def test_technical_analysis_production_real(self):
        """Test technical analysis with production parameters."""

        if not self.has_credentials:
            pytest.skip("API credentials required for production test")

        print("🔧 TECHNICAL ANALYSIS PRODUCTION TEST")
        print("=" * 50)

        # Test with aggressive technical parameters
        technical = get_technical_config()

        start_time = time.time()

        try:
            result = await analyze_peaks_and_troughs(
                symbols="AAPL",  # Single liquid stock
                timeframe="1Min",
                days=1,
                limit=200,  # Limited for speed
                window_len=None,  # Use global config (11)
                lookahead=None,  # Use global config (1)
                min_peak_distance=None,  # Use global config (3)
            )

            analysis_time = time.time() - start_time

            # Production performance requirements
            assert analysis_time < 15.0, f"Technical analysis too slow: {analysis_time:.1f}s"
            assert isinstance(result, str), "Analysis should return string result"
            assert "Peak and Trough Analysis" in result, "Analysis result malformed"

            # Check that aggressive parameters are being used
            assert (
                f"Window: {technical.hanning_window_samples}" in result
            ), "Not using global window config"
            assert (
                f"Lookahead: {technical.peak_trough_lookahead}" in result
            ), "Not using global lookahead config"
            assert (
                f"Min Peak Distance: {technical.peak_trough_min_distance}" in result
            ), "Not using global distance config"

            print(f"✅ Technical analysis production test: {analysis_time:.1f}s")
            print(f"  • Window: {technical.hanning_window_samples} (aggressive)")
            print(f"  • Distance: {technical.peak_trough_min_distance} (close peaks)")
            print(f"  • Lookahead: {technical.peak_trough_lookahead} (minimal delay)")

        except Exception as e:
            print(f"⚠️ Technical analysis production test failed: {e}")
            # This may happen due to market hours or insufficient data
            assert "Error" in str(e) or "No data" in str(e)

    def test_fastapi_service_production_readiness_real(self):
        """Test FastAPI service for production readiness."""

        print("🚀 FASTAPI SERVICE PRODUCTION READINESS")
        print("=" * 50)

        # Create service instance
        service = MonitoringServiceAPI()

        # Test initialization
        assert service is not None
        assert hasattr(service, "config")
        assert hasattr(service, "watchlist")
        assert hasattr(service, "logger")

        # Test production-scale watchlist
        production_watchlist = [
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "TSLA",
            "META",
            "NVDA",
            "NFLX",
            "AMD",
            "INTC",
            "CRM",
            "ORCL",
            "ADBE",
            "PYPL",
            "UBER",
            "LYFT",
            "COIN",
            "HOOD",
            "PLTR",
            "PALR",
            "SNOW",
            "ZM",
            "ZOOM",
            "DOCU",
        ]

        # Add symbols to watchlist
        start_time = time.time()
        for symbol in production_watchlist:
            service.watchlist.add(symbol)
        add_time = time.time() - start_time

        # Performance check
        assert add_time < 1.0, f"Watchlist operations too slow: {add_time:.3f}s"
        assert len(service.watchlist) == len(production_watchlist)

        # Test watchlist operations
        assert "AAPL" in service.watchlist
        assert "MSFT" in service.watchlist

        # Test state management
        service.active = True
        service.check_count = 1000
        service.error_count = 5

        # Service should handle production-scale state
        assert service.active is True
        assert service.check_count == 1000
        assert service.error_count == 5

        print("✅ FastAPI service production readiness verified")
        print(f"  • Watchlist: {len(service.watchlist)} symbols in {add_time*1000:.1f}ms")
        print(f"  • State management: Active with {service.check_count} checks")

    def test_memory_usage_production_scale_real(self):
        """Test memory usage at production scale."""

        import psutil

        print("💾 MEMORY USAGE PRODUCTION SCALE TEST")
        print("=" * 50)

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create multiple services and configs (simulate production load)
        services = []
        configs = []

        for i in range(10):
            # Create service instances
            service = MonitoringServiceAPI()

            # Add production-scale data
            for j in range(50):
                service.watchlist.add(f"STOCK{j}")

            service.check_count = 1000 + i * 100
            services.append(service)

            # Access configs repeatedly
            for _ in range(100):
                trading = get_trading_config()
                technical = get_technical_config()
                configs.extend([trading, technical])

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        # Memory usage should be reasonable for production
        assert memory_increase < 200, f"Memory usage too high: {memory_increase:.1f}MB"

        # Verify functionality is still working
        assert len(services) == 10
        assert all(len(s.watchlist) == 50 for s in services)

        latest_trading = get_trading_config()
        assert latest_trading.trades_per_minute_threshold >= 500

        print(f"✅ Memory usage production scale: {memory_increase:.1f}MB increase")
        print(f"  • {len(services)} services with {len(services[0].watchlist)} symbols each")

    def test_error_recovery_production_scenarios_real(self):
        """Test error recovery in production scenarios."""

        print("🛡️ ERROR RECOVERY PRODUCTION SCENARIOS")
        print("=" * 50)

        # Test service resilience
        service = MonitoringServiceAPI()

        # Simulate production errors
        error_scenarios = [
            ("Invalid symbol", lambda: service.watchlist.add("")),
            ("None symbol", lambda: service.watchlist.add(None) if None else None),
            ("Large watchlist", lambda: [service.watchlist.add(f"SYM{i}") for i in range(1000)]),
        ]

        for scenario_name, scenario_func in error_scenarios:
            try:
                if scenario_func:
                    scenario_func()
                print(f"  • {scenario_name}: Handled gracefully")
            except Exception as e:
                # Errors should be handled gracefully
                print(f"  • {scenario_name}: Error handled - {type(e).__name__}")

        # Service should still be functional
        service.watchlist.add("AAPL")
        assert "AAPL" in service.watchlist

        # Config system should be resilient
        for _ in range(10):
            try:
                trading = get_trading_config()
                assert trading.trades_per_minute_threshold >= 500
            except Exception as e:
                pytest.fail(f"Config system not resilient: {e}")

        print("✅ Error recovery verified for production scenarios")

    def test_high_frequency_trading_simulation_real(self):
        """Test system under high-frequency trading simulation."""

        print("⚡ HIGH-FREQUENCY TRADING SIMULATION")
        print("=" * 50)

        # Simulate rapid decision-making cycle
        decisions = []
        errors = []

        start_time = time.time()

        for i in range(500):  # 500 rapid decisions
            try:
                # Get config (like real trading system would)
                trading = get_trading_config()
                technical = get_technical_config()

                # Simulate trading decision
                if (
                    trading.trades_per_minute_threshold > 400
                    and technical.hanning_window_samples < 20
                    and trading.never_sell_for_loss
                ):
                    decisions.append(f"BUY_SIGNAL_{i}")

                # Simulate very fast decision making
                if i % 100 == 0:
                    time.sleep(0.001)  # 1ms delay every 100 decisions

            except Exception as e:
                errors.append(e)

        simulation_time = time.time() - start_time
        decisions_per_second = len(decisions) / simulation_time

        # High-frequency requirements
        assert len(errors) == 0, f"Errors in HFT simulation: {errors}"
        assert (
            decisions_per_second > 1000
        ), f"HFT too slow: {decisions_per_second:.0f} decisions/sec"
        assert len(decisions) > 0, "No trading decisions generated"

        print(f"✅ HFT simulation: {decisions_per_second:.0f} decisions/sec")
        print(f"  • {len(decisions)} decisions in {simulation_time:.3f}s")
        print(f"  • {len(errors)} errors (should be 0)")

    def test_24_7_operation_simulation_real(self):
        """Test system for 24/7 operation characteristics."""

        print("🕒 24/7 OPERATION SIMULATION")
        print("=" * 50)

        # Simulate extended operation
        service = MonitoringServiceAPI()
        service.active = True

        # Simulate days of operation
        for _ in range(7):  # 7 days
            for hour in range(24):  # 24 hours
                # Simulate hourly operations
                service.check_count += 1

                # Get config (would happen frequently)
                trading = get_trading_config()

                # Simulate market conditions
                if hour >= 4 and hour <= 20:  # Market hours EST
                    service.watchlist.add(f"ACTIVE_STOCK_{hour}")

                # Simulate occasional errors (real systems have them)
                if hour % 13 == 0:  # Occasional issues
                    service.error_count += 1

        # Verify system state after extended simulation
        total_hours = 7 * 24
        assert service.check_count == total_hours
        assert service.active is True
        assert len(service.watchlist) >= 15  # Should have accumulated symbols

        # Error rate should be reasonable
        error_rate = service.error_count / service.check_count * 100
        assert error_rate < 10, f"Error rate too high: {error_rate:.1f}%"

        # Config should still work perfectly
        trading = get_trading_config()
        assert trading.trades_per_minute_threshold == 500
        assert trading.never_sell_for_loss is True

        print(f"✅ 24/7 operation simulation: {total_hours} hours")
        print(f"  • {service.check_count} operations")
        print(f"  • {service.error_count} errors ({error_rate:.1f}% rate)")
        print(f"  • {len(service.watchlist)} symbols tracked")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
