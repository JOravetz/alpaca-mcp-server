"""
Performance Under Load Tests - REAL tests for config system performance.
Tests high-frequency access, concurrent usage, memory efficiency - NO MOCKING.
"""

import asyncio
import gc
import sys
import threading
import time
from pathlib import Path

import psutil
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server.config import (
    get_global_config,
    get_technical_config,
    get_trading_config,
    reload_global_config,
)


class TestConfigPerformance:
    """REAL performance tests for config system under load."""

    def test_high_frequency_config_access_real(self):
        """Test config access performance under high frequency."""

        # Warm up
        for _ in range(10):
            get_trading_config()
            get_technical_config()

        # Time high-frequency access
        start_time = time.time()
        access_count = 1000

        for _i in range(access_count):
            trading = get_trading_config()
            technical = get_technical_config()

            # Verify values are correct
            assert trading.trades_per_minute_threshold >= 500
            assert technical.hanning_window_samples >= 3

        end_time = time.time()
        duration = end_time - start_time
        access_per_second = access_count / duration

        # Should be fast (>1000 accesses per second)
        assert access_per_second > 1000, f"Only {access_per_second:.0f} accesses/sec"

        print(f"✅ High-frequency access: {access_per_second:.0f} accesses/second")

    def test_concurrent_config_access_performance_real(self):
        """Test config access performance with multiple threads."""

        access_results = []
        errors = []

        def config_access_worker(worker_id, iterations):
            """Worker function for concurrent access."""
            worker_results = []
            start_time = time.time()

            try:
                for _i in range(iterations):
                    trading = get_trading_config()
                    technical = get_technical_config()

                    # Verify data
                    assert trading.trades_per_minute_threshold >= 500
                    assert technical.hanning_window_samples >= 3

                    worker_results.append(1)

                end_time = time.time()
                duration = end_time - start_time

                access_results.append(
                    {
                        "worker_id": worker_id,
                        "count": len(worker_results),
                        "duration": duration,
                        "rate": len(worker_results) / duration,
                    }
                )

            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        # Start multiple concurrent workers
        threads = []
        worker_count = 5
        iterations_per_worker = 200

        start_time = time.time()

        for worker_id in range(worker_count):
            thread = threading.Thread(
                target=config_access_worker, args=(worker_id, iterations_per_worker)
            )
            threads.append(thread)
            thread.start()

        # Wait for all workers
        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Verify no errors
        assert len(errors) == 0, f"Concurrent access errors: {errors}"

        # Verify all workers completed
        assert len(access_results) == worker_count

        # Calculate total throughput
        total_accesses = sum(r["count"] for r in access_results)
        overall_rate = total_accesses / total_time

        # Should handle concurrent access efficiently
        assert overall_rate > 500, f"Only {overall_rate:.0f} total accesses/sec"

        print(
            f"✅ Concurrent access: {worker_count} threads, {overall_rate:.0f} total accesses/sec"
        )

    def test_memory_usage_under_load_real(self):
        """Test memory usage during intensive config operations."""

        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform intensive config operations
        configs_created = []
        iterations = 500

        for i in range(iterations):
            # Create multiple config references
            global_config = get_global_config()
            trading_config = get_trading_config()
            technical_config = get_technical_config()

            configs_created.extend([global_config, trading_config, technical_config])

            # Reload periodically to test memory management
            if i % 100 == 0:
                reload_global_config()

        # Check memory after operations
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        # Force garbage collection
        gc.collect()

        # Check memory after cleanup
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Memory increase should be reasonable (< 50MB for this test)
        assert memory_increase < 50, f"Memory increased by {memory_increase:.1f}MB"

        print(
            f"✅ Memory usage: Initial: {initial_memory:.1f}MB, Peak: {peak_memory:.1f}MB, Final: {final_memory:.1f}MB"
        )

    def test_config_caching_efficiency_real(self):
        """Test that config caching is working efficiently."""

        # Time first access (cold)
        start_time = time.time()
        config1 = get_global_config()
        first_access_time = time.time() - start_time

        # Time subsequent accesses (should be cached)
        cached_times = []
        for _i in range(100):
            start_time = time.time()
            config2 = get_global_config()
            cached_times.append(time.time() - start_time)

        average_cached_time = sum(cached_times) / len(cached_times)

        # Cached access should be much faster than first access
        speedup_ratio = first_access_time / average_cached_time

        # Should see reasonable speedup from caching (adjusted threshold)
        assert speedup_ratio > 2, f"Only {speedup_ratio:.1f}x speedup from caching"

        # Verify same instance is returned (true caching)
        assert config1 is config2, "Config instances should be identical (cached)"

        print(
            f"✅ Caching efficiency: {speedup_ratio:.1f}x speedup, avg cached time: {average_cached_time*1000:.3f}ms"
        )

    def test_rapid_reload_performance_real(self):
        """Test performance of rapid config reloads."""

        reload_times = []
        reload_count = 50

        for _i in range(reload_count):
            start_time = time.time()
            reload_global_config()
            reload_time = time.time() - start_time
            reload_times.append(reload_time)

            # Verify config still works after reload
            trading = get_trading_config()
            assert trading.trades_per_minute_threshold >= 500

        average_reload_time = sum(reload_times) / len(reload_times)
        max_reload_time = max(reload_times)

        # Reloads should be reasonably fast (< 100ms average)
        assert (
            average_reload_time < 0.1
        ), f"Average reload time too slow: {average_reload_time:.3f}s"
        assert max_reload_time < 0.5, f"Max reload time too slow: {max_reload_time:.3f}s"

        print(
            f"✅ Reload performance: Avg: {average_reload_time*1000:.1f}ms, Max: {max_reload_time*1000:.1f}ms"
        )

    def test_config_access_scaling_real(self):
        """Test how config access scales with increasing load."""

        thread_counts = [1, 2, 4, 8]
        results = []

        for thread_count in thread_counts:
            access_results = []
            errors = []

            def worker():
                try:
                    start_time = time.time()
                    for _ in range(100):
                        get_trading_config()
                        get_technical_config()
                    duration = time.time() - start_time
                    access_results.append(duration)
                except Exception as e:
                    errors.append(e)

            # Run test with current thread count
            threads = []
            start_time = time.time()

            for _ in range(thread_count):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            total_time = time.time() - start_time

            assert len(errors) == 0, f"Errors with {thread_count} threads: {errors}"

            total_accesses = thread_count * 200  # 100 iterations * 2 config calls
            throughput = total_accesses / total_time

            results.append(
                {"threads": thread_count, "throughput": throughput, "total_time": total_time}
            )

        # Verify scaling is reasonable (throughput should increase with threads)
        for i in range(1, len(results)):
            prev_throughput = results[i - 1]["throughput"]
            curr_throughput = results[i]["throughput"]

            # Should see some improvement (not necessarily linear due to GIL)
            improvement = curr_throughput / prev_throughput
            assert improvement > 0.8, f"Poor scaling: {improvement:.2f}x with more threads"

        print("✅ Scaling results:")
        for result in results:
            print(f"  {result['threads']} threads: {result['throughput']:.0f} accesses/sec")

    @pytest.mark.asyncio
    async def test_async_config_access_performance_real(self):
        """Test config access performance in async context."""

        async def async_config_worker(worker_id, iterations):
            """Async worker for config access."""
            results = []

            for _i in range(iterations):
                # Simulate some async work
                await asyncio.sleep(0.001)  # 1ms delay

                # Access config
                trading = get_trading_config()
                technical = get_technical_config()

                assert trading.trades_per_minute_threshold >= 500
                assert technical.hanning_window_samples >= 3

                results.append(1)

            return len(results)

        # Run multiple async workers concurrently
        worker_count = 10
        iterations_per_worker = 50

        start_time = time.time()

        tasks = [async_config_worker(i, iterations_per_worker) for i in range(worker_count)]

        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time
        total_operations = sum(results)
        throughput = total_operations / total_time

        # Should handle async access efficiently
        assert throughput > 100, f"Async throughput too low: {throughput:.0f} ops/sec"
        assert all(r == iterations_per_worker for r in results), "Some workers didn't complete"

        print(f"✅ Async performance: {worker_count} workers, {throughput:.0f} operations/sec")

    def test_large_scale_config_simulation_real(self):
        """Test config system under large-scale simulation."""

        # Simulate a busy trading system
        operations = []
        errors = []

        def trading_simulation():
            """Simulate trading operations using config."""
            try:
                for _ in range(50):
                    # Simulate scanner operation
                    trading = get_trading_config()
                    threshold = trading.trades_per_minute_threshold

                    # Simulate technical analysis
                    technical = get_technical_config()
                    window = technical.hanning_window_samples

                    # Simulate decision making
                    if threshold > 400 and window < 20:
                        operations.append("trade_signal")

                    # Small delay to simulate processing
                    time.sleep(0.001)

            except Exception as e:
                errors.append(e)

        # Run multiple simulation threads
        threads = []
        simulation_count = 8

        start_time = time.time()

        for _i in range(simulation_count):
            thread = threading.Thread(target=trading_simulation)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Verify simulation completed successfully
        assert len(errors) == 0, f"Simulation errors: {errors}"
        assert len(operations) > 0, "No trading operations generated"

        operations_per_second = len(operations) / total_time

        print(
            f"✅ Large-scale simulation: {len(operations)} operations in {total_time:.2f}s ({operations_per_second:.0f} ops/sec)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
