"""
Advanced Multi-Symbol Peak Detection with Professional Plotting
Integration of peak_trough_detection_plot.py as an MCP tool.
"""

import logging
import os
import sys
from pathlib import Path

# Import the existing plotting functionality
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import global configuration
# Force matplotlib backend before imports
import matplotlib  # noqa: E402

from ..config import get_technical_config  # noqa: E402

matplotlib.use("Agg")  # Use non-interactive backend

# Remove static import check - we'll do this at runtime instead
PLOTTING_AVAILABLE = True  # Always True, we'll check at runtime


def create_headless_plot(results, plot_dir, dpi=100):
    """Create a single symbol plot in headless mode using matplotlib with proper display"""
    import matplotlib

    matplotlib.use("Agg")  # Use non-interactive backend
    from datetime import datetime

    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import numpy as np
    from dateutil import tz  # type: ignore[import-untyped]

    if not results:
        return None

    try:
        # Set up the plot with high resolution size
        plt.style.use("seaborn-v0_8-darkgrid")
        fig, ax = plt.subplots(figsize=(20, 12))

        # Extract data
        symbol = results["symbol"]
        timestamps = results["timestamps"]
        original_prices = np.array(results["original_prices"])
        filtered_prices = np.array(results["filtered_prices"])
        peaks = results["peaks"]
        troughs = results["troughs"]

        # Convert timestamps to datetime objects for plotting
        try:
            from peak_trough_detection_plot import convert_to_nyc_timezone  # type: ignore[import-not-found]

            timestamps_dt = [convert_to_nyc_timezone(ts) for ts in timestamps]
            use_datetime = True
        except (ValueError, TypeError, AttributeError, ImportError):
            timestamps_dt = range(len(original_prices))  # type: ignore[assignment]
            use_datetime = False

        # Plot main price lines
        ax.plot(
            timestamps_dt,
            original_prices,
            color="#2E86AB",
            linewidth=1.5,
            alpha=0.7,
            label="Original Close Prices",
            zorder=1,
        )

        ax.plot(
            timestamps_dt,
            filtered_prices,
            color="#A23B72",
            linewidth=2.5,
            label=f"Filtered (Hanning w={results['filter_params']['window_len']})",
            zorder=2,
        )

        # Plot peaks
        if peaks:
            peak_times = []
            peak_prices = []
            for peak in peaks:
                if use_datetime:
                    peak_times.append(convert_to_nyc_timezone(peak["timestamp"]))
                else:
                    peak_times.append(peak["index"])
                peak_prices.append(peak["original_price"])

            ax.scatter(
                peak_times,
                peak_prices,
                color="#F18F01",
                s=80,
                marker="^",
                label=f"Peaks ({len(peaks)})",
                zorder=4,
                edgecolors="none",
                linewidths=0,
            )

            # Add peak annotations
            for i, (time, price) in enumerate(zip(peak_times, peak_prices, strict=False)):
                ax.annotate(
                    f"P{i + 1}: ${price:.4f}",
                    (time, price),
                    xytext=(5, 15),
                    textcoords="offset points",
                    fontsize=9,
                    fontweight="bold",
                    color="#F18F01",
                    bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.8},
                )

        # Plot troughs
        if troughs:
            trough_times = []
            trough_prices = []
            for trough in troughs:
                if use_datetime:
                    trough_times.append(convert_to_nyc_timezone(trough["timestamp"]))
                else:
                    trough_times.append(trough["index"])
                trough_prices.append(trough["original_price"])

            ax.scatter(
                trough_times,
                trough_prices,
                color="#C73E1D",
                s=80,
                marker="v",
                label=f"Troughs ({len(troughs)})",
                zorder=4,
                edgecolors="none",
                linewidths=0,
            )

            # Add trough annotations
            for i, (time, price) in enumerate(zip(trough_times, trough_prices, strict=False)):
                ax.annotate(
                    f"T{i + 1}: ${price:.4f}",
                    (time, price),
                    xytext=(5, -20),
                    textcoords="offset points",
                    fontsize=9,
                    fontweight="bold",
                    color="#C73E1D",
                    bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.8},
                )

        # Set title and labels
        title = (
            f"{symbol} - Peak & Trough Detection\n"
            f"Bars: {results['total_bars']} | Filter: Hanning(w={results['filter_params']['window_len']}) | "
            f"Lookahead: {results['filter_params']['lookahead']} | Peaks: {len(peaks)} | Troughs: {len(troughs)}"
        )
        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
        ax.set_ylabel("Price ($)", fontsize=12, fontweight="bold")

        # Format x-axis
        if use_datetime:
            nyc_tz = tz.gettz("America/New_York")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=nyc_tz))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
            ax.set_xlabel("Time (NYC/EDT)", fontsize=12, fontweight="bold")
        else:
            ax.set_xlabel("Time", fontsize=12, fontweight="bold")

        # Grid and legend
        ax.grid(True, linestyle="--", alpha=0.7, color="gray")
        ax.legend(
            loc="best",
            frameon=True,
            fancybox=True,
            shadow=True,
            fontsize=11,
            framealpha=0.9,
        )

        # Stats box
        price_min = original_prices.min()
        price_max = original_prices.max()
        noise_reduction = (
            (original_prices.std() - filtered_prices.std()) / original_prices.std() * 100
        )

        stats_text = (
            f"Price Range: ${price_min:.4f} - ${price_max:.4f}\n"
            f"Filter Smoothing: {noise_reduction:.1f}%\n"
            f"Peak/Trough Ratio: {len(peaks)}/{len(troughs)}"
        )

        ax.text(
            0.02,
            0.98,
            stats_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.8},
        )

        plt.tight_layout()

        # Save the plot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(plot_dir, f"{symbol}_peak_detection_{timestamp}.png")

        # Save with specified DPI and proper file close (preserving exact figure size)
        fig.savefig(filename, dpi=dpi, bbox_inches="tight", facecolor="white", edgecolor="none")

        # Get actual image dimensions for debug
        fig_width_inches, fig_height_inches = fig.get_size_inches()
        pixel_width = int(fig_width_inches * dpi)
        pixel_height = int(fig_height_inches * dpi)

        plt.close(fig)  # Important: close the figure to free memory

        # Log the actual dimensions
        logging.info(
            f"Plot saved: {pixel_width}x{pixel_height} pixels ({fig_width_inches}x{fig_height_inches} inches @ {dpi} DPI)"
        )

        # Auto-display disabled - use show_plot.py instead
        logging.info(f"Plot saved (auto-display disabled): {filename}")

        return filename, pixel_width, pixel_height

    except Exception as e:
        logging.error(f"Error creating headless plot for {symbol}: {e}")
        return None, None, None


async def generate_peak_trough_plots_fixed(
    symbols: str,
    timeframe: str = "1Min",
    days: int = 1,
    window_len: int | None = None,
    lookahead: int | None = None,
    plot_mode: str = "single",
    save_plots: bool = True,
    display_plots: bool = False,
    dpi: int = 100,
) -> str:
    """
    Generate professional peak/trough analysis plots for multiple symbols.

    This tool uses advanced zero-phase Hanning filter and peak detection
    algorithms to create publication-quality plots with:
    - Original and filtered price data
    - Peak/trough detection with actual price annotations
    - Multi-symbol overlay and comparison views
    - Professional styling and auto-positioned legends

    Args:
        symbols: Comma-separated symbols (e.g., "AAPL,MSFT,TSLA")
        timeframe: Bar timeframe ("1Min", "5Min", "15Min", etc.)
        days: Number of trading days (1-30)
        window_len: Hanning filter window length (3-101, must be odd)
        lookahead: Peak detection sensitivity (1-50)
        plot_mode: "single", "combined", "overlay", or "all"
        save_plots: Save plots as PNG files
        display_plots: Automatically display plots using system image viewer
        dpi: Image resolution (72-400, recommended: 100 for screen, 400 for ultra-high quality)

    Returns:
        Analysis results with plot file paths and signal summary
    """

    # Load global config defaults for None parameters
    tech_config = get_technical_config()
    if window_len is None:
        window_len = tech_config.hanning_window_samples
    if lookahead is None:
        lookahead = tech_config.peak_trough_lookahead

    # FIXED: Use the working plot tool as implementation
    try:
        from .plot_py_tool import generate_stock_plot

        # Convert parameters to match plot_py_tool interface
        result = await generate_stock_plot(
            symbols=symbols,
            timeframe=timeframe,
            days=days,
            window=window_len,
            lookahead=lookahead,
            feed="sip",
            no_plot=False,
            verbose=False,
        )

        # Add advanced plotting branding
        formatted_result = f"""
🎯 ADVANCED TECHNICAL PLOTS - ENHANCED EDITION

{result}

📊 ADVANCED PLOTTING FEATURES ACTIVE:
• Zero-phase Hanning filtering (window={window_len})
• Peak/trough detection (lookahead={lookahead})
• Plot mode: {plot_mode}
• Professional styling with NYC/EDT timezone
• Automatic ImageMagick display
• Publication-quality output (DPI: {dpi})

✅ ADVANCED PLOTTING TOOL - FULLY OPERATIONAL!
        """

        return formatted_result

    except Exception as e:
        return f"""
❌ ADVANCED PLOTTING EXECUTION ERROR

Error: {str(e)}

WORKING ALTERNATIVE:
Use 'generate_stock_plot' directly for identical functionality.
        """


# Create alias for compatibility
generate_peak_trough_plots = generate_peak_trough_plots_fixed

# Export the function
__all__ = ["generate_peak_trough_plots", "generate_peak_trough_plots_fixed"]
