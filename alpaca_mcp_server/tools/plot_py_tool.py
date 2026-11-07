"""Peak/trough stock charts as an MCP tool: interactive ECharts HTML plus a PNG.

Formerly a wrapper that shelled out to the matplotlib script plot.py and opened
every PNG in an ImageMagick `display` window. The analysis (zero-phase Hanning
filter + peak detection) is unchanged; rendering moved to tools/echart_plot.py,
and nothing opens on screen unless the caller asks for it.
"""

import logging
import os
import webbrowser
from pathlib import Path

from ..config import get_technical_config
from ..utils.timezone_utils import now_et
from .echart_plot import fetch_chart_data, plot_dir, render_html, render_png

logger = logging.getLogger(__name__)

MAX_SYMBOLS = 10  # past this an overlay cannot keep a validated colour per line
_MODES = ("single", "combined", "overlay", "all")


def _max_days(timeframe: str) -> int:
    if timeframe == "1Day":
        return 2520  # ~10 years
    if timeframe in ("1Hour", "2Hour", "4Hour"):
        return 90
    return 30  # intraday


async def generate_stock_plot(
    symbols: str,
    timeframe: str = "1Min",
    days: int = 1,
    window: int | None = None,
    lookahead: int | None = None,
    feed: str = "sip",
    no_plot: bool = False,
    verbose: bool = False,
    plot_mode: str = "single",
    open_in_browser: bool = False,
) -> str:
    """
    Generate interactive peak/trough charts (ECharts HTML) with a PNG snapshot.

    Each symbol gets a price panel (raw close, zero-phase Hanning filter, peaks ▼
    and troughs ▲ with the latest prices labelled) over a separate volume panel,
    with crosshair tooltip, zoom, dark/light toggle, ET time axis and a table view
    of every turning point. Uses the global config when window/lookahead are None.

    Args:
        symbols: Comma-separated symbols (e.g., "AAPL,MSFT,TSLA"), at most 10.
        timeframe: "1Min", "5Min", "15Min", "30Min", "1Hour", "1Day".
        days: Trading days (1-30 intraday, 1-90 hourly, 1-2520 daily).
        window: Hanning window length (3-101; even values are rounded up to odd).
        lookahead: Peak detection lookahead (1-50).
        feed: Market-data feed, "sip" (default) or "boats" (overnight session).
        no_plot: Analysis text only; write no chart files.
        verbose: Accepted for compatibility; logging follows the server's level.
        plot_mode: "single" (one chart file per symbol), "combined" (all symbols
            on one page), "overlay" (symbols indexed to % change on one axis),
            or "all".
        open_in_browser: Open the HTML in the default browser (default False).

    Returns:
        Analysis summary, signal levels and the paths of the HTML and PNG files.
    """
    del verbose  # logging level is the server's
    try:
        tech_config = get_technical_config()
        if window is None:
            window = tech_config.hanning_window_samples
        if lookahead is None:
            lookahead = tech_config.peak_trough_lookahead

        max_days = _max_days(timeframe)
        if days < 1 or days > max_days:
            return f"❌ Days must be between 1 and {max_days} for {timeframe} timeframe"
        if window < 3 or window > 101:
            return "❌ Window length must be between 3 and 101"
        if window % 2 == 0:
            window += 1
            logger.info("Window length adjusted to %s (must be odd)", window)
        if lookahead < 1 or lookahead > 50:
            return "❌ Lookahead must be between 1 and 50"
        if plot_mode not in _MODES:
            return f"❌ plot_mode must be one of: {', '.join(_MODES)}"
        feed = feed.lower()
        if feed not in ("sip", "boats"):
            return (
                "❌ feed must be 'sip' or 'boats' (SIP is the consolidated tape; IEX is not used)"
            )

        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            return "❌ No valid symbols provided"
        if len(symbol_list) > MAX_SYMBOLS:
            return f"❌ Maximum {MAX_SYMBOLS} symbols allowed"

        api_key = os.environ.get("APCA_API_KEY_ID")
        api_secret = os.environ.get("APCA_API_SECRET_KEY")
        if not api_key or not api_secret:
            return (
                "\n❌ API CREDENTIALS NOT CONFIGURED\n\n"
                "The server reads them from ~/.secrets (APCA_API_KEY_ID / APCA_API_SECRET_KEY).\n"
                f"Current paper trading status: {os.environ.get('PAPER', 'Not set')}"
            )

        data = await fetch_chart_data(
            symbol_list, timeframe, days, window, lookahead, feed, api_key, api_secret
        )
    except Exception as e:
        logger.exception("plot generation failed")
        return f"❌ PLOT GENERATION FAILED\n\nError: {type(e).__name__}: {e}"

    found = [s for s, cd in data.items() if cd is not None]
    missing = [s for s, cd in data.items() if cd is None]

    files: list[str] = []
    png_notes: list[str] = []
    if not no_plot and found:
        out = plot_dir()
        stamp = now_et().strftime("%H%M%S")
        common = {
            "timeframe": timeframe,
            "days": days,
            "window": window,
            "lookahead": lookahead,
            "feed": feed,
        }
        pages: list[tuple[str, dict, bool, bool]] = []  # (name, data, symbol panels, overlay)
        if plot_mode in ("single", "all"):
            pages += [(f"{s}_{timeframe}_{stamp}", {s: data[s]}, True, False) for s in found]
        if plot_mode in ("combined", "all") and len(found) > 1:
            pages.append((f"combined_{'-'.join(found)}_{timeframe}_{stamp}", data, True, False))
        if plot_mode in ("overlay", "all") and len(found) > 1:
            pages.append((f"overlay_{'-'.join(found)}_{timeframe}_{stamp}", data, False, True))
        if not pages:  # combined/overlay with a single symbol
            pages = [(f"{found[0]}_{timeframe}_{stamp}", {found[0]: data[found[0]]}, True, False)]
        for name, page_data, panels, overlay in pages:
            html_path = out / f"{name}.html"
            html_path.write_text(
                render_html(page_data, symbol_panels=panels, overlay=overlay, **common),  # type: ignore[arg-type]
                encoding="utf-8",
            )
            files.append(str(html_path))
            png_path = html_path.with_suffix(".png")
            err = await render_png(html_path, png_path)
            if err is None:
                files.append(str(png_path))
            else:
                png_notes.append(f"{png_path.name}: {err}")
        if open_in_browser:
            webbrowser.open(Path(files[0]).as_uri())

    return _report(
        data,
        found,
        missing,
        files,
        png_notes,
        timeframe,
        days,
        window,
        lookahead,
        feed,
        plot_mode,
        no_plot,
    )


def _money(v: float) -> str:
    return f"${v:.4f}" if abs(v) < 1 else f"${v:,.2f}"


def _report(data, found, missing, files, png_notes, timeframe, days, window, lookahead, feed, plot_mode, no_plot) -> str:  # type: ignore[no-untyped-def]
    lines = [
        "",
        "📊 ANALYSIS COMPLETED:",
        f"• Symbols: {', '.join(found) if found else 'none with data'}",
        f"• Timeframe: {timeframe} over {days} trading day(s)",
        f"• Filter: Hanning window {window}, lookahead {lookahead}",
        f"• Feed: {feed.upper()}",
        f"• Plot mode: {plot_mode}",
    ]
    if missing:
        lines.append(f"• No bars returned for: {', '.join(missing)}")
    lines += ["", "📋 ANALYSIS SUMMARY:"]
    for s in found:
        a = data[s].analysis
        last = a.original_prices[-1]
        lines.append(
            f"• {s}: last {_money(last)}, range {_money(a.stats['price_min'])} – {_money(a.stats['price_max'])}, "
            f"{len(a.peaks)} peaks / {len(a.troughs)} troughs over {a.total_bars:,} bars"
        )
        turns = sorted(
            [("Peak", p) for p in a.peaks] + [("Trough", t) for t in a.troughs],
            key=lambda r: r[1].index,
        )
        if turns:
            kind, p = turns[-1]
            lines.append(
                f"    latest {kind.lower()} {_money(p.original_price)} "
                f"({a.total_bars - 1 - p.index} bars ago; now {(last / p.original_price - 1) * 100:+.2f}% from it)"
            )
    lines += ["", "📈 PLOTS GENERATED:"]
    if no_plot:
        lines.append("• none (no_plot=True)")
    elif files:
        lines += [f"• {f}" for f in files]
    else:
        lines.append("• none (no symbol returned data)")
    if png_notes:
        lines += ["", "⚠️ PNG snapshot skipped:"] + [f"• {n}" for n in png_notes]
    lines += [
        "",
        "✅ ANALYSIS COMPLETE — interactive ECharts HTML (open in a browser) + PNG snapshot",
    ]
    return "\n".join(lines)
