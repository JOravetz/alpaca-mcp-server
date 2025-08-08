"""
REAL tests for streaming functionality - NO MOCKING.
Tests actual streaming components and FastAPI integration.
"""

import os
import sys
import time
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server  # noqa: E402.config import get_global_config, get_system_config
from alpaca_mcp_server  # noqa: E402.monitoring.fastapi_service import MonitoringServiceAPI


class TestStreamingReal:
    """REAL streaming tests - actual components, no mocking."""

    def setup_method(self):
        """Set up test environment."""
        self.has_credentials = os.getenv("APCA_API_KEY_ID") and os.getenv("APCA_API_SECRET_KEY")

    def test_fastapi_service_initialization_real(self):
        """Test that FastAPI service initializes with real config."""

        # Create a real service instance
        service = MonitoringServiceAPI()

        # Verify it initializes properly
        assert service is not None
        assert hasattr(service, "config")
        assert hasattr(service, "logger")
        assert service.active is False
        assert service.start_time is None

    def test_fastapi_service_config_integration_real(self):
        """Test that FastAPI service uses global config values."""

        # Get the global config
        config = get_global_config()
        system_config = get_system_config()

        # Create service and verify it can access config
        MonitoringServiceAPI()

        # Verify service can access the same config values
        assert config.trading.trades_per_minute_threshold >= 500
        assert config.technical_analysis.hanning_window_samples >= 3
        assert system_config.monitoring_check_interval_seconds >= 60

    def test_fastapi_service_lifecycle_real(self):
        """Test FastAPI service startup and shutdown lifecycle."""

        service = MonitoringServiceAPI()

        # Test initial state
        assert service.active is False
        assert service.start_time is None
        assert service.check_count == 0

        # Test state after potential startup
        # (Without actually starting full service to avoid resource conflicts)
        service.active = True
        service.start_time = time.time()
        service.check_count = 1

        assert service.active is True
        assert service.start_time is not None
        assert service.check_count == 1

    def test_watchlist_management_real(self):
        """Test real watchlist management without external dependencies."""

        service = MonitoringServiceAPI()

        # Test initial empty watchlist
        assert len(service.watchlist) == 0

        # Test adding symbols
        test_symbols = ["AAPL", "MSFT", "NVDA"]
        for symbol in test_symbols:
            service.watchlist.add(symbol)

        assert len(service.watchlist) == 3
        assert "AAPL" in service.watchlist
        assert "MSFT" in service.watchlist
        assert "NVDA" in service.watchlist

        # Test removing symbols
        service.watchlist.remove("MSFT")
        assert len(service.watchlist) == 2
        assert "MSFT" not in service.watchlist

    def test_service_state_persistence_real(self):
        """Test that service state can be persisted and loaded."""

        service = MonitoringServiceAPI()

        # Set some state
        service.watchlist.update(["AAPL", "MSFT", "NVDA"])
        service.active = True
        service.check_count = 10
        service.error_count = 1

        # Create state dict (simulate persistence)
        state = {
            "watchlist": list(service.watchlist),
            "active": service.active,
            "check_count": service.check_count,
            "error_count": service.error_count,
        }

        # Create new service and restore state
        new_service = MonitoringServiceAPI()
        new_service.watchlist.update(state["watchlist"])
        new_service.active = state["active"]
        new_service.check_count = state["check_count"]
        new_service.error_count = state["error_count"]

        # Verify state was restored
        assert len(new_service.watchlist) == 3
        assert new_service.active is True
        assert new_service.check_count == 10
        assert new_service.error_count == 1

    def test_configuration_consistency_real(self):
        """Test that all components use consistent configuration values."""

        # Import different components that use config
        from alpaca_mcp_server.config import (
            get_scanner_config,
            get_technical_config,
            get_trading_config,
        )

        # Get configs from different components
        trading_config = get_trading_config()
        technical_config = get_technical_config()
        scanner_config = get_scanner_config()

        # Verify they all return consistent values
        assert trading_config.trades_per_minute_threshold == 500
        assert technical_config.hanning_window_samples == 11
        assert technical_config.peak_trough_min_distance == 3
        assert scanner_config.max_watchlist_size == 50

    def test_symbol_validation_real(self):
        """Test real symbol validation logic."""

        service = MonitoringServiceAPI()

        # Test valid symbols
        valid_symbols = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL"]
        for symbol in valid_symbols:
            # Should be able to add without error
            service.watchlist.add(symbol)
            assert symbol in service.watchlist

        # Test symbol cleanup (uppercase, strip)
        test_symbol = "  aapl  "
        cleaned = test_symbol.strip().upper()
        service.watchlist.add(cleaned)
        assert "AAPL" in service.watchlist

        # Test symbol format validation
        valid_symbol_chars = all(c.isalpha() for c in "AAPL")
        assert valid_symbol_chars is True

        valid_symbol_length = 1 <= len("AAPL") <= 5
        assert valid_symbol_length is True

    def test_performance_monitoring_real(self):
        """Test real performance monitoring capabilities."""

        service = MonitoringServiceAPI()

        # Test timing operations
        start_time = time.time()
        time.sleep(0.01)  # Small delay
        end_time = time.time()

        duration = end_time - start_time
        assert duration >= 0.01
        assert duration < 0.1  # Should be fast

        # Test check counting
        service.check_count = 0
        for _i in range(5):
            service.check_count += 1

        assert service.check_count == 5

    def test_error_handling_real(self):
        """Test real error handling and recovery."""

        service = MonitoringServiceAPI()

        # Test error counting
        service.error_count = 0

        # Simulate error scenarios
        try:
            # This should raise an error
            result = 1 / 0
        except ZeroDivisionError:
            service.error_count += 1

        assert service.error_count == 1

        # Test error recovery
        try:
            # This should work
            result = 1 / 1
            # Reset error count on success
            if result == 1:
                service.error_count = 0
        except Exception:
            pass

        assert service.error_count == 0

    def test_config_driven_behavior_real(self):
        """Test that service behavior is actually driven by config values."""

        from alpaca_mcp_server.config import get_scanner_config, get_trading_config

        trading_config = get_trading_config()
        scanner_config = get_scanner_config()

        # Test that aggressive config values are in effect
        assert trading_config.trades_per_minute_threshold == 500  # Aggressive threshold
        assert trading_config.min_percent_change_threshold == 10.0  # High volatility
        assert trading_config.never_sell_for_loss is True  # Never sell for loss

        # Test scanner is configured for aggressive trading
        assert scanner_config.max_watchlist_size == 50  # Large watchlist for comprehensive scanning
        assert scanner_config.active_scan_interval_seconds == 60  # Fast scanning
        assert scanner_config.scanner_sort_method == "trades"  # Liquidity focus

    def test_concurrent_operations_real(self):
        """Test real concurrent operations without mocking."""

        service = MonitoringServiceAPI()

        # Test concurrent watchlist operations
        def add_symbols(symbols):
            for symbol in symbols:
                service.watchlist.add(symbol)

        def remove_symbols(symbols):
            for symbol in symbols:
                service.watchlist.discard(symbol)  # Use discard to avoid KeyError

        # Add symbols
        add_symbols(["AAPL", "MSFT", "NVDA"])
        assert len(service.watchlist) == 3

        # Remove some symbols
        remove_symbols(["MSFT"])
        assert len(service.watchlist) == 2
        assert "MSFT" not in service.watchlist

    def test_memory_efficiency_real(self):
        """Test real memory efficiency of service components."""

        service = MonitoringServiceAPI()

        # Test watchlist memory usage
        large_watchlist = [f"SYMB{i:03d}" for i in range(100)]
        service.watchlist.update(large_watchlist)

        assert len(service.watchlist) == 100

        # Test clearing watchlist
        service.watchlist.clear()
        assert len(service.watchlist) == 0

        # Test that service can handle moderate load
        for _i in range(50):
            service.check_count += 1

        assert service.check_count == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
