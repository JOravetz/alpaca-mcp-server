"""
Perplexity Finance MCP Tools.

Thin formatting layer over the shared `perplexity_client` package, which
provides the curl_cffi-based REST client (TLS impersonation, no browser).
Replaces the prior cloudscraper + Camoufox subprocess implementation.
"""

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any

import pytz
from alpaca.data.enums import DataFeed

try:
    from perplexity_client import PerplexityClient
except ImportError:  # optional: the `perplexity` dependency group (a private repo)
    PerplexityClient = None  # type: ignore[assignment,misc]

_NOT_INSTALLED = (
    "Error: perplexity-client is not installed. It is the optional `perplexity`\n"
    "dependency group (a private repo); install it with `uv sync --group perplexity`."
)

from ..utils.feed_select import live_feed
from ..utils.timezone_utils import now_et
from ..utils.trading_calendar import latest_trading_day
from .freshness import freshness_cutoff, is_stale
from .market_data_tools import _px

# Perplexity's /rest/finance/quote endpoint serves the prior session's close
# (observed ~17h stale intraday). Anything older than this many seconds is
# flagged STALE so the operator never trades off a day-old price.
_PPLX_STALE_AFTER_S = 300


# ---------- Helpers ----------


def _normalize_alpaca_snapshot(
    symbol: str,
    snapshot: Any,
    live: Any = None,
    pre_market: bool = False,
    cutoff_epoch: int = 0,
) -> dict | None:
    """Build a normalized quote dict from an Alpaca snapshot (authoritative, real-time).

    *snapshot* is the SIP snapshot (daily and previous-day bars). *live*, when
    given, supplies the latest trade/quote instead (the BOATS snapshot during
    the overnight session). In *pre_market* the daily bar is still the last
    session's, so the change is measured from its close, as get_stock_snapshots
    does. A latest trade older than *cutoff_epoch* is flagged stale.
    """
    if snapshot is None:
        return None
    live = live if live is not None else snapshot
    latest_trade = getattr(live, "latest_trade", None) or getattr(snapshot, "latest_trade", None)
    latest_quote = getattr(live, "latest_quote", None) or getattr(snapshot, "latest_quote", None)
    daily_bar = getattr(snapshot, "daily_bar", None)
    prev_bar = getattr(snapshot, "previous_daily_bar", None)

    price = None
    if latest_trade is not None and getattr(latest_trade, "price", None):
        price = float(latest_trade.price)
    elif daily_bar is not None and getattr(daily_bar, "close", None):
        price = float(daily_bar.close)
    if not price:
        return None

    prev_close = (
        float(prev_bar.close) if prev_bar is not None and getattr(prev_bar, "close", None) else 0.0
    )
    if pre_market and daily_bar is not None and getattr(daily_bar, "close", None):
        prev_close = float(daily_bar.close)
    change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
    volume = (
        int(daily_bar.volume) if daily_bar is not None and getattr(daily_bar, "volume", None) else 0
    )
    day_low = (
        float(daily_bar.low) if daily_bar is not None and getattr(daily_bar, "low", None) else 0.0
    )
    day_high = (
        float(daily_bar.high) if daily_bar is not None and getattr(daily_bar, "high", None) else 0.0
    )
    bid = (
        float(latest_quote.bid_price)
        if latest_quote is not None and getattr(latest_quote, "bid_price", None)
        else 0.0
    )
    ask = (
        float(latest_quote.ask_price)
        if latest_quote is not None and getattr(latest_quote, "ask_price", None)
        else 0.0
    )

    as_of = ""
    ref_ts = getattr(latest_trade, "timestamp", None) or getattr(daily_bar, "timestamp", None)
    if ref_ts is not None:
        try:
            as_of = ref_ts.astimezone(pytz.timezone("America/New_York")).strftime(
                "%Y-%m-%d %H:%M:%S %Z"
            )
        except Exception:
            as_of = ""

    return {
        "source": "alpaca",
        "price": price,
        "change_pct": change_pct,
        "prev_close": prev_close,
        "volume": volume,
        "day_low": day_low,
        "day_high": day_high,
        "bid": bid,
        "ask": ask,
        "as_of": as_of,
        "stale": is_stale(ref_ts.isoformat() if ref_ts is not None else None, cutoff_epoch),
    }


def _normalize_pplx_quote(q: Any, now_epoch: float | None = None) -> dict | None:
    """Build a normalized quote dict from a Perplexity quote, flagging staleness."""
    if not isinstance(q, dict) or "error" in q:
        return None
    price = q.get("price")
    if not price:
        return None

    as_of = ""
    stale = False
    ts = q.get("timestamp")
    if isinstance(ts, int | float) and ts > 0:
        dt = datetime.fromtimestamp(ts, tz=UTC)
        as_of = dt.astimezone(pytz.timezone("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")
        now = now_epoch if now_epoch is not None else time.time()
        stale = (now - ts) > _PPLX_STALE_AFTER_S

    return {
        "source": "perplexity",
        "price": float(price),
        "change_pct": float(q.get("changesPercentage") or 0),
        "prev_close": float(q.get("previousClose") or 0),
        "volume": int(q.get("volume") or 0),
        "day_low": float(q.get("dayLow") or 0),
        "day_high": float(q.get("dayHigh") or 0),
        "bid": 0.0,
        "ask": 0.0,
        "as_of": as_of,
        "stale": stale,
    }


def _alpaca_realtime_quotes(symbol_list: list[str]) -> dict[str, dict]:
    """Fetch authoritative Alpaca real-time quotes for symbols. Empty dict on any failure."""
    try:
        from alpaca.data.requests import StockSnapshotRequest

        from ..config.settings import get_stock_historical_client

        client = get_stock_historical_client()
        # Bars always SIP; live prints from BOATS during the overnight session.
        snaps = client.get_stock_snapshot(
            StockSnapshotRequest(symbol_or_symbols=symbol_list, feed=DataFeed.SIP)
        )
        feed = live_feed()
        live_snaps = snaps
        if feed == DataFeed.BOATS:
            live_snaps = client.get_stock_snapshot(
                StockSnapshotRequest(symbol_or_symbols=symbol_list, feed=feed)
            )
        now = now_et()
        pre_market = (
            now.hour >= 4
            and (now.hour, now.minute) < (9, 30)
            and latest_trading_day() == now.date()
        )
        cutoff_epoch, _ = freshness_cutoff()
    except Exception:
        return {}
    out: dict[str, dict] = {}
    for sym in symbol_list:
        snap = (snaps or {}).get(sym)
        live = (live_snaps or {}).get(sym) if live_snaps is not snaps else None
        nq = _normalize_alpaca_snapshot(sym, snap, live, pre_market, cutoff_epoch)
        if nq is not None:
            out[sym] = nq
    return out


def _format_quote_block(nq: dict) -> list[str]:
    """Render a normalized quote dict into the QUOTE block lines."""
    src = "Alpaca real-time" if nq.get("source") == "alpaca" else "Perplexity"
    lines = ["", "QUOTE:", f"  Price:        {_px(nq['price'])} ({nq['change_pct']:+.2f}%)"]
    if nq.get("bid") and nq.get("ask"):
        lines.append(f"  Bid/Ask:      {_px(nq['bid'])} / {_px(nq['ask'])}")
    if nq.get("prev_close"):
        lines.append(f"  Prev Close:   {_px(nq['prev_close'])}")
    if nq.get("day_low") or nq.get("day_high"):
        lines.append(f"  Day Range:    {_px(nq['day_low'])} - {_px(nq['day_high'])}")
    lines.append(f"  Volume:       {nq['volume']:,}")
    lines.append(f"  As of:        {nq['as_of'] or 'unknown'}  (source: {src})")
    if nq.get("stale"):
        lines.append(
            "  ⚠️  STALE QUOTE — the Perplexity feed lags the live session (often a prior "
            "close). Use get_stock_snapshots for authoritative real-time price."
        )
    return lines


# ---------- Legacy helpers ----------


def _safe_get(d: Any, *keys: str, default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d:
            return d[k]
    return default


def _as_list(v: Any, key: str | None = None) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, dict) and key and key in v:
        inner = v[key]
        return inner if isinstance(inner, list) else []
    return []


# ---------- Tool: get_perplexity_quote ----------


def _pplx_extra_lines(pplx_quote: Any) -> list[str]:
    """52-week range and 50-day MA — Perplexity-only fields not in the Alpaca snapshot."""
    if not isinstance(pplx_quote, dict):
        return []
    lines: list[str] = []
    year_low = pplx_quote.get("yearLow") or 0
    year_high = pplx_quote.get("yearHigh") or 0
    if year_low or year_high:
        lines.append(f"  52W Range:    {_px(float(year_low))} - {_px(float(year_high))}")
    ma50 = pplx_quote.get("priceAvg50") or 0
    price = pplx_quote.get("price") or 0
    if ma50 and price:
        pct = ((float(price) - float(ma50)) / float(ma50)) * 100
        lines.append(f"  50-Day MA:    {_px(float(ma50))} ({pct:+.1f}%)")
    return lines


def _format_quote_entry(symbol: str, pplx_quote: Any, alpaca_quote: dict | None) -> str:
    """Render one symbol's quote, preferring authoritative Alpaca real-time data.

    Falls back to Perplexity's quote (stale-flagged) when Alpaca is unavailable.
    52-week range / 50-day MA from Perplexity are appended when present.
    """
    nq = alpaca_quote or _normalize_pplx_quote(pplx_quote)
    if nq is None:
        err = (
            pplx_quote.get("error", "unknown")
            if isinstance(pplx_quote, dict)
            else "invalid response"
        )
        return f"{symbol}: Error - {err}"
    header = [f"\n{'=' * 50}", f"  {symbol} - Quote", f"{'=' * 50}"]
    body = _format_quote_block(nq)
    return "\n".join(header + body + _pplx_extra_lines(pplx_quote) + [""])


async def get_perplexity_quote(symbols: str) -> str:
    """
    Get real-time stock quotes (authoritative Alpaca data, Perplexity fallback).

    Price/change/volume come from Alpaca's real-time snapshot. Perplexity is used
    only for 52-week range / 50-day MA, and as a (stale-flagged) price fallback if
    Alpaca is unavailable — the Perplexity quote feed lags the live session.
    For news and bull/bear cases, use get_perplexity_comprehensive.

    Args:
        symbols: Comma-separated stock symbols (e.g., "NVDA,AAPL,SMX")

    Returns:
        Formatted quote data including price, change, bid/ask, volume, as-of time.
    """
    if PerplexityClient is None:
        return _NOT_INSTALLED
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        return "Error: No symbols provided"

    paths = [f"/rest/finance/quote/{s}?with_history=false&with_ui_hints=true" for s in symbol_list]
    async with PerplexityClient() as pc:
        quotes = await pc.fetch_many(paths)
    # Blocking HTTP (snapshots + market calendar): run it off the event loop.
    alpaca = await asyncio.to_thread(_alpaca_realtime_quotes, symbol_list)
    return "\n".join(
        _format_quote_entry(sym, q, alpaca.get(sym))
        for sym, q in zip(symbol_list, quotes, strict=False)
    )


# ---------- Tool: get_perplexity_movers ----------


async def get_perplexity_movers() -> str:
    """
    Get today's top market gainers and losers from Perplexity Finance.

    Calls the live /rest/finance/top-movers/market endpoint.
    Replaces the prior implementation that iterated a hardcoded penny-stock list.

    Returns:
        Formatted list of top gainers and losers for day-trading.
    """
    if PerplexityClient is None:
        return _NOT_INSTALLED
    async with PerplexityClient() as pc:
        data = await pc.fetch_json("/rest/finance/top-movers/market?country=US")

    if isinstance(data, dict) and data.get("error"):
        return f"Error fetching top movers: {data['error']}"

    if not isinstance(data, dict):
        return "Error: unexpected response shape from top-movers endpoint"

    gainers = data.get("gainers") or []
    losers = data.get("losers") or []

    if not gainers and not losers:
        return "No top movers data available"

    def _row(q: dict) -> str:
        sym = _safe_get(q, "symbol", "ticker", default="?")
        price = _safe_get(q, "price", "regularMarketPrice", default=0) or 0
        pct = (
            _safe_get(
                q, "changesPercentage", "percentChange", "regularMarketChangePercent", default=0
            )
            or 0
        )
        # _px keeps sub-dollar movers at 4 decimals ($0.1568, not $0.16); right-justified.
        return f"  {sym:6s} {_px(float(price)):>10s}  {float(pct):+7.2f}%"

    lines = [f"\n{'=' * 60}", "  🚀 TOP MOVERS - Perplexity Finance", "=" * 60, ""]
    if gainers:
        lines.append("GAINERS:")
        lines.extend(_row(g) for g in gainers[:10])
    if losers:
        lines.append("")
        lines.append("LOSERS:")
        lines.extend(_row(loser) for loser in losers[:10])
    lines.append("")
    return "\n".join(lines)


# ---------- Tool: get_perplexity_comprehensive ----------


def _format_comprehensive(symbol: str, raw: dict, quote: dict | None = None) -> str:
    """Format multi-endpoint stock data into a readable text block.

    The QUOTE block prefers the authoritative `quote` override (Alpaca
    real-time) when supplied, falling back to Perplexity's quote (which lags the
    live session and is flagged STALE when old).
    """
    lines = [
        f"\n{'=' * 60}",
        f"  {symbol} - Perplexity Finance Comprehensive",
        f"{'=' * 60}",
    ]

    # Quote — authoritative Alpaca real-time when available, else stale-flagged Perplexity.
    nq = quote or _normalize_pplx_quote(raw.get("quote") or {})
    if nq is not None:
        lines.extend(_format_quote_block(nq))

    # Profile
    p = raw.get("profile") or {}
    if isinstance(p, dict) and "error" not in p:
        name = _safe_get(p, "companyName", "name", default="")
        sector = _safe_get(p, "sector", default="")
        industry = _safe_get(p, "industry", default="")
        if name or sector:
            lines.append("")
            lines.append("PROFILE:")
            if name:
                lines.append(f"  Company:      {name}")
            if sector:
                lines.append(f"  Sector:       {sector}")
            if industry:
                lines.append(f"  Industry:     {industry}")

    # Bulls vs Bears
    bvb_data = _as_list(raw.get("bulls_bears"), "controversial_issues")
    if bvb_data:
        lines.append("")
        lines.append("BULLS vs BEARS:")
        for issue in bvb_data[:3]:
            iss_name = _safe_get(issue, "issue", default="")
            bull = _safe_get(issue.get("positive_view") or {}, "description", default="")
            bear = _safe_get(issue.get("negative_view") or {}, "description", default="")
            if iss_name:
                lines.append(f"  • {iss_name}")
            if bull:
                lines.append(f"    🐂 {bull[:300]}")
            if bear:
                lines.append(f"    🐻 {bear[:300]}")

    # News
    news_posts = _as_list(raw.get("news"), "posts")
    if news_posts:
        lines.append("")
        lines.append("RECENT NEWS:")
        for n in news_posts[:5]:
            headline = _safe_get(n, "headline", default="(no headline)")
            ts = str(_safe_get(n, "timestamp", default=""))[:10]
            lines.append(f"  [{ts}] {headline}")

    # Earnings
    earn_list = _as_list(raw.get("earnings"), "earnings")
    next_earning = next(
        (
            e
            for e in earn_list
            if isinstance(e, dict)
            and e.get("actualEps") is None
            and e.get("estimatedEps") is not None
        ),
        None,
    )
    if next_earning:
        date = str(_safe_get(next_earning, "date", default=""))[:10]
        period_q = _safe_get(next_earning, "fiscalPeriod", default="")
        period_y = _safe_get(next_earning, "fiscalYear", default="")
        eps_est = next_earning.get("estimatedEps")
        lines.append("")
        lines.append(f"NEXT EARNINGS: {date} ({period_q} {period_y}), Est EPS: ${eps_est}")

    # Peers
    peer_list = _as_list(raw.get("peers"), "peers")
    if peer_list:
        peer_syms = [_safe_get(pe, "symbol", "ticker", default="") for pe in peer_list[:5]]
        peer_syms = [ps for ps in peer_syms if ps]
        if peer_syms:
            lines.append("")
            lines.append(f"PEERS: {', '.join(peer_syms)}")

    lines.append("")
    return "\n".join(lines)


async def get_perplexity_comprehensive(symbol: str, json_output: bool = False) -> str:
    """
    Get comprehensive stock analysis from Perplexity Finance.

    Fetches 8 Perplexity REST endpoints in parallel via curl_cffi (~2-3s):
    quote, profile, timeline, bulls-vs-bears summary, news, peers, earnings,
    and prediction-markets. Replaces the prior Camoufox subprocess approach.

    Args:
        symbol: Stock ticker symbol (e.g., "NVDA", "AAPL")
        json_output: If True, return the raw 8-endpoint dict as JSON. Otherwise
                     return a formatted text block.

    Returns:
        Formatted comprehensive analysis or JSON dump.
    """
    if PerplexityClient is None:
        return _NOT_INSTALLED
    symbol = symbol.strip().upper()
    if not symbol:
        return "Error: No symbol provided"

    async with PerplexityClient() as pc:
        result = await pc.fetch_stock_data(symbol)
    raw = result.get("raw", {})

    # Authoritative real-time price from Alpaca; Perplexity's quote lags a session.
    quote = (await asyncio.to_thread(_alpaca_realtime_quotes, [symbol])).get(symbol)

    if json_output:
        if quote is not None:
            raw = {**raw, "quote_realtime": quote}
        return json.dumps(raw, indent=2, default=str)

    return _format_comprehensive(symbol, raw, quote=quote)
