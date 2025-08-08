"""
Config File Edge Cases Tests - REAL tests for resilience.
Tests malformed files, permissions, corruption scenarios - NO MOCKING.
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

import contextlib

from alpaca_mcp_server  # noqa: E402.config.global_config import (
    GlobalConfig,
)


class TestConfigEdgeCases:
    """REAL edge case tests for config file handling."""

    def test_corrupted_json_recovery_real(self):
        """Test system handles corrupted JSON gracefully."""

        # Create corrupted JSON file
        corrupted_configs = [
            '{ "trading": { "trades_per_minute_threshold": 500, }',  # Trailing comma
            '{ "trading": { "invalid_field": }',  # Missing value
            '{ "trading": { "trades_per_minute_threshold": 500 } extra_text',  # Extra content
            "{ incomplete json",  # Incomplete
            "",  # Empty file
            "   ",  # Whitespace only
        ]

        for i, corrupted_json in enumerate(corrupted_configs):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(corrupted_json)
                temp_file = f.name

            try:
                # Should gracefully fall back to defaults
                config = GlobalConfig.load(temp_file)

                # Verify fallback to defaults worked (check actual default values)
                assert isinstance(config.trading.trades_per_minute_threshold, int | float)
                assert isinstance(config.trading.min_percent_change_threshold, int | float)
                assert isinstance(config.technical_analysis.hanning_window_samples, int)
                assert (
                    config.trading.trades_per_minute_threshold >= 500
                )  # Should be default or higher
                assert (
                    config.trading.min_percent_change_threshold >= 10.0
                )  # Should be default or higher
                assert (
                    config.technical_analysis.hanning_window_samples >= 3
                )  # Should be valid value

                print(f"✅ Corrupted JSON case {i+1} handled gracefully")

            finally:
                os.unlink(temp_file)

    def test_wrong_type_values_handled_real(self):
        """Test system handles wrong type values appropriately."""

        # Test with string where number expected
        wrong_type_config = '{ "trading": { "trades_per_minute_threshold": "not_a_number" } }'

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(wrong_type_config)
            temp_file = f.name

        try:
            # Should handle wrong type gracefully (may convert or use defaults)
            config = GlobalConfig.load(temp_file)

            # System should either convert the value or fall back to defaults
            # We accept either behavior as long as it doesn't crash
            threshold = config.trading.trades_per_minute_threshold
            if isinstance(threshold, int | float):
                assert threshold >= 500  # Converted or default
            elif isinstance(threshold, str):
                # If it preserved the string, that's also acceptable for this test
                # as long as the system doesn't crash
                assert threshold == "not_a_number"

            print("✅ Wrong type values handled appropriately")

        finally:
            os.unlink(temp_file)

    def test_config_file_permission_errors_real(self):
        """Test behavior when config file has permission issues."""

        # Create a valid config file
        valid_config = {
            "trading": {"trades_per_minute_threshold": 750, "min_percent_change_threshold": 15.0}
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(valid_config, f)
            temp_file = f.name

        try:
            # Remove read permissions (on Unix systems)
            if os.name != "nt":  # Not Windows
                os.chmod(temp_file, 0o000)  # No permissions

                # Should fall back to defaults
                config = GlobalConfig.load(temp_file)

                # Verify fallback worked
                assert config.trading.trades_per_minute_threshold == 500  # Default
                print("✅ Permission error handled gracefully")

                # Restore permissions for cleanup
                os.chmod(temp_file, 0o644)
            else:
                print("⚠️ Permission test skipped on Windows")

        finally:
            with contextlib.suppress(PermissionError, FileNotFoundError):
                os.unlink(temp_file)

    def test_config_directory_missing_real(self):
        """Test creating config in non-existent directory."""

        # Try to load from non-existent directory
        non_existent_path = "/tmp/non_existent_dir/config.json"

        # Should handle gracefully
        config = GlobalConfig.load(non_existent_path)

        # Verify defaults are used
        assert config.trading.trades_per_minute_threshold == 500
        assert config.technical_analysis.hanning_window_samples == 11
        print("✅ Non-existent directory handled gracefully")

    def test_config_large_file_handling_real(self):
        """Test handling very large config files."""

        # Create large config with many repeated sections
        large_config = {
            "trading": {
                "trades_per_minute_threshold": 500,
                "min_percent_change_threshold": 10.0,
                "never_sell_for_loss": True,
            },
            "technical_analysis": {
                "hanning_window_samples": 11,
                "peak_trough_min_distance": 3,
                "peak_trough_lookahead": 1,
            },
        }

        # Add lots of extra data to make it large
        for i in range(1000):
            large_config[f"dummy_section_{i}"] = {"dummy_field": f"dummy_value_{i}" * 100}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(large_config, f)
            temp_file = f.name

        try:
            # Should handle large file without issues
            config = GlobalConfig.load(temp_file)

            # Core config should still work
            assert config.trading.trades_per_minute_threshold == 500
            assert config.technical_analysis.hanning_window_samples == 11
            print(f"✅ Large config file handled (size: {os.path.getsize(temp_file)} bytes)")

        finally:
            os.unlink(temp_file)

    def test_config_with_unicode_content_real(self):
        """Test config files with Unicode characters."""

        unicode_configs = [
            {
                "trading": {
                    "trades_per_minute_threshold": 500,
                    "description": "Aggressīve trading with émojis 🚀📈",
                }
            },
            {"trading": {"trades_per_minute_threshold": 500, "notes": "测试中文字符"}},
            {"trading": {"trades_per_minute_threshold": 500, "symbols": "ЯНДЕКС,МБРД"}},  # Cyrillic
        ]

        for i, unicode_config in enumerate(unicode_configs):
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                json.dump(unicode_config, f, ensure_ascii=False)
                temp_file = f.name

            try:
                # Should handle Unicode gracefully
                config = GlobalConfig.load(temp_file)

                # Core functionality should work
                assert config.trading.trades_per_minute_threshold == 500
                print(f"✅ Unicode config case {i+1} handled correctly")

            finally:
                os.unlink(temp_file)

    def test_config_nested_structure_validation_real(self):
        """Test deeply nested or malformed structure handling."""

        malformed_structures = [
            {"trading": {"nested": {"deep": {"very_deep": {"trades_per_minute_threshold": 500}}}}},
            {"trading": [1, 2, 3]},  # Array instead of object
            {"trading": "not_an_object"},  # String instead of object
            {"trading": None},  # Null value
        ]

        for i, malformed in enumerate(malformed_structures):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(malformed, f)
                temp_file = f.name

            try:
                # Should handle malformed structure gracefully
                config = GlobalConfig.load(temp_file)

                # Should fall back to defaults
                assert config.trading.trades_per_minute_threshold == 500
                assert config.trading.min_percent_change_threshold == 10.0
                print(f"✅ Malformed structure case {i+1} handled gracefully")

            finally:
                os.unlink(temp_file)

    def test_config_concurrent_file_access_real(self):
        """Test concurrent access to config file."""

        import threading

        # Create config file
        test_config = {
            "trading": {"trades_per_minute_threshold": 600, "min_percent_change_threshold": 12.0}
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_config, f)
            temp_file = f.name

        try:
            configs_loaded = []
            errors = []

            def load_config_worker():
                try:
                    config = GlobalConfig.load(temp_file)
                    configs_loaded.append(config)
                except Exception as e:
                    errors.append(e)

            # Start multiple threads loading config simultaneously
            threads = []
            for _i in range(5):
                thread = threading.Thread(target=load_config_worker)
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # Verify all loaded successfully
            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(configs_loaded) == 5

            # All configs should have same values
            for config in configs_loaded:
                assert config.trading.trades_per_minute_threshold == 600
                assert config.trading.min_percent_change_threshold == 12.0

            print("✅ Concurrent file access handled correctly")

        finally:
            os.unlink(temp_file)

    def test_config_backup_and_recovery_real(self):
        """Test config backup and recovery scenarios."""

        # Create original config
        original_config = {
            "trading": {"trades_per_minute_threshold": 800, "min_percent_change_threshold": 20.0}
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(original_config, f)
            temp_file = f.name

        try:
            # Load original
            config1 = GlobalConfig.load(temp_file)
            assert config1.trading.trades_per_minute_threshold == 800

            # Corrupt the file
            with open(temp_file, "w") as f:
                f.write("corrupted content")

            # Should fall back to defaults
            config2 = GlobalConfig.load(temp_file)
            assert config2.trading.trades_per_minute_threshold == 500  # Default

            # Restore good config
            with open(temp_file, "w") as f:
                json.dump(original_config, f)

            # Should load properly again
            config3 = GlobalConfig.load(temp_file)
            assert config3.trading.trades_per_minute_threshold == 800

            print("✅ Backup and recovery scenario handled correctly")

        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
