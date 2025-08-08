"""Tests for ConfigurableStockDataBuffer timestamp parsing."""

import time
from datetime import UTC, datetime

from alpaca_mcp_server.config.settings import ConfigurableStockDataBuffer


class TestBufferTimestampParsing:
    """Test timestamp parsing in ConfigurableStockDataBuffer."""

    def setup_method(self):
        """Set up test buffer."""
        self.buffer = ConfigurableStockDataBuffer()

    def test_iso_timestamp_parsing(self):
        """Test parsing of ISO format timestamps."""
        now = datetime.now()
        item = {"symbol": "TEST", "price": 100.0, "timestamp": now.isoformat()}

        self.buffer.add(item)
        recent_data = self.buffer.get_recent(10)

        assert len(recent_data) == 1
        assert recent_data[0]["symbol"] == "TEST"

    def test_numeric_timestamp_parsing(self):
        """Test parsing of numeric timestamps."""
        item = {"symbol": "TEST", "price": 100.0, "timestamp": time.time()}

        self.buffer.add(item)
        recent_data = self.buffer.get_recent(10)

        assert len(recent_data) == 1
        assert recent_data[0]["symbol"] == "TEST"

    def test_string_numeric_timestamp_parsing(self):
        """Test parsing of string numeric timestamps."""
        item = {"symbol": "TEST", "price": 100.0, "timestamp": str(time.time())}

        self.buffer.add(item)
        recent_data = self.buffer.get_recent(10)

        assert len(recent_data) == 1
        assert recent_data[0]["symbol"] == "TEST"

    def test_mixed_timestamp_formats(self):
        """Test buffer with mixed timestamp formats."""
        now = datetime.now()
        current_time = time.time()

        items = [
            {"symbol": "TEST1", "price": 100.0, "timestamp": now.isoformat()},
            {"symbol": "TEST2", "price": 101.0, "timestamp": current_time},
            {"symbol": "TEST3", "price": 102.0, "timestamp": str(current_time)},
        ]

        for item in items:
            self.buffer.add(item)

        recent_data = self.buffer.get_recent(10)
        assert len(recent_data) == 3

    def test_old_data_filtering(self):
        """Test that old data is properly filtered out."""
        old_time = time.time() - 3600  # 1 hour ago
        recent_time = time.time()

        items = [
            {"symbol": "OLD", "price": 100.0, "timestamp": old_time},
            {"symbol": "NEW", "price": 101.0, "timestamp": recent_time},
        ]

        for item in items:
            self.buffer.add(item)

        recent_data = self.buffer.get_recent(10)
        assert len(recent_data) == 1
        assert recent_data[0]["symbol"] == "NEW"

    def test_invalid_timestamp_handling(self):
        """Test handling of invalid timestamps."""
        items = [
            {"symbol": "VALID", "price": 100.0, "timestamp": time.time()},
            {"symbol": "INVALID", "price": 101.0, "timestamp": "invalid-time"},
            {"symbol": "MISSING", "price": 102.0},  # No timestamp
        ]

        for item in items:
            self.buffer.add(item)

        # Should only return the valid item
        recent_data = self.buffer.get_recent(10)
        assert len(recent_data) == 1
        assert recent_data[0]["symbol"] == "VALID"

    def test_timezone_aware_iso_timestamps(self):
        """Test handling of timezone-aware ISO timestamps."""
        now_utc = datetime.now(UTC)
        item = {"symbol": "TZ_TEST", "price": 100.0, "timestamp": now_utc.isoformat()}

        self.buffer.add(item)
        recent_data = self.buffer.get_recent(10)

        assert len(recent_data) == 1
        assert recent_data[0]["symbol"] == "TZ_TEST"

    def test_get_all_returns_all_data(self):
        """Test that get_all returns all data regardless of timestamp."""
        old_time = time.time() - 3600  # 1 hour ago
        recent_time = time.time()

        items = [
            {"symbol": "OLD", "price": 100.0, "timestamp": old_time},
            {"symbol": "NEW", "price": 101.0, "timestamp": recent_time},
        ]

        for item in items:
            self.buffer.add(item)

        all_data = self.buffer.get_all()
        assert len(all_data) == 2

        recent_data = self.buffer.get_recent(10)
        assert len(recent_data) == 1  # Only recent data
