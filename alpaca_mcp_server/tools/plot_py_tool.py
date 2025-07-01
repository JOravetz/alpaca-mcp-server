"""
Plot.py MCP Tool Integration
Registers the standalone plot.py script as an MCP tool with proper ImageMagick display.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path to import plot.py
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import global configuration
from ..config import get_technical_config

logger = logging.getLogger(__name__)


async def generate_stock_plot(
    symbols: str,
    timeframe: str = "1Min",
    days: int = 1,
    window: int = None,
    lookahead: int = None,
    feed: str = "sip",
    no_plot: bool = False,
    verbose: bool = False,
) -> str:
    """
    Generate stock analysis plots using the plot.py script with ImageMagick display.

    This tool integrates the standalone plot.py script as an MCP tool, providing
    professional technical analysis plots with automatic ImageMagick display.

    Features:
    - Zero-phase Hanning filtering for noise reduction
    - Peak/trough detection with precise price annotations
    - Real-time market data from Alpaca API
    - Professional styling with NYC/EDT timezone
    - Automatic plot display via ImageMagick
    - Multi-symbol support in single API call

    Args:
        symbols: Comma-separated stock symbols (e.g., "AAPL,MSFT,TSLA")
        timeframe: Bar timeframe - "1Min", "5Min", "15Min", "30Min", "1Hour", "1Day"
        days: Number of trading days to analyze (1-30 for intraday, 1-2520 for daily)
        window: Hanning filter window length (3-101, must be odd)
        lookahead: Peak detection sensitivity (1-50, higher = more sensitive)
        feed: Data feed - "sip", "iex", or "otc"
        no_plot: Skip plotting and only show analysis (useful for batch processing)
        verbose: Enable detailed logging output

    Returns:
        Comprehensive analysis results with plot locations and trading signals
    """

    try:
        # Load global config defaults for None parameters
        tech_config = get_technical_config()
        if window is None:
            window = tech_config.hanning_window_samples
        if lookahead is None:
            lookahead = tech_config.peak_trough_lookahead

        # Validate parameters - timeframe-aware limits
        if timeframe == "1Day":
            max_days = 2520  # ~10 years for daily analysis
        elif timeframe in ["1Hour", "2Hour", "4Hour"]:
            max_days = 90  # 3 months for hourly
        else:  # Intraday timeframes (1Min, 5Min, etc.)
            max_days = 30  # Current limit for intraday

        if days < 1 or days > max_days:
            return f"❌ Days must be between 1 and {max_days} for {timeframe} timeframe"

        if window < 3 or window > 101:
            return "❌ Window length must be between 3 and 101"

        if window % 2 == 0:
            window += 1
            logger.info(f"Window length adjusted to {window} (must be odd)")

        if lookahead < 1 or lookahead > 50:
            return "❌ Lookahead must be between 1 and 50"

        # Parse and validate symbols
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            return "❌ No valid symbols provided"

        if len(symbol_list) > 20:
            return "❌ Maximum 20 symbols allowed"

        # Check API credentials
        api_key = os.environ.get("APCA_API_KEY_ID")
        api_secret = os.environ.get("APCA_API_SECRET_KEY")

        if not api_key or not api_secret:
            return """
❌ API CREDENTIALS NOT CONFIGURED

Please set environment variables:
• APCA_API_KEY_ID
• APCA_API_SECRET_KEY

Current paper trading status: """ + str(
                os.environ.get("PAPER", "Not set")
            )

        # Construct command for plot.py script
        plot_script = Path(__file__).parent / "plot.py"
        if not plot_script.exists():
            return f"❌ Plot script not found at {plot_script}"

        cmd = [
            "python",
            str(plot_script),
            "--symbols",
            symbols,
            "--timeframe",
            timeframe,
            "--days",
            str(days),
            "--window",
            str(window),
            "--lookahead",
            str(lookahead),
            "--feed",
            feed,
        ]

        if no_plot:
            cmd.append("--no-plot")

        if verbose:
            cmd.append("--verbose")

        logger.info(f"Executing plot.py with command: {' '.join(cmd)}")

        # Execute plot.py script asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=dict(os.environ),  # Pass current environment including API keys
        )

        stdout, stderr = await process.communicate()

        # Decode output
        stdout_text = stdout.decode("utf-8") if stdout else ""
        stderr_text = stderr.decode("utf-8") if stderr else ""

        # Check for errors
        if process.returncode != 0:
            error_info = f"""
❌ PLOT GENERATION FAILED

Return code: {process.returncode}

STDOUT:
{stdout_text}

STDERR:
{stderr_text}

🔧 TROUBLESHOOTING:
1. Verify API credentials are properly set
2. Check symbol validity (try with just "AAPL")
3. Ensure plot.py script has proper dependencies
4. Try with --verbose flag for detailed logging
5. Check if market data is available for selected timeframe

💡 FALLBACK:
Use get_stock_peak_trough_analysis() for text-based analysis
            """
            return error_info

        # Parse output for plot information
        plot_files_generated = []
        temp_dir = ""

        for line in stdout_text.split("\n"):
            if "Plot generated and displayed:" in line:
                plot_file = line.split(":")[-1].strip()
                plot_files_generated.append(plot_file)
            elif "Generated" in line and "plots in:" in line:
                temp_dir = line.split(":")[-1].strip()

        # Generate success response
        symbol_count = len(symbol_list)
        plot_count = len(plot_files_generated)

        success_msg = f"""
🎯 STOCK PLOT GENERATION SUCCESSFUL

📊 ANALYSIS COMPLETED:
• Symbols processed: {symbol_count}
• Timeframe: {timeframe} over {days} trading day(s)
• Filter: Zero-phase Hanning window (length={window})
• Peak sensitivity: Lookahead={lookahead}
• Data feed: {feed}

📈 PLOTS GENERATED:
• Plot files created: {plot_count}
• Auto-display: ✅ ImageMagick (background windows)
• Output directory: {temp_dir or 'Temporary directory'}

📁 PLOT FILES:
{chr(10).join(f"• {os.path.basename(f)}" for f in plot_files_generated)}

📋 ANALYSIS OUTPUT:
{stdout_text}

💡 PLOT FEATURES:
• Original and filtered price data visualization
• Peak/trough detection with price annotations
• Professional styling with NYC/EDT timezone
• Support/resistance level identification
• Statistical summary and trading signals

🔍 NEXT STEPS:
• Review plots for visual confirmation of levels
• Use identified peaks/troughs for entry/exit planning
• Set price alerts at key support/resistance levels
• Integrate with real-time streaming for live validation

✅ PROFESSIONAL TECHNICAL ANALYSIS WITH IMAGEMAGICK DISPLAY COMPLETE!
        """

        # Include any stderr warnings if present (but not errors)
        if stderr_text and "warning" in stderr_text.lower():
            success_msg += f"\n\n⚠️  WARNINGS:\n{stderr_text}"

        return success_msg

    except FileNotFoundError as e:
        return f"""
❌ SCRIPT EXECUTION ERROR

Could not execute plot.py script: {e}

🔧 TROUBLESHOOTING:
1. Ensure Python is available in PATH
2. Verify plot.py script exists at project root
3. Check file permissions on plot.py
4. Try running manually: python plot.py --help

SYSTEM INFO:
• Project root: {project_root}
• Plot script: {project_root / 'plot.py'}
• Current working directory: {os.getcwd()}
        """

    except Exception as e:
        return f"""
❌ UNEXPECTED ERROR

Error during plot generation: {str(e)}

🔧 TROUBLESHOOTING:
1. Check API credentials and connectivity
2. Verify symbol validity and market hours
3. Try with simpler parameters (single symbol, 1 day)
4. Enable verbose mode for detailed logging
5. Check system resources and dependencies

💡 FALLBACK OPTIONS:
• Use get_stock_peak_trough_analysis() for text analysis
• Try generate_advanced_technical_plots() alternative
• Use get_stock_bars_intraday() for raw data

PARAMETERS USED:
• Symbols: {symbols}
• Timeframe: {timeframe}
• Days: {days}
• Window: {window}
• Lookahead: {lookahead}
        """


# Export for MCP server registration
__all__ = ["generate_stock_plot"]
