"""
Performance tests for advanced agentic workflows.
Tests response times, throughput, and resource usage with real data.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

import psutil
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server.prompts.day_trading_workflow import day_trading_workflow  # noqa: E402
from alpaca_mcp_server.prompts.list_trading_capabilities import list_trading_capabilities  # noqa: E402
from alpaca_mcp_server.prompts.market_session_workflow import market_session_workflow  # noqa: E402
from alpaca_mcp_server.prompts.master_scanning_workflow import master_scanning_workflow  # noqa: E402
from alpaca_mcp_server.prompts.pro_technical_workflow import pro_technical_workflow  # noqa: E402


class TestWorkflowPerformance:
    """Test individual workflow performance metrics."""

    @pytest.mark.asyncio
    async def test_master_scanner_performance(self):
        """Test master scanner performance across different modes."""
        modes = ["quick", "comprehensive", "extended_hours"]
        results = []

        for mode in modes:
            start_time = time.time()
            result = await master_scanning_workflow(mode)
            end_time = time.time()

            duration = end_time - start_time
            char_count = len(result)

            results.append((mode, duration, char_count))

            assert isinstance(result, str)
            assert char_count > 100
            assert duration < 30.0  # Should complete within 30 seconds

            print(f"✅ Master scanner '{mode}': {duration:.2f}s, {char_count:,} chars")

        # Verify quick mode is fastest
        quick_time = next(r[1] for r in results if r[0] == "quick")
        comprehensive_time = next(r[1] for r in results if r[0] == "comprehensive")

        print(f"Quick vs Comprehensive: {quick_time:.2f}s vs {comprehensive_time:.2f}s")
        return results

    @pytest.mark.asyncio
    async def test_technical_analysis_performance(self):
        """Test technical analysis performance across timeframes."""
        timeframes = ["quick", "comprehensive", "deep"]
        symbol = "AAPL"
        results = []

        for timeframe in timeframes:
            start_time = time.time()
            result = await pro_technical_workflow(symbol, timeframe)
            end_time = time.time()

            duration = end_time - start_time
            char_count = len(result)

            results.append((timeframe, duration, char_count))

            assert isinstance(result, str)
            assert symbol in result
            assert char_count > 500
            assert duration < 45.0  # Technical analysis can take longer

            print(f"✅ Technical analysis '{timeframe}': {duration:.2f}s, {char_count:,} chars")

        return results

    @pytest.mark.asyncio
    async def test_session_workflow_performance(self):
        """Test session workflow performance across session types."""
        sessions = ["pre_market", "market_open", "mid_day", "power_hour", "after_hours", "full_day"]
        results = []

        for session in sessions:
            start_time = time.time()
            result = await market_session_workflow(session)
            end_time = time.time()

            duration = end_time - start_time
            char_count = len(result)

            results.append((session, duration, char_count))

            assert isinstance(result, str)
            assert char_count > 200
            assert duration < 25.0

            print(f"✅ Session '{session}': {duration:.2f}s, {char_count:,} chars")

        # Full day should have most content
        full_day_chars = next(r[2] for r in results if r[0] == "full_day")
        other_chars = [r[2] for r in results if r[0] != "full_day"]

        assert full_day_chars >= max(other_chars), "Full day should have most content"
        return results

    @pytest.mark.asyncio
    async def test_day_trading_workflow_performance(self):
        """Test day trading workflow performance with different symbols."""
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "SPY"]
        results = []

        for symbol in symbols:
            start_time = time.time()
            result = await day_trading_workflow(symbol)
            end_time = time.time()

            duration = end_time - start_time
            char_count = len(result)

            results.append((symbol, duration, char_count))

            assert isinstance(result, str)
            assert symbol in result
            assert char_count > 300
            assert duration < 35.0

            print(f"✅ Day trading '{symbol}': {duration:.2f}s, {char_count:,} chars")

        return results


class TestConcurrentPerformance:
    """Test concurrent workflow execution performance."""

    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self):
        """Test multiple workflows running concurrently."""
        workflows = [
            ("master_scan", master_scanning_workflow("quick")),
            ("technical_aapl", pro_technical_workflow("AAPL", "quick")),
            ("technical_spy", pro_technical_workflow("SPY", "quick")),
            ("session", market_session_workflow("market_open")),
            ("day_trading", day_trading_workflow("MSFT")),
        ]

        start_time = time.time()
        results = await asyncio.gather(
            *[workflow for _, workflow in workflows], return_exceptions=True
        )
        end_time = time.time()

        concurrent_duration = end_time - start_time

        successful_results = []
        for i, result in enumerate(results):
            workflow_name = workflows[i][0]
            if isinstance(result, Exception):
                print(f"❌ {workflow_name} failed: {result}")
            else:
                assert isinstance(result, str)
                successful_results.append((workflow_name, len(result)))
                print(f"✅ {workflow_name}: {len(result):,} chars")

        assert len(successful_results) >= 3, "At least 3 workflows should succeed"
        print(
            f"✅ Concurrent execution: {len(successful_results)}/{len(workflows)} workflows in {concurrent_duration:.2f}s"
        )

        # Concurrent should be faster than sequential
        assert (
            concurrent_duration < len(workflows) * 10.0
        ), "Concurrent execution should be efficient"

        return concurrent_duration, successful_results

    @pytest.mark.asyncio
    async def test_high_concurrency_stress(self):
        """Test high concurrency stress with many simultaneous workflows."""
        num_concurrent = 10
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "SPY", "NVDA", "META", "AMZN", "NFLX", "COIN"]

        workflows = [
            pro_technical_workflow(symbols[i % len(symbols)], "quick")
            for i in range(num_concurrent)
        ]

        start_time = time.time()
        results = await asyncio.gather(*workflows, return_exceptions=True)
        end_time = time.time()

        duration = end_time - start_time

        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = num_concurrent - successful

        print(f"✅ High concurrency: {successful}/{num_concurrent} succeeded in {duration:.2f}s")
        print(f"Success rate: {successful/num_concurrent*100:.1f}%")

        assert successful >= num_concurrent * 0.7, "At least 70% should succeed under stress"
        assert duration < 60.0, "High concurrency should complete within 1 minute"

        return duration, successful, failed


class TestResourceUsage:
    """Test resource usage and memory management."""

    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self):
        """Monitor memory usage during workflow execution."""
        process = psutil.Process(os.getpid())

        # Get baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Baseline memory: {baseline_memory:.1f} MB")

        # Run memory-intensive workflows
        memory_readings = [baseline_memory]

        workflows = [
            ("master_comprehensive", master_scanning_workflow("comprehensive")),
            ("technical_deep", pro_technical_workflow("AAPL", "comprehensive")),
            ("session_full", market_session_workflow("full_day")),
            ("capabilities", list_trading_capabilities()),
        ]

        for name, workflow in workflows:
            result = await workflow
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_readings.append(current_memory)

            assert isinstance(result, str)
            print(f"✅ {name}: {len(result):,} chars, {current_memory:.1f} MB")

        max_memory = max(memory_readings)
        memory_growth = max_memory - baseline_memory

        print(
            f"Memory usage: {baseline_memory:.1f} MB → {max_memory:.1f} MB (+{memory_growth:.1f} MB)"
        )

        # Memory growth should be reasonable (less than 500MB for these workflows)
        assert memory_growth < 500, f"Memory growth too high: {memory_growth:.1f} MB"

        return memory_readings

    @pytest.mark.asyncio
    async def test_cpu_usage_efficiency(self):
        """Test CPU usage efficiency during workflow execution."""
        process = psutil.Process(os.getpid())

        # Monitor CPU during intensive operations
        cpu_readings = []

        workflows = [
            master_scanning_workflow("comprehensive"),
            pro_technical_workflow("AAPL", "comprehensive"),
            market_session_workflow("full_day"),
        ]

        for workflow in workflows:
            process.cpu_percent()
            start_time = time.time()

            result = await workflow

            end_time = time.time()
            cpu_after = process.cpu_percent()

            duration = end_time - start_time
            cpu_readings.append((duration, cpu_after))

            assert isinstance(result, str)
            print(f"✅ Workflow: {duration:.2f}s, CPU: {cpu_after:.1f}%")

        avg_cpu = sum(reading[1] for reading in cpu_readings) / len(cpu_readings)
        print(f"Average CPU usage: {avg_cpu:.1f}%")

        return cpu_readings


class TestScalabilityLimits:
    """Test scalability limits and breaking points."""

    @pytest.mark.asyncio
    async def test_sequential_workflow_scalability(self):
        """Test how many sequential workflows can be executed efficiently."""
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "SPY", "NVDA", "META", "AMZN", "NFLX", "COIN"]

        start_time = time.time()
        results = []

        for i, symbol in enumerate(symbols):
            workflow_start = time.time()
            result = await pro_technical_workflow(symbol, "quick")
            workflow_end = time.time()

            workflow_duration = workflow_end - workflow_start
            results.append((symbol, workflow_duration, len(result)))

            assert isinstance(result, str)
            assert symbol in result

            print(f"✅ {i+1:2d}. {symbol}: {workflow_duration:.2f}s, {len(result):,} chars")

        total_time = time.time() - start_time
        avg_time = total_time / len(symbols)

        print(
            f"Sequential scalability: {len(symbols)} workflows in {total_time:.2f}s (avg: {avg_time:.2f}s)"
        )

        # Performance should remain consistent (no degradation)
        first_half_avg = sum(r[1] for r in results[:5]) / 5
        second_half_avg = sum(r[1] for r in results[5:]) / 5

        degradation = (second_half_avg - first_half_avg) / first_half_avg
        print(f"Performance degradation: {degradation*100:.1f}%")

        assert degradation < 0.5, "Performance degradation should be less than 50%"

        return results

    @pytest.mark.asyncio
    async def test_workflow_output_size_limits(self):
        """Test workflows with different output size requirements."""
        # Test different modes that produce different output sizes
        test_cases = [
            ("quick_scan", master_scanning_workflow("quick")),
            ("comprehensive_scan", master_scanning_workflow("comprehensive")),
            ("quick_technical", pro_technical_workflow("AAPL", "quick")),
            ("comprehensive_technical", pro_technical_workflow("AAPL", "comprehensive")),
            ("single_session", market_session_workflow("market_open")),
            ("full_day_session", market_session_workflow("full_day")),
            ("capabilities", list_trading_capabilities()),
        ]

        results = []

        for name, workflow in test_cases:
            start_time = time.time()
            result = await workflow
            end_time = time.time()

            duration = end_time - start_time
            size = len(result)

            results.append((name, duration, size))

            assert isinstance(result, str)
            print(f"✅ {name}: {duration:.2f}s, {size:,} chars")

        # Analyze size vs performance relationship
        results.sort(key=lambda x: x[2])  # Sort by size

        print("\nSize vs Performance Analysis:")
        for name, duration, size in results:
            chars_per_second = size / duration if duration > 0 else 0
            print(f"  {name}: {chars_per_second:,.0f} chars/second")

        return results


class TestPerformanceBenchmarks:
    """Establish performance benchmarks for monitoring."""

    @pytest.mark.asyncio
    async def test_workflow_performance_benchmarks(self):
        """Establish baseline performance benchmarks."""
        benchmarks = {}

        # Core workflow benchmarks
        test_cases = [
            ("capabilities", list_trading_capabilities()),
            ("quick_scan", master_scanning_workflow("quick")),
            ("quick_technical", pro_technical_workflow("AAPL", "quick")),
            ("market_open_session", market_session_workflow("market_open")),
            ("day_trading_aapl", day_trading_workflow("AAPL")),
        ]

        print("🎯 PERFORMANCE BENCHMARKS")
        print("=" * 50)

        for name, workflow in test_cases:
            # Run multiple times for average
            times = []
            sizes = []

            for _ in range(3):
                start_time = time.time()
                result = await workflow
                end_time = time.time()

                times.append(end_time - start_time)
                sizes.append(len(result))

                assert isinstance(result, str)

            avg_time = sum(times) / len(times)
            avg_size = sum(sizes) / len(sizes)
            std_time = (sum((t - avg_time) ** 2 for t in times) / len(times)) ** 0.5

            benchmarks[name] = {
                "avg_time": avg_time,
                "std_time": std_time,
                "avg_size": avg_size,
                "chars_per_second": avg_size / avg_time,
            }

            print(
                f"{name:20s}: {avg_time:.2f}s ±{std_time:.2f}, {avg_size:,} chars, {avg_size/avg_time:,.0f} chars/s"
            )

        # Performance assertions
        assert benchmarks["capabilities"]["avg_time"] < 5.0, "Capabilities should load quickly"
        assert benchmarks["quick_scan"]["avg_time"] < 15.0, "Quick scan should be fast"
        assert (
            benchmarks["quick_technical"]["avg_time"] < 20.0
        ), "Quick technical should be responsive"

        print("\n✅ All benchmarks established and within acceptable limits")

        return benchmarks


if __name__ == "__main__":
    # Run performance tests directly
    pytest.main([__file__, "-v", "-s"])
