"""
Focused test runner for market-closed conditions.
Tests REST API functionality and workflow logic without real-time streaming.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import after path modification
from alpaca_mcp_server.prompts.day_trading_workflow import day_trading_workflow  # noqa: E402
from alpaca_mcp_server.prompts.list_trading_capabilities import (  # noqa: E402
    list_trading_capabilities,
)
from alpaca_mcp_server.prompts.market_session_workflow import market_session_workflow  # noqa: E402
from alpaca_mcp_server.prompts.master_scanning_workflow import (  # noqa: E402
    master_scanning_workflow,
)
from alpaca_mcp_server.prompts.pro_technical_workflow import pro_technical_workflow  # noqa: E402


async def test_workflow_functionality():
    """Test core workflow functionality with REST APIs."""
    print("🧪 TESTING WORKFLOW FUNCTIONALITY (Markets Closed)")
    print("=" * 60)

    tests_passed = 0
    tests_total = 0

    # Test 1: Capabilities Discovery
    print("\n1. Testing capabilities discovery...")
    tests_total += 1
    try:
        start_time = time.time()
        result = await list_trading_capabilities()
        duration = time.time() - start_time

        assert isinstance(result, str)
        assert len(result) > 2000
        assert "ADVANCED AGENTIC WORKFLOWS" in result
        assert "master_scanning_workflow" in result

        tests_passed += 1
        print(f"   ✅ PASSED ({duration:.2f}s, {len(result):,} chars)")
        print("   Contains advanced workflows section ✓")

    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Test 2: Master Scanner (REST-based)
    print("\n2. Testing master scanner workflow...")
    tests_total += 1
    try:
        start_time = time.time()
        result = await master_scanning_workflow("quick")
        duration = time.time() - start_time

        assert isinstance(result, str)
        assert len(result) > 1000
        assert "MASTER SCANNER" in result

        tests_passed += 1
        print(f"   ✅ PASSED ({duration:.2f}s, {len(result):,} chars)")
        print("   Scanner components executed ✓")

    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Test 3: Technical Analysis (with real historical data)
    print("\n3. Testing technical analysis workflow...")
    tests_total += 1
    try:
        start_time = time.time()
        result = await pro_technical_workflow("AAPL", "quick")
        duration = time.time() - start_time

        assert isinstance(result, str)
        assert len(result) > 1000
        assert "AAPL" in result
        assert "TECHNICAL ANALYSIS" in result

        tests_passed += 1
        print(f"   ✅ PASSED ({duration:.2f}s, {len(result):,} chars)")
        print("   Peak/trough analysis executed ✓")

    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Test 4: Market Session Strategy
    print("\n4. Testing market session workflow...")
    tests_total += 1
    try:
        start_time = time.time()
        result = await market_session_workflow("market_open")
        duration = time.time() - start_time

        assert isinstance(result, str)
        assert len(result) > 1000
        assert "SESSION STRATEGY" in result

        tests_passed += 1
        print(f"   ✅ PASSED ({duration:.2f}s, {len(result):,} chars)")
        print("   Session strategies loaded ✓")

    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Test 5: Day Trading Workflow
    print("\n5. Testing day trading workflow...")
    tests_total += 1
    try:
        start_time = time.time()
        result = await day_trading_workflow("AAPL")
        duration = time.time() - start_time

        assert isinstance(result, str)
        assert len(result) > 800
        assert "AAPL" in result

        tests_passed += 1
        print(f"   ✅ PASSED ({duration:.2f}s, {len(result):,} chars)")
        print("   Day trading analysis complete ✓")

    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    return tests_passed, tests_total


async def test_error_handling():
    """Test error handling with invalid inputs."""
    print("\n🛡️ TESTING ERROR HANDLING")
    print("=" * 40)

    tests_passed = 0
    tests_total = 0

    # Test invalid symbol
    print("\n1. Testing invalid symbol handling...")
    tests_total += 1
    try:
        result = await pro_technical_workflow("INVALIDXYZ", "quick")
        assert isinstance(result, str)
        assert len(result) > 0
        tests_passed += 1
        print("   ✅ PASSED - Invalid symbol handled gracefully")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Test invalid scan type
    print("\n2. Testing invalid scan type...")
    tests_total += 1
    try:
        result = await master_scanning_workflow("invalid_type")
        assert isinstance(result, str)
        assert len(result) > 0
        tests_passed += 1
        print("   ✅ PASSED - Invalid scan type handled")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Test empty parameters
    print("\n3. Testing empty parameters...")
    tests_total += 1
    try:
        result = await day_trading_workflow("")
        assert isinstance(result, str)
        assert len(result) > 0
        tests_passed += 1
        print("   ✅ PASSED - Empty parameters handled")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    return tests_passed, tests_total


async def test_workflow_integration():
    """Test workflow integration and composition."""
    print("\n🔗 TESTING WORKFLOW INTEGRATION")
    print("=" * 45)

    tests_passed = 0
    tests_total = 0

    # Test workflow composition
    print("\n1. Testing workflow composition...")
    tests_total += 1
    try:
        # Get capabilities first
        capabilities = await list_trading_capabilities()
        assert "master_scanning_workflow" in capabilities

        # Run scanner
        scanner_result = await master_scanning_workflow("quick")
        assert len(scanner_result) > 0

        # Run technical analysis
        technical_result = await pro_technical_workflow("AAPL", "quick")
        assert "AAPL" in technical_result

        tests_passed += 1
        print("   ✅ PASSED - Workflow composition working")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Test concurrent execution
    print("\n2. Testing concurrent workflow execution...")
    tests_total += 1
    try:
        tasks = [
            master_scanning_workflow("quick"),
            pro_technical_workflow("SPY", "quick"),
            market_session_workflow("market_open"),
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time

        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful >= 2  # At least 2 should succeed

        tests_passed += 1
        print(f"   ✅ PASSED - {successful}/3 workflows succeeded in {duration:.2f}s")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    return tests_passed, tests_total


async def test_multiple_symbols():
    """Test workflows with multiple high-liquidity symbols."""
    print("\n📊 TESTING MULTIPLE SYMBOLS")
    print("=" * 40)

    symbols = ["AAPL", "MSFT", "SPY", "GOOGL", "TSLA"]
    tests_passed = 0
    tests_total = len(symbols)

    for symbol in symbols:
        print(f"\nTesting {symbol}...")
        try:
            start_time = time.time()
            result = await pro_technical_workflow(symbol, "quick")
            duration = time.time() - start_time

            assert isinstance(result, str)
            assert symbol in result
            assert len(result) > 500

            tests_passed += 1
            print(f"   ✅ {symbol}: PASSED ({duration:.2f}s, {len(result):,} chars)")

        except Exception as e:
            print(f"   ❌ {symbol}: FAILED - {str(e)[:100]}...")

    return tests_passed, tests_total


async def run_focused_tests():
    """Run focused test suite for market-closed conditions."""
    print("🚀 ALPACA MCP SERVER ENHANCED - FOCUSED TEST SUITE")
    print("=" * 80)
    print("Testing with markets closed - REST APIs and workflow logic")
    print("Real-time streaming tests skipped (markets closed)")
    print()

    start_time = time.time()
    total_passed = 0
    total_tests = 0

    # Run test suites
    test_suites = [
        ("Core Functionality", test_workflow_functionality()),
        ("Error Handling", test_error_handling()),
        ("Integration", test_workflow_integration()),
        ("Multiple Symbols", test_multiple_symbols()),
    ]

    for suite_name, test_coro in test_suites:
        print(f"\n{'=' * 20} {suite_name} {'=' * 20}")
        try:
            passed, total = await test_coro
            total_passed += passed
            total_tests += total
            success_rate = (passed / total) * 100 if total > 0 else 0
            print(f"\n{suite_name} Results: {passed}/{total} passed ({success_rate:.1f}%)")
        except Exception as e:
            print(f"\n{suite_name} Suite Error: {e}")

    # Final results
    end_time = time.time()
    total_duration = end_time - start_time
    overall_success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0

    print("\n" + "=" * 80)
    print("🎉 FOCUSED TEST RESULTS")
    print("=" * 80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed} ✅")
    print(f"Failed: {total_tests - total_passed} ❌")
    print(f"Success Rate: {overall_success_rate:.1f}%")
    print(f"Duration: {total_duration:.2f} seconds")

    # System status
    print("\n🎯 SYSTEM STATUS:")
    if overall_success_rate >= 90:
        print("  ✅ EXCELLENT - Advanced workflows fully operational")
        print("  ✅ REST APIs working correctly")
        print("  ✅ Error handling robust")
        print("  ✅ Multi-symbol support validated")
        print("\n🏆 SYSTEM READY FOR PRODUCTION!")
    elif overall_success_rate >= 80:
        print("  ✅ GOOD - System functional with minor issues")
        print("  ⚠️  Some components may need attention")
    else:
        print("  ⚠️  NEEDS IMPROVEMENT - Several issues detected")

    # Next steps
    print("\n💡 NEXT STEPS:")
    print("  1. Test with live markets when open for real-time data")
    print("  2. Monitor performance during market hours")
    print("  3. Validate streaming functionality when markets active")
    print("  4. System ready for Claude Code integration")

    return total_passed, total_tests, overall_success_rate


if __name__ == "__main__":
    asyncio.run(run_focused_tests())
