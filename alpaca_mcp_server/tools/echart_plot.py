"""Interactive ECharts peak/trough charts (HTML) with a headless PNG snapshot.

Replaces the matplotlib + ImageMagick pipeline (plot.py). Same analysis — the
zero-phase Hanning filter and peak detection of peak_trough_analysis_tool — drawn
with ECharts 5.5.0, the version bottom_barrel's Rust workbenches use, so every
chart in the toolchain shares one visual language.

Design (dataviz skill):
- Price and volume are separate panels on one shared time axis: never a dual
  y-axis. Overlay mode indexes every symbol to % change from its first bar, so
  several symbols share one honest axis.
- Categorical slots 1-4 of the reference palette, validated light and dark with
  validate_palette.js: price blue, filtered orange, peaks aqua (down triangle),
  troughs yellow (up triangle). Peaks and troughs also differ by shape and by
  label, so colour never carries the meaning alone. Light mode's aqua/yellow sit
  under 3:1 contrast, so the relief rule applies: visible direct labels on the
  latest turning points plus a full table view.
- Selective direct labels (the latest three peaks and troughs), crosshair
  tooltip, zoom, dark/light toggle, ET time axis, sub-dollar prices at 4 decimals.
- The PNG is rendered by headless Chrome through Playwright, so no window opens;
  it waits for ECharts' `finished` event before capturing.
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..utils.timezone_utils import fmt_et, now_et, to_et
from .peak_trough_analysis_tool import (
    HistoricalDataFetcher,
    SymbolAnalysisResult,
    process_bars_for_peaks,
)

logger = logging.getLogger(__name__)

ECHARTS_URL = "https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"
LABELLED_TURNS = 3  # direct-label only the most recent N peaks and N troughs


@dataclass
class ChartData:
    """One symbol's analysis plus what the chart needs beyond it."""

    analysis: SymbolAnalysisResult
    labels: list[str]  # ET "MM-DD HH:MM" per bar
    volumes: list[int]
    epochs: list[int]  # bar start, epoch seconds: aligns symbols on real time


def plot_dir() -> Path:
    """Where charts are written: ALPACA_PLOT_DIR, else <tmp>/alpaca_plots/<ET date>."""
    base = os.environ.get("ALPACA_PLOT_DIR") or os.path.join(tempfile.gettempdir(), "alpaca_plots")
    d = Path(base) / now_et().strftime("%Y-%m-%d")
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── data ─────────────────────────────────────────────────────────────────────


def _fetch_one(
    fetcher: HistoricalDataFetcher,
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
    feed: str,
    window: int,
    lookahead: int,
) -> ChartData | None:
    # One request per symbol: the bars endpoint's 10,000-bar limit is shared
    # across every symbol in a request, so a multi-symbol call truncates.
    bars_by_symbol = fetcher.fetch_historical_bars([symbol], timeframe, start, end, feed)
    bars = (bars_by_symbol or {}).get(symbol) or []
    if not bars:
        return None
    analysis = process_bars_for_peaks(symbol, bars, window_len=window, lookahead=lookahead)
    if analysis is None:
        return None
    labels = [fmt_et(b["t"], "%m-%d %H:%M") for b in bars]
    volumes = [int(b.get("v", 0)) for b in bars]
    epochs = [int(to_et(b["t"]).timestamp()) for b in bars]
    return ChartData(analysis=analysis, labels=labels, volumes=volumes, epochs=epochs)


async def fetch_chart_data(
    symbols: list[str],
    timeframe: str,
    days: int,
    window: int,
    lookahead: int,
    feed: str,
    api_key: str,
    api_secret: str,
) -> dict[str, ChartData | None]:
    """Fetch and analyse each symbol in a worker thread (the fetcher is blocking)."""
    fetcher = HistoricalDataFetcher(api_key, api_secret)
    trading_days = await asyncio.to_thread(fetcher.get_trading_days, days)
    if not trading_days:
        raise RuntimeError("no trading days resolved from the market calendar")
    start, end = trading_days[-1], trading_days[0]
    results = await asyncio.gather(
        *(
            asyncio.to_thread(_fetch_one, fetcher, s, timeframe, start, end, feed, window, lookahead)
            for s in symbols
        )
    )
    return dict(zip(symbols, results, strict=True))


# ── html ─────────────────────────────────────────────────────────────────────

_CSS = """
:root { color-scheme: light;
  --page:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --ring:rgba(11,11,11,0.10);
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4; --s6:#008300; --s7:#6250d6; --s8:#e34948; }
@media (prefers-color-scheme: dark) { :root:where(:not([data-theme="light"])) { color-scheme: dark;
  --page:#0d0d0d; --surface:#1a1a19; --ink:#f0efec; --ink-2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --ring:rgba(255,255,255,0.10);
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767; } }
:root[data-theme="dark"] { color-scheme: dark;
  --page:#0d0d0d; --surface:#1a1a19; --ink:#f0efec; --ink-2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --ring:rgba(255,255,255,0.10);
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767; }
* { box-sizing: border-box; }
body { margin:0; background:var(--page); color:var(--ink);
  font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1400px; margin: 0 auto; padding: 20px 16px 40px; }
header.top { display:flex; align-items:baseline; justify-content:space-between; gap:12px; flex-wrap:wrap; }
h1 { font-size: 20px; margin: 0; font-weight: 600; }
.meta { color: var(--ink-2); font-size: 13px; }
button.theme { font: inherit; font-size: 13px; color: var(--ink-2); background: var(--surface);
  border: 1px solid var(--ring); border-radius: 6px; padding: 4px 10px; cursor: pointer; }
section.card { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px;
  padding: 14px 14px 6px; margin-top: 16px; }
.card h2 { font-size: 16px; margin: 0 0 2px; font-weight: 600; }
.stats { color: var(--ink-2); font-size: 13px; display: flex; gap: 18px; flex-wrap: wrap; }
.stats b { color: var(--ink); font-weight: 600; }
.chart { width: 100%; height: 560px; }
.chart.overlay { height: 460px; }
details { margin: 4px 0 10px; } summary { cursor: pointer; color: var(--ink-2); font-size: 13px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 6px; }
th, td { padding: 4px 10px; border-bottom: 1px solid var(--grid); text-align: left; }
th.n, td.n { text-align: right; font-variant-numeric: tabular-nums; }
th { color: var(--ink-2); font-weight: 600; }
.peak { color: var(--ink); } .trough { color: var(--ink); }
.empty { color: var(--muted); padding: 24px 0; }
"""

_JS = r"""
const DATA = __DATA__;
const MODE = __MODE__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const px = v => (v == null || isNaN(v)) ? '' : (Math.abs(v) < 1 ? '$' + v.toFixed(4) : '$' + v.toFixed(2));
const vol = v => v >= 1e6 ? (v / 1e6).toFixed(2) + 'M' : v >= 1e3 ? (v / 1e3).toFixed(1) + 'K' : String(v);
const DOWN = 'path://M0,0 L10,0 L5,9 Z', UP = 'path://M5,0 L10,9 L0,9 Z';
const charts = [];
let pending = 0;
function ready() { if (--pending <= 0) window.__chartsReady = true; }

function turnSeries(name, turns, color, symbol, labelPos, n) {
  const lastIdx = new Set(turns.slice(-LABELLED).map(t => t.index));
  // hideOverlap: a label that would collide is dropped (its value stays in the
  // tooltip and the table view) rather than overprinting its neighbour.
  return { name, type: 'scatter', xAxisIndex: 0, yAxisIndex: 0, z: 5, labelLayout: { hideOverlap: true },
    symbol, symbolSize: 11,
    itemStyle: { color, borderColor: css('--surface'), borderWidth: 2 },
    data: turns.map(t => ({ value: [t.index, t.price],
      label: { show: lastIdx.has(t.index), position: labelPos, color: css('--ink'),
               fontSize: 11, formatter: () => px(t.price) } })) };
}

function symbolOption(d) {
  const n = d.labels.length;
  return {
    animation: false, backgroundColor: 'transparent',
    textStyle: { fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif', color: css('--ink-2') },
    legend: { top: 0, left: 0, textStyle: { color: css('--ink-2') }, itemWidth: 16, itemHeight: 8,
      data: ['Price', 'Filtered (Hanning ' + d.window + ')', { name: 'Peak', icon: DOWN }, { name: 'Trough', icon: UP }] },
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross', lineStyle: { color: css('--axis') } },
      backgroundColor: css('--surface'), borderColor: css('--ring'), textStyle: { color: css('--ink') },
      formatter: ps => {
        const i = ps[0].dataIndex, lines = [d.labels[i] + ' ET'];
        lines.push('Price ' + px(d.close[i]), 'Filtered ' + px(d.filtered[i]), 'Volume ' + vol(d.volume[i]));
        if (d.peakAt[i] !== undefined) lines.push('▼ Peak ' + px(d.peakAt[i]));
        if (d.troughAt[i] !== undefined) lines.push('▲ Trough ' + px(d.troughAt[i]));
        return lines.join('<br>');
      } },
    grid: [{ left: 72, right: 24, top: 56, height: '54%' }, { left: 72, right: 24, top: '73%', height: '15%' }],
    xAxis: [0, 1].map(g => ({ type: 'category', gridIndex: g, data: d.labels, boundaryGap: g === 1,
      axisLine: { lineStyle: { color: css('--axis') } }, axisTick: { show: false },
      axisLabel: { show: g === 1, color: css('--muted'), hideOverlap: true },
      splitLine: { show: false } })),
    yAxis: [
      { gridIndex: 0, scale: true,
        axisLabel: { color: css('--muted'), formatter: px }, axisLine: { show: false },
        splitLine: { lineStyle: { color: css('--grid'), width: 1 } } },
      { gridIndex: 1, name: 'Volume', nameLocation: 'end', nameGap: 6,
        nameTextStyle: { color: css('--muted'), align: 'left', padding: [0, 0, 0, -56] },
        splitNumber: 2, axisLabel: { color: css('--muted'), formatter: vol }, axisLine: { show: false },
        splitLine: { lineStyle: { color: css('--grid'), width: 1 } } } ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, 1] },
      { type: 'slider', xAxisIndex: [0, 1], bottom: 6, height: 18, borderColor: css('--ring'),
        textStyle: { color: css('--muted') }, fillerColor: 'rgba(128,128,128,0.12)' }],
    series: [
      { name: 'Price', type: 'line', data: d.close, showSymbol: false, xAxisIndex: 0, yAxisIndex: 0,
        lineStyle: { width: 1.5, color: css('--s1') }, itemStyle: { color: css('--s1') } },
      { name: 'Filtered (Hanning ' + d.window + ')', type: 'line', data: d.filtered, showSymbol: false,
        xAxisIndex: 0, yAxisIndex: 0, lineStyle: { width: 2, color: css('--s2') }, itemStyle: { color: css('--s2') } },
      turnSeries('Peak', d.peaks, css('--s3'), DOWN, 'top', n),
      turnSeries('Trough', d.troughs, css('--s4'), UP, 'bottom', n),
      { name: 'Volume', type: 'bar', data: d.volume, xAxisIndex: 1, yAxisIndex: 1, barCategoryGap: '20%',
        itemStyle: { color: css('--muted'), borderRadius: [2, 2, 0, 0] } } ] };
}

function overlayOption(list) {
  const slots = ['--s1', '--s2', '--s3', '--s4', '--s5', '--s6', '--s7', '--s8'];
  // Align on real time: the category axis is the union of every symbol's bar times.
  // (Indexing each series by its own bar number squeezed a thin trader like SNTI
  // into the first third of a busier symbol's axis.)
  const label = {}; list.forEach(d => d.epochs.forEach((e, i) => { label[e] = d.labels[i]; }));
  const grid = Object.keys(label).map(Number).sort((a, b) => a - b);
  const pos = new Map(grid.map((e, i) => [e, i]));
  return {
    animation: false, backgroundColor: 'transparent',
    textStyle: { fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif', color: css('--ink-2') },
    legend: { top: 0, left: 0, textStyle: { color: css('--ink-2') } },
    tooltip: { trigger: 'axis', backgroundColor: css('--surface'), borderColor: css('--ring'),
      textStyle: { color: css('--ink') }, valueFormatter: v => (v == null ? '' : (v >= 0 ? '+' : '') + v.toFixed(2) + '%') },
    grid: { left: 64, right: 80, top: 44, bottom: 48 },
    xAxis: { type: 'category', data: grid.map(e => label[e]), axisLine: { lineStyle: { color: css('--axis') } },
      axisTick: { show: false }, axisLabel: { color: css('--muted'), hideOverlap: true } },
    yAxis: { axisLabel: { color: css('--muted'), formatter: v => v + '%' }, axisLine: { show: false },
      splitLine: { lineStyle: { color: css('--grid') } } },
    dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 6, height: 18, borderColor: css('--ring') }],
    series: list.map((d, k) => ({ name: d.symbol, type: 'line', showSymbol: false, connectNulls: true,
      data: (() => { const row = new Array(grid.length).fill(null);
        d.close.forEach((c, i) => { row[pos.get(d.epochs[i])] = (c / d.close[0] - 1) * 100; }); return row; })(),
      lineStyle: { width: 2, color: css(slots[k]) }, itemStyle: { color: css(slots[k]) },
      endLabel: { show: true, color: css('--ink'), formatter: p => d.symbol } })) };
}

function draw() {
  charts.forEach(c => c.dispose()); charts.length = 0;
  const targets = [];
  if (MODE.overlay) targets.push(['chart-overlay', overlayOption(DATA)]);
  if (MODE.symbols) DATA.forEach(d => targets.push(['chart-' + d.symbol, symbolOption(d)]));
  pending = targets.length; window.__chartsReady = targets.length === 0;
  for (const [id, opt] of targets) {
    const el = document.getElementById(id); if (!el) { ready(); continue; }
    const c = echarts.init(el, null, { renderer: 'canvas' });
    c.on('finished', function once() { c.off('finished', once); ready(); });
    c.setOption(opt); charts.push(c);
  }
}
const LABELLED = __LABELLED__;
document.querySelector('button.theme').addEventListener('click', () => {
  const root = document.documentElement;
  const dark = root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  root.dataset.theme = dark ? 'light' : 'dark'; draw();
});
addEventListener('resize', () => charts.forEach(c => c.resize()));
draw();
"""


def _payload(cd: ChartData) -> dict:
    a = cd.analysis

    def turns(points: list) -> list[dict]:
        return [{"index": p.index, "price": p.original_price} for p in points]

    return {
        "symbol": a.symbol,
        "window": a.filter_params.get("window_len"),
        "labels": cd.labels,
        "epochs": cd.epochs,
        "close": a.original_prices,
        "filtered": [round(v, 6) for v in a.filtered_prices],
        "volume": cd.volumes,
        "peaks": turns(a.peaks),
        "troughs": turns(a.troughs),
        "peakAt": {p.index: p.original_price for p in a.peaks},
        "troughAt": {t.index: t.original_price for t in a.troughs},
    }


def _money(v: float) -> str:
    return f"${v:.4f}" if abs(v) < 1 else f"${v:,.2f}"


def _table(cd: ChartData) -> str:
    a = cd.analysis
    rows = sorted(
        [("▼ Peak", p) for p in a.peaks] + [("▲ Trough", t) for t in a.troughs],
        key=lambda r: r[1].index,
    )
    body = "".join(
        f"<tr><td>{kind}</td><td>{html.escape(cd.labels[p.index])} ET</td>"
        f'<td class="n">{_money(p.original_price)}</td><td class="n">{_money(p.filtered_price)}</td>'
        f'<td class="n">{p.volume:,}</td><td class="n">{a.total_bars - 1 - p.index}</td></tr>'
        for kind, p in rows
    )
    return (
        "<details><summary>Table view — every peak and trough</summary><table>"
        '<thead><tr><th>Signal</th><th>Time</th><th class="n">Price</th>'
        '<th class="n">Filtered</th><th class="n">Volume</th><th class="n">Bars ago</th></tr></thead>'
        f"<tbody>{body}</tbody></table></details>"
    )


def render_html(
    data: dict[str, ChartData | None],
    *,
    timeframe: str,
    days: int,
    window: int,
    lookahead: int,
    feed: str,
    symbol_panels: bool = True,
    overlay: bool = False,
) -> str:
    """The complete, self-contained chart page."""
    ok = {s: cd for s, cd in data.items() if cd is not None}
    title = (" ".join(list(ok)[:3]) or "No data") + " Peaks"
    cards = []
    if overlay and len(ok) > 1:
        cards.append(
            '<section class="card"><h2>Relative performance</h2>'
            '<div class="stats">Each symbol indexed to % change from its first bar — one shared axis.</div>'
            '<div id="chart-overlay" class="chart overlay"></div></section>'
        )
    if symbol_panels or not overlay or len(ok) < 2:
        for sym, cd in data.items():
            if cd is None:
                cards.append(
                    f'<section class="card"><h2>{html.escape(sym)}</h2>'
                    '<div class="empty">No bars returned for this symbol and window.</div></section>'
                )
                continue
            a = cd.analysis
            last = a.original_prices[-1]
            first = a.original_prices[0]
            chg = (last / first - 1) * 100 if first else 0.0
            cards.append(
                f'<section class="card"><h2>{html.escape(sym)}</h2><div class="stats">'
                f"<span>Last <b>{_money(last)}</b></span><span>Window change <b>{chg:+.2f}%</b></span>"
                f"<span>Range <b>{_money(a.stats['price_min'])} – {_money(a.stats['price_max'])}</b></span>"
                f"<span>Peaks <b>{len(a.peaks)}</b></span><span>Troughs <b>{len(a.troughs)}</b></span>"
                f"<span>Bars <b>{a.total_bars:,}</b></span></div>"
                f'<div id="chart-{html.escape(sym)}" class="chart"></div>{_table(cd)}</section>'
            )
    payload = json.dumps([_payload(cd) for cd in ok.values()], separators=(",", ":"))
    mode = json.dumps(
        {"overlay": bool(overlay and len(ok) > 1), "symbols": bool(symbol_panels or not overlay or len(ok) < 2)}
    )
    js = (
        _JS.replace("__DATA__", payload.replace("</", "<\\/"))
        .replace("__MODE__", mode)
        .replace("__LABELLED__", str(LABELLED_TURNS))
    )
    meta = (
        f"{timeframe} bars · {days} trading day(s) · Hanning window {window} · lookahead {lookahead} · "
        f"{feed.upper()} · generated {fmt_et(None, '%Y-%m-%d %H:%M %Z')}"
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>{_CSS}</style>"
        f'<script src="{ECHARTS_URL}"></script></head><body><main>'
        f'<header class="top"><div><h1>Peak / trough analysis</h1><div class="meta">{html.escape(meta)}</div></div>'
        '<button class="theme" type="button">Toggle dark / light</button></header>'
        f"{''.join(cards)}</main><script>{js}</script></body></html>"
    )


# ── png ──────────────────────────────────────────────────────────────────────


async def render_png(html_path: Path, png_path: Path, *, dark: bool = True, width: int = 1400) -> str | None:
    """Screenshot the page headlessly. Returns an error string, or None on success."""
    if os.environ.get("ALPACA_PLOT_PNG", "1").lower() in ("0", "false", "no"):
        return "PNG rendering disabled (ALPACA_PLOT_PNG=0)"
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return "playwright not installed"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(channel="chrome", headless=True)
            try:
                page = await browser.new_page(
                    viewport={"width": width, "height": 900},
                    color_scheme="dark" if dark else "light",
                    device_scale_factor=2,
                )
                await page.goto(html_path.as_uri(), wait_until="load", timeout=30_000)
                await page.wait_for_function("window.__chartsReady === true", timeout=30_000)
                await page.screenshot(path=str(png_path), full_page=True)
            finally:
                await browser.close()
    except Exception as e:  # browser missing, CDN unreachable, render timeout
        return f"{type(e).__name__}: {e}"
    return None
