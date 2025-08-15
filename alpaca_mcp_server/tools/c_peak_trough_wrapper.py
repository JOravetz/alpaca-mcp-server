"""
Fast C-based peak and trough analysis wrapper.

This module provides a Python wrapper around the high-performance C implementation
of peak/trough detection using zero-phase Hanning filtering. The C program is
significantly faster than the pure Python implementation, making it ideal for
real-time scanning and high-frequency analysis.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from alpaca_mcp_server.config import get_global_config, get_technical_config


class CPeakTroughAnalyzer:
    """Wrapper for the C peak/trough analysis program."""

    def __init__(self):
        """Initialize the C program wrapper."""
        # Find the C program binary
        base_dir = Path(__file__).parent.parent.parent
        self.c_program_path = base_dir / "c_progs" / "filter_bars_input"
        
        # Check if binary exists, try to compile if not
        if not self.c_program_path.exists():
            # Try to compile it
            makefile_path = base_dir / "c_progs" / "Makefile"
            if makefile_path.exists():
                try:
                    import subprocess
                    result = subprocess.run(
                        ["make", "filter_bars_input"],
                        cwd=str(base_dir / "c_progs"),
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode != 0:
                        raise RuntimeError(f"Failed to compile: {result.stderr}")
                except Exception as e:
                    raise FileNotFoundError(
                        f"C program not found at {self.c_program_path} and compilation failed: {e}\n"
                        "Please compile manually: cd c_progs && make filter_bars_input"
                    )
            
            # Check again after compile attempt
            if not self.c_program_path.exists():
                raise FileNotFoundError(
                    f"C program not found at {self.c_program_path}. "
                    "Please compile it first: cd c_progs && make filter_bars_input"
                )
        
        # Get global configuration for defaults
        tech_config = get_technical_config()
        self.default_window = tech_config.hanning_window_samples
        self.default_lookahead = tech_config.peak_trough_lookahead

    def analyze(
        self,
        symbols: Union[str, List[str]],
        timeframe: str = "1Min",
        days: int = 1,
        window_length: Optional[int] = None,
        filter_key: str = "close",
        feed: str = "sip",
        print_signals: bool = True,
        input_file: Optional[str] = None,
    ) -> Dict:
        """
        Analyze stocks using the fast C implementation.

        Args:
            symbols: Single symbol or list of symbols
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
            days: Number of trading days to analyze
            window_length: Hanning window length (uses global config if None)
            filter_key: Data field to filter (open, high, low, close, vwap)
            feed: Data feed source (sip, iex, otc)
            print_signals: Whether to output trading signals
            input_file: Optional JSON file with existing data (skips API fetch)

        Returns:
            Dict containing analysis results
        """
        # Prepare symbols
        if isinstance(symbols, list):
            symbols_str = ",".join(symbols)
        else:
            symbols_str = symbols
        
        # Use default window if not specified
        if window_length is None:
            window_length = self.default_window
        
        # Build command
        cmd = [
            str(self.c_program_path),
            "-s", symbols_str,
            "-t", timeframe,
            "-n", str(days),
            "-w", str(window_length),
            "-k", filter_key,
            "--feed", feed,
        ]
        
        if print_signals:
            cmd.append("-p")
        
        if input_file:
            cmd.extend(["-i", input_file])
        
        # Set environment variables for API access
        env = os.environ.copy()
        # These should already be set, but ensure they're available
        if "APCA_API_KEY_ID" not in env or "APCA_API_SECRET_KEY" not in env:
            from alpaca_mcp_server.config.settings import settings
            env["APCA_API_KEY_ID"] = settings.api_key
            env["APCA_API_SECRET_KEY"] = settings.api_secret
        
        try:
            # Run the C program
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=30,  # 30 second timeout
                check=True
            )
            
            # Parse JSON output
            if result.stdout:
                # The C program outputs some text before the JSON
                # Look for the JSON part (starts with '{')
                stdout = result.stdout.strip()
                json_start = stdout.find('{')
                if json_start != -1:
                    json_str = stdout[json_start:]
                    return json.loads(json_str)
                else:
                    # No JSON found, might be an error or different format
                    return {"error": "No JSON in output", "raw_output": stdout}
            else:
                return {"error": "No output from C program", "stderr": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"error": "C program timed out after 30 seconds"}
        except subprocess.CalledProcessError as e:
            return {
                "error": f"C program failed with exit code {e.returncode}",
                "stderr": e.stderr,
                "stdout": e.stdout
            }
        except json.JSONDecodeError as e:
            return {
                "error": f"Failed to parse C program output as JSON: {e}",
                "raw_output": result.stdout if 'result' in locals() else None
            }
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}


async def analyze_peaks_troughs_fast(
    symbols: str,
    timeframe: str = "1Min", 
    days: int = 1,
    window_len: Optional[int] = None,
    filter_key: str = "close",
    feed: str = "sip",
) -> str:
    """
    Fast peak and trough analysis using C implementation.
    
    This is the main MCP tool function that uses the C program for speed.
    It's 5-10x faster than the Python implementation, especially for
    multiple symbols or large datasets.
    
    Args:
        symbols: Comma-separated symbols or "AUTO" for scanner results
        timeframe: Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
        days: Number of trading days to analyze (1-30)
        window_len: Hanning filter window length (3-101, odd)
        filter_key: Data field to filter (close, open, high, low, vwap)
        feed: Data feed source (sip, iex, otc)
    
    Returns:
        Formatted string with analysis results and trading signals
    """
    try:
        # Handle AUTO mode
        if symbols.upper() == "AUTO":
            # Get symbols from scanner
            try:
                from alpaca_mcp_server.tools.day_trading_scanner import get_scanner_results
                scanner_symbols = await get_scanner_results()
                if not scanner_symbols:
                    return "No symbols available from scanner. Run scan_day_trading_opportunities first."
                symbols = ",".join(scanner_symbols[:10])  # Limit to top 10
            except Exception as e:
                return f"Error getting scanner results: {str(e)}"
        
        # Validate parameters
        days = max(1, min(30, days))
        
        if window_len:
            window_len = max(3, min(101, window_len))
            if window_len % 2 == 0:
                window_len += 1  # Make odd
        
        # Create analyzer instance
        analyzer = CPeakTroughAnalyzer()
        
        # Run analysis
        result = analyzer.analyze(
            symbols=symbols,
            timeframe=timeframe,
            days=days,
            window_length=window_len,
            filter_key=filter_key,
            feed=feed,
            print_signals=True,
        )
        
        # Check for errors
        if "error" in result:
            return f"❌ C Analysis Error: {result['error']}\n{result.get('stderr', '')}"
        
        # Format output
        output = []
        output.append("=" * 80)
        output.append("📊 FAST Peak and Trough Analysis (C Implementation)")
        output.append("=" * 80)
        
        # Parameters section
        if "parameters" in result:
            params = result["parameters"]
            output.append(f"\n⚙️ Parameters:")
            output.append(f"  • Timeframe: {params.get('timeframe', timeframe)}")
            output.append(f"  • Window Length: {params.get('window_length', window_len)}")
            output.append(f"  • Filter Key: {params.get('filter_key', filter_key)}")
            output.append(f"  • Data Range: {params.get('data_range', f'{days} days')}")
            output.append(f"  • Current Time: {params.get('current_time_et', 'N/A')}")
        
        # Trading signals section
        if "signals" in result and result["signals"]:
            output.append(f"\n📈 Trading Signals ({result.get('count', len(result['signals']))} active):")
            output.append("-" * 40)
            
            for signal in result["signals"]:
                symbol = signal["symbol"]
                signal_type = signal["last_signal"]
                signal_price = signal["signal_price"]
                current_price = signal["current_price"]
                percent_diff = signal["percent_diff"]
                samples_ago = signal["samples_ago"]
                signal_time = signal.get("signal_time_et", signal.get("signal_timestamp_utc"))
                
                # Determine action based on signal type
                if signal_type == "Support" and percent_diff < 1.0:
                    action = "🟢 BUY SIGNAL"
                    color = "32"  # Green
                elif signal_type == "Resistance" and percent_diff > -1.0:
                    action = "🔴 SELL SIGNAL"
                    color = "31"  # Red
                else:
                    action = "⚪ MONITOR"
                    color = "37"  # White
                
                output.append(f"\n  {symbol}:")
                output.append(f"    • Signal: {signal_type} @ ${signal_price:.4f}")
                output.append(f"    • Current: ${current_price:.4f} ({percent_diff:+.2f}%)")
                output.append(f"    • Time: {signal_time} ({samples_ago} bars ago)")
                output.append(f"    • Action: {action}")
        
        # Performance note
        output.append(f"\n⚡ Using high-performance C implementation for faster analysis")
        output.append("=" * 80)
        
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ Error in fast peak/trough analysis: {str(e)}"


async def compare_implementations(
    symbol: str,
    timeframe: str = "1Min",
    days: int = 1,
) -> str:
    """
    Compare performance between C and Python implementations.
    
    Args:
        symbol: Stock symbol to analyze
        timeframe: Bar timeframe
        days: Number of days to analyze
    
    Returns:
        Performance comparison report
    """
    import time
    from alpaca_mcp_server.tools.peak_trough_analysis_tool import analyze_peaks_and_troughs
    
    output = []
    output.append("=" * 60)
    output.append("⚡ Performance Comparison: C vs Python")
    output.append("=" * 60)
    output.append(f"Symbol: {symbol}, Timeframe: {timeframe}, Days: {days}")
    output.append("-" * 60)
    
    # Test C implementation
    start_c = time.time()
    c_result = await analyze_peaks_troughs_fast(symbol, timeframe, days)
    c_time = time.time() - start_c
    
    # Test Python implementation
    start_py = time.time()
    py_result = await analyze_peaks_and_troughs(symbol, timeframe, days)
    py_time = time.time() - start_py
    
    # Calculate speedup
    speedup = py_time / c_time if c_time > 0 else float('inf')
    
    output.append(f"\n📊 Results:")
    output.append(f"  • C Implementation: {c_time:.3f} seconds")
    output.append(f"  • Python Implementation: {py_time:.3f} seconds")
    output.append(f"  • Speedup: {speedup:.1f}x faster with C")
    
    # Verify both got results
    c_has_signals = "Trading Signals" in c_result or "SIGNAL" in c_result.upper()
    py_has_signals = "Trading Signal" in py_result or "Peak" in py_result or "Trough" in py_result
    
    output.append(f"\n✅ Validation:")
    output.append(f"  • C found signals: {'Yes' if c_has_signals else 'No'}")
    output.append(f"  • Python found signals: {'Yes' if py_has_signals else 'No'}")
    
    output.append("\n" + "=" * 60)
    
    return "\n".join(output)


# Tool metadata for MCP registration
TOOL_METADATA = {
    "name": "analyze_peaks_troughs_fast",
    "description": "Ultra-fast peak/trough analysis using C implementation (5-10x faster)",
    "parameters": {
        "symbols": "Comma-separated symbols or AUTO for scanner results",
        "timeframe": "Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)",
        "days": "Number of trading days (1-30)",
        "window_len": "Hanning filter window length (3-101, odd)",
        "filter_key": "Data field to filter (close, open, high, low, vwap)",
        "feed": "Data feed source (sip, iex, otc)",
    }
}