"""
Simple REAL tests for the global configuration system.
NO MOCKING - Tests actual configuration loading and usage.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server.config import (
    get_global_config,
    get_scanner_config,
    get_technical_config,
    get_trading_config,
)


class TestGlobalConfigSimple:
    """Simple REAL tests for global configuration - no mocking."""

    def test_config_loading_real(self):
        """Test that global config can be loaded and accessed."""

        # Get the configs
        global_config = get_global_config()
        trading_config = get_trading_config()
        technical_config = get_technical_config()
        scanner_config = get_scanner_config()

        # Verify they load without error
        assert global_config is not None
        assert trading_config is not None
        assert technical_config is not None
        assert scanner_config is not None

    def test_aggressive_trading_parameters_real(self):
        """Test that aggressive trading parameters are correctly set."""

        trading = get_trading_config()
        technical = get_technical_config()
        scanner = get_scanner_config()

        # Verify aggressive trading settings
        assert trading.trades_per_minute_threshold == 1000  # High liquidity requirement
        assert trading.min_percent_change_threshold == 10.0  # High volatility requirement
        assert trading.never_sell_for_loss is True  # Never sell for loss rule

        # Verify aggressive technical analysis settings
        assert technical.hanning_window_samples == 11  # Lower smoothing for faster response
        assert technical.peak_trough_min_distance == 3  # Closer peaks allowed
        assert technical.peak_trough_lookahead == 1  # Minimal lookahead for speed

        # Verify aggressive scanner settings
        assert scanner.max_watchlist_size == 50  # Large watchlist for comprehensive scanning
        assert scanner.scanner_sort_method == "trades"  # Liquidity focus

    def test_config_values_are_reasonable_real(self):
        """Test that config values are within reasonable ranges."""

        trading = get_trading_config()
        technical = get_technical_config()

        # Trading parameters should be aggressive but reasonable
        assert 100 <= trading.trades_per_minute_threshold <= 1000
        assert 1.0 <= trading.min_percent_change_threshold <= 50.0
        assert 10000 <= trading.default_position_size_usd <= 100000

        # Technical parameters should be valid
        assert 3 <= technical.hanning_window_samples <= 101
        assert technical.hanning_window_samples % 2 == 1  # Must be odd
        assert 1 <= technical.peak_trough_min_distance <= 20
        assert 1 <= technical.peak_trough_lookahead <= 10

    def test_config_consistency_real(self):
        """Test that config values are consistent across calls."""

        # Get configs multiple times
        trading1 = get_trading_config()
        trading2 = get_trading_config()

        technical1 = get_technical_config()
        technical2 = get_technical_config()

        # Should return the same values
        assert trading1.trades_per_minute_threshold == trading2.trades_per_minute_threshold
        assert trading1.min_percent_change_threshold == trading2.min_percent_change_threshold

        assert technical1.hanning_window_samples == technical2.hanning_window_samples
        assert technical1.peak_trough_min_distance == technical2.peak_trough_min_distance

    def test_config_file_creation_real(self):
        """Test creating and loading a real config file."""

        # Create test config
        test_config = {
            "trading": {
                "trades_per_minute_threshold": 750,
                "min_percent_change_threshold": 15.0,
                "never_sell_for_loss": True,
            },
            "technical_analysis": {
                "hanning_window_samples": 13,
                "peak_trough_min_distance": 5,
                "peak_trough_lookahead": 2,
            },
        }

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_config, f, indent=2)
            temp_file = f.name

        try:
            # Verify file was created and contains expected data
            assert os.path.exists(temp_file)

            with open(temp_file) as f:
                loaded_data = json.load(f)

            assert loaded_data["trading"]["trades_per_minute_threshold"] == 750
            assert loaded_data["technical_analysis"]["hanning_window_samples"] == 13

        finally:
            os.unlink(temp_file)

    def test_production_config_file_real(self):
        """Test the production config file if it exists."""

        # Check if production config exists
        config_path = project_root / "config" / "global_config.json"

        if config_path.exists():
            # Load and verify it's valid JSON
            with open(config_path) as f:
                config_data = json.load(f)

            # Should have expected sections
            assert "trading" in config_data
            assert "technical_analysis" in config_data

            # Should have aggressive values
            trading = config_data["trading"]
            assert trading["trades_per_minute_threshold"] == 500
            assert trading["min_percent_change_threshold"] == 10.0

        else:
            # If no production config, that's OK - defaults are used
            pass

    def test_config_field_access_real(self):
        """Test that all expected config fields can be accessed."""

        trading = get_trading_config()
        technical = get_technical_config()

        # Test trading config fields
        assert hasattr(trading, "trades_per_minute_threshold")
        assert hasattr(trading, "min_percent_change_threshold")
        assert hasattr(trading, "default_position_size_usd")
        assert hasattr(trading, "never_sell_for_loss")

        # Test technical config fields
        assert hasattr(technical, "hanning_window_samples")
        assert hasattr(technical, "peak_trough_min_distance")
        assert hasattr(technical, "peak_trough_lookahead")

        # Verify they have valid values
        assert isinstance(trading.trades_per_minute_threshold, int)
        assert isinstance(trading.min_percent_change_threshold, float)
        assert isinstance(trading.never_sell_for_loss, bool)

        assert isinstance(technical.hanning_window_samples, int)
        assert isinstance(technical.peak_trough_min_distance, int)
        assert isinstance(technical.peak_trough_lookahead, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
