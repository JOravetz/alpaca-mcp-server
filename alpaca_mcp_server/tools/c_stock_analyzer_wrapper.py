"""
Fast C-based stock analyzer wrapper for real-time market analysis.

This module provides a Python wrapper around the high-performance C implementation
of stock market analysis. It analyzes snapshots, calculates gradients, and detects
high-activity stocks with complex filtering criteria.
"""

import json
import os
import subprocess
from pathlib import Path

# No config imports needed - using C program defaults


class CStockAnalyzer:
    """Wrapper for the C stock analyzer program."""

    def __init__(self):
        """Initialize the C program wrapper."""
        # Find the C program binary
        base_dir = Path(__file__).parent.parent.parent
        self.c_program_path = base_dir / "c_progs" / "stock_analyzer_json"

        # Check if binary exists, try to compile if not
        if not self.c_program_path.exists():
            # Try to compile it
            makefile_path = base_dir / "c_progs" / "Makefile"
            if makefile_path.exists():
                try:
                    result = subprocess.run(
                        ["make", "stock_analyzer_json"],
                        cwd=str(base_dir / "c_progs"),
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if result.returncode != 0:
                        raise RuntimeError(f"Failed to compile: {result.stderr}")
                except Exception as e:
                    raise FileNotFoundError(
                        f"C program not found at {self.c_program_path} and compilation failed: {e}\n"
                        "Please compile manually: cd c_progs && make stock_analyzer_json"
                    )

            # Check again after compile attempt
            if not self.c_program_path.exists():
                raise FileNotFoundError(
                    f"C program not found at {self.c_program_path}. "
                    "Please compile it first: cd c_progs && make stock_analyzer_json"
                )

        # Use the SAME defaults as the C program
        # From stock_analyzer_json.c help output:
        self.default_max_results = 5  # -n NUM default
        self.default_max_price = 30.0  # -p PRICE default
        self.default_min_change = 20.0  # -c PERCENT default
        self.default_min_trades = 1000  # -t TRADES default

    def analyze(
        self,
        symbols: str | list[str] | None = None,
        max_results: int | None = None,
        max_price: float = 30.0,
        min_percent_change: float | None = None,
        min_trades: int | None = None,
        symbols_file: str | None = None,
        sort_keys: str = "trades,percent_change",
        output_all: bool = False,
        raw_data: bool = False,
    ) -> dict:
        """
        Analyze stocks using the fast C implementation.

        Args:
            symbols: Optional symbols to analyze (comma-separated or list)
            max_results: Maximum number of results (uses config default if None)
            max_price: Maximum stock price filter
            min_percent_change: Minimum percent change threshold
            min_trades: Minimum trades threshold
            symbols_file: File containing symbols to analyze
            sort_keys: Comma-separated sort keys
            output_all: Output all symbols without filtering
            raw_data: Include raw snapshot data

        Returns:
            Dict containing analysis results
        """
        # Use defaults from config if not specified
        if max_results is None:
            max_results = self.default_max_results
        if min_percent_change is None:
            min_percent_change = self.default_min_change
        if min_trades is None:
            min_trades = self.default_min_trades

        # Build command
        cmd = [str(self.c_program_path)]

        if symbols:
            if isinstance(symbols, list):
                symbols_str = ",".join(symbols)
            else:
                symbols_str = symbols
            cmd.extend(["-s", symbols_str])

        if output_all:
            cmd.append("-a")
        else:
            cmd.extend(["-n", str(max_results)])
            cmd.extend(["-p", str(max_price)])
            cmd.extend(["-c", str(min_percent_change)])
            cmd.extend(["-t", str(min_trades)])

        if symbols_file:
            cmd.extend(["-f", symbols_file])

        if sort_keys:
            cmd.extend(["-k", sort_keys])

        if raw_data:
            cmd.append("-r")

        # Set environment variables for API access
        env = os.environ.copy()
        if "APCA_API_KEY_ID" not in env or "APCA_API_SECRET_KEY" not in env:
            from alpaca_mcp_server.config.settings import settings

            env["APCA_API_KEY_ID"] = settings.api_key  # type: ignore[assignment]
            env["APCA_API_SECRET_KEY"] = settings.api_secret  # type: ignore[assignment]

        try:
            # Run the C program
            result = subprocess.run(
                cmd, capture_output=True, text=True, env=env, timeout=30, check=True
            )

            # Parse JSON output
            if result.stdout:
                # Find JSON in output (may have debug text before it)
                stdout = result.stdout.strip()
                json_start = stdout.find("{")
                if json_start != -1:
                    json_str = stdout[json_start:]
                    return json.loads(json_str)
                else:
                    return {"error": "No JSON in output", "raw_output": stdout}
            else:
                return {"error": "No output from C program", "stderr": result.stderr}

        except subprocess.TimeoutExpired:
            return {"error": "C program timed out after 30 seconds"}
        except subprocess.CalledProcessError as e:
            return {
                "error": f"C program failed with exit code {e.returncode}",
                "stderr": e.stderr,
                "stdout": e.stdout,
            }
        except json.JSONDecodeError as e:
            return {
                "error": f"Failed to parse C program output as JSON: {e}",
                "raw_output": result.stdout if "result" in locals() else None,
            }
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}


async def analyze_market_activity_fast(
    symbols: str | None = None,
    max_results: int = 5,  # C program default
    max_price: float = 30.0,  # C program default
    min_percent_change: float = 20.0,  # C program default
    min_trades: int = 1000,  # C program default
    sort_by: str = "trades,percent_change",  # C program default
) -> str:
    """
    Ultra-fast market activity analysis using C implementation.

    Analyzes real-time stock snapshots to find high-activity stocks with
    momentum. Calculates gradients, volume changes, and trade intensity.

    Args:
        symbols: Optional comma-separated symbols to analyze (None = use default list)
        max_results: Maximum number of results to return
        max_price: Maximum stock price filter (for penny stock focus)
        min_percent_change: Minimum percent change threshold
        min_trades: Minimum trades threshold
        sort_by: Sort keys (trades, percent_change, volume, gradient_change)

    Returns:
        Formatted string with market analysis and trading opportunities
    """
    try:
        # Create analyzer instance
        analyzer = CStockAnalyzer()

        # Run analysis
        result = analyzer.analyze(
            symbols=symbols,
            max_results=max_results,
            max_price=max_price,
            min_percent_change=min_percent_change,
            min_trades=min_trades,
            sort_keys=sort_by,
            output_all=False,
        )

        # Check for errors
        if "error" in result:
            return f"❌ C Analyzer Error: {result['error']}\n{result.get('stderr', '')}"

        # Format output
        output = []
        output.append("=" * 80)
        output.append("🚀 FAST Market Activity Analysis (C Implementation)")
        output.append("=" * 80)

        # Summary section
        output.append("\n📊 Analysis Summary:")
        output.append(f"  • Total Processed: {result.get('total_processed', 0)} stocks")
        output.append(f"  • Active Stocks Found: {result.get('results_count', 0)}")
        output.append(f"  • Max Price Filter: ${max_price:.2f}")
        output.append(f"  • Min Change Filter: {min_percent_change:.1f}%")
        output.append(f"  • Min Trades Filter: {min_trades}")

        # Stock results
        stocks = result.get("stocks", [])
        if stocks:
            output.append(f"\n🔥 High Activity Stocks ({len(stocks)} found):")
            output.append("-" * 40)

            for stock in stocks:
                rank = stock.get("rank", 0)
                symbol = stock["symbol"]
                price = stock["price"]
                percent_change = stock["percent_change"]
                gradient_change = stock.get("gradient_change", 0)
                volume = stock["volume"]
                trades = stock["trades"]

                # Determine trading signal
                if percent_change > 10:
                    signal = "🟢 STRONG BUY"
                    color = "32"
                elif percent_change > 5:
                    signal = "🟡 BUY"
                    color = "33"
                elif percent_change < -5:
                    signal = "🔴 AVOID"
                    color = "31"
                else:
                    signal = "⚪ MONITOR"
                    color = "37"

                output.append(f"\n  #{rank} {symbol}:")
                output.append(f"    • Price: ${price:.4f}")
                output.append(f"    • Change: {percent_change:+.2f}%")
                output.append(f"    • Gradient Change: {gradient_change:+.2f}%")
                output.append(f"    • Volume: {volume:,}")
                output.append(f"    • Trades: {trades:,}")
                output.append(f"    • Signal: {signal}")
        else:
            output.append("\n⚠️ No stocks found matching criteria")
            output.append("   Try relaxing filters or checking market hours")

        # Performance note
        output.append("\n⚡ Using high-performance C implementation")
        output.append("=" * 80)

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error in fast market analysis: {str(e)}"


async def scan_explosive_stocks_fast(
    max_results: int = 20,
    min_percent_change: float = 15.0,  # Higher for explosive moves
    max_price: float = 30.0,  # C program default for penny stocks
) -> str:
    """
    Fast scan for explosive momentum stocks using C analyzer.

    Optimized for finding extreme percentage movers with high activity.
    Perfect for day trading volatile penny stocks.

    Args:
        max_results: Maximum number of results
        min_percent_change: Minimum percent change for explosive moves
        max_price: Maximum price (focus on penny stocks)

    Returns:
        Formatted list of explosive opportunities
    """
    # Use lower trades threshold for explosive penny stocks
    min_trades = 100  # Lower threshold for volatile stocks

    # Create analyzer instance and run analysis directly
    analyzer = CStockAnalyzer()
    result = analyzer.analyze(
        symbols=None,  # Use default symbol list
        max_results=max_results,
        max_price=max_price,
        min_percent_change=min_percent_change,
        min_trades=min_trades,
        sort_keys="percent_change,trades",  # Sort by biggest movers first
        output_all=False,
    )

    # Check for errors
    if "error" in result:
        return f"❌ C Analyzer Error: {result['error']}\n{result.get('stderr', '')}"

    # Format output similar to analyze_market_activity_fast but with explosive header
    output = []
    output.append("=" * 80)
    output.append("💥 EXPLOSIVE Stock Scanner (C Implementation)")
    output.append("=" * 80)

    # Summary section
    output.append("\n📊 Scanner Settings:")
    output.append(f"  • Max Price Filter: ${max_price:.2f}")
    output.append(f"  • Min Change Filter: {min_percent_change:.1f}%")
    output.append(f"  • Min Trades Filter: {min_trades}")

    # Stock results
    stocks = result.get("stocks", [])
    if stocks:
        output.append(f"\n🔥 Explosive Stocks Found ({len(stocks)}):")
        output.append("-" * 40)

        for stock in stocks:
            rank = stock.get("rank", 0)
            symbol = stock["symbol"]
            price = stock["price"]
            percent_change = stock["percent_change"]
            volume = stock["volume"]
            trades = stock["trades"]

            # Explosive signals
            if percent_change > 20:
                signal = "🚀 ROCKET"
            elif percent_change > 15:
                signal = "🔥 HOT"
            else:
                signal = "⚡ ACTIVE"

            output.append(f"\n  #{rank} {symbol}: {signal}")
            output.append(f"    • Price: ${price:.4f}")
            output.append(f"    • Change: {percent_change:+.2f}%")
            output.append(f"    • Volume: {volume:,}")
            output.append(f"    • Trades: {trades:,}")
    else:
        output.append("\n⚠️ No explosive stocks found")
        output.append("   Market may be calm - check again soon")

    output.append("\n" + "=" * 80)
    return "\n".join(output)


async def compare_analyzer_performance(
    test_symbols: str = "AAPL,MSFT,NVDA,SPY,TSLA",
) -> str:
    """
    Compare performance between C analyzer and Python scanners.

    Args:
        test_symbols: Symbols to test with

    Returns:
        Performance comparison report
    """
    import time

    output = []
    output.append("=" * 60)
    output.append("⚡ Analyzer Performance Comparison")
    output.append("=" * 60)
    output.append(f"Test Symbols: {test_symbols}")
    output.append("-" * 60)

    # Test C implementation
    start_c = time.time()
    analyzer = CStockAnalyzer()
    c_result = analyzer.analyze(
        symbols=test_symbols,
        max_results=10,
        output_all=True,
    )
    c_time = time.time() - start_c

    # Test Python scanner (if available)
    try:
        from alpaca_mcp_server.tools.day_trading_scanner import scan_day_trading_opportunities

        start_py = time.time()
        py_result = await scan_day_trading_opportunities(
            symbols=test_symbols,
            min_trades_per_minute=0,
            min_percent_change=0,
            max_symbols=10,
        )
        py_time = time.time() - start_py

        speedup = py_time / c_time if c_time > 0 else float("inf")

        output.append("\n📊 Results:")
        output.append(f"  • C Analyzer: {c_time:.3f} seconds")
        output.append(f"  • Python Scanner: {py_time:.3f} seconds")
        output.append(f"  • Speedup: {speedup:.1f}x faster with C")
    except Exception as e:
        output.append("\n📊 Results:")
        output.append(f"  • C Analyzer: {c_time:.3f} seconds")
        output.append(f"  • Python Scanner: Not available ({e})")

    # Validate results
    c_stocks = c_result.get("results_count", 0) if isinstance(c_result, dict) else 0
    output.append("\n✅ Validation:")
    output.append(f"  • C found {c_stocks} stocks")

    output.append("\n" + "=" * 60)

    return "\n".join(output)


# Tool metadata for MCP registration
TOOL_METADATA = {
    "analyze_market_activity_fast": {
        "name": "analyze_market_activity_fast",
        "description": "Ultra-fast market activity scanner using C (10x+ faster)",
        "parameters": {
            "symbols": "Optional symbols to analyze",
            "max_results": "Maximum results to return",
            "max_price": "Maximum stock price filter",
            "min_percent_change": "Minimum percent change",
            "min_trades": "Minimum trades threshold",
            "sort_by": "Sort keys for results",
        },
    },
    "scan_explosive_stocks_fast": {
        "name": "scan_explosive_stocks_fast",
        "description": "Fast scan for explosive penny stocks",
        "parameters": {
            "max_results": "Maximum results",
            "min_percent_change": "Minimum percent change",
            "max_price": "Maximum price filter",
        },
    },
}
