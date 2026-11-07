"""Advanced peak/trough plots: the MCP entry point over tools/echart_plot.py.

Formerly matplotlib + ImageMagick (see backup/advanced_plotting_tool.py.pre-echarts-20261107).
Charts are now interactive ECharts HTML with a headless PNG snapshot, rendered by
plot_py_tool.generate_stock_plot; this module keeps the advanced tool's signature.
"""

from ..config import get_technical_config
from .plot_py_tool import generate_stock_plot


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
    Generate peak/trough analysis charts for one or more symbols.

    Each chart shows raw close, the zero-phase Hanning filter, peaks (▼) and
    troughs (▲) with the latest prices labelled, and volume in its own panel,
    as interactive ECharts HTML plus a PNG snapshot.

    Args:
        symbols: Comma-separated symbols (e.g., "AAPL,MSFT,TSLA"), at most 10.
        timeframe: Bar timeframe ("1Min", "5Min", "15Min", "30Min", "1Hour", "1Day").
        days: Number of trading days (1-30 intraday).
        window_len: Hanning window length (3-101). Uses the global config if None.
        lookahead: Peak detection lookahead (1-50). Uses the global config if None.
        plot_mode: "single", "combined", "overlay", or "all".
        save_plots: False returns the analysis without writing chart files.
        display_plots: Open the HTML chart in the default browser (default False).
        dpi: Accepted for compatibility; the PNG renders at 2x device scale.

    Returns:
        Analysis results with chart file paths and signal summary.
    """
    del dpi  # resolution is fixed at 2x device scale
    tech_config = get_technical_config()
    if window_len is None:
        window_len = tech_config.hanning_window_samples
    if lookahead is None:
        lookahead = tech_config.peak_trough_lookahead

    result = await generate_stock_plot(
        symbols=symbols,
        timeframe=timeframe,
        days=days,
        window=window_len,
        lookahead=lookahead,
        feed="sip",
        no_plot=not save_plots,
        plot_mode=plot_mode,
        open_in_browser=display_plots,
    )
    return f"\n🎯 ADVANCED TECHNICAL PLOTS\n{result}"


# Alias kept for callers and tests
generate_peak_trough_plots = generate_peak_trough_plots_fixed

__all__ = ["generate_peak_trough_plots", "generate_peak_trough_plots_fixed"]
