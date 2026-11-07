"""Client for bottom_barrel's bb-stream-hub: the account's one Alpaca market-data socket.

Alpaca allows ONE market-data websocket per account. bb-stream-hub owns it and fans
out to local consumers over ws://127.0.0.1:8770/ws, so the MCP server's streaming
tools attach to it as an ordinary client instead of opening a second upstream
socket that would fight bb-live-monitor, bb-fast-breakout and the other Rust
consumers. When the hub is not running, streaming_tools falls back to its own
direct StockDataStream.

HubStream mirrors the slice of alpaca-py's StockDataStream that streaming_tools
uses (subscribe_trades/quotes/bars/trading_statuses, run, stop), and hands the
existing handlers objects with the same attribute names the SDK models carry, so
the handlers, buffers and every downstream tool are unchanged.

Protocol (bb-stream-hub/src/protocol.rs):
  -> {"cmd":"subscribe","symbols":[...],"types":["trades","quotes","bars","statuses"]}
  <- {"type":"trade","symbol","price","size","i","x","c","t"}
     {"type":"quote","symbol","bid","ask","bid_size","ask_size","t"}
     {"type":"bar","symbol","o","h","l","c","v","n","vw","t"}
     {"type":"tradingstatus","symbol","status_code","status_message",...,"t"}
     {"type":"gap","from","to"}  (upstream reconnected: the series has a hole)
     {"type":"error","code","message"}
The hub's upstream feed (SIP or BOATS) is fixed by its own --feed flag.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import websockets

logger = logging.getLogger(__name__)

HUB_URL_DEFAULT = "ws://127.0.0.1:8770/ws"
HUB_TYPES = ("trades", "quotes", "bars", "statuses")  # what the hub transports

Handler = Callable[[Any], Awaitable[None]]


def hub_url() -> str:
    """BB_STREAM_HUB overrides the hub address (same variable the Rust consumers read)."""
    return os.environ.get("BB_STREAM_HUB") or HUB_URL_DEFAULT


async def hub_available(url: str | None = None, timeout: float = 1.0) -> bool:
    """True when a hub answers a websocket handshake at *url*."""
    try:
        async with asyncio.timeout(timeout):
            async with websockets.connect(url or hub_url(), open_timeout=timeout):  # type: ignore[attr-defined]
                return True
    except Exception:
        return False


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _to_model(event: dict) -> tuple[str, SimpleNamespace] | None:
    """Translate a hub event into (stream type, SDK-shaped object)."""
    kind = event.get("type")
    if kind == "trade":
        return "trades", SimpleNamespace(
            symbol=event["symbol"],
            price=event["price"],
            size=event["size"],
            timestamp=_ts(event["t"]),
            exchange=event.get("x", "Unknown"),
            conditions=event.get("c", []),
            id=event.get("i"),
        )
    if kind == "quote":
        return "quotes", SimpleNamespace(
            symbol=event["symbol"],
            bid_price=event["bid"],
            ask_price=event["ask"],
            bid_size=event["bid_size"],
            ask_size=event["ask_size"],
            timestamp=_ts(event["t"]),
        )
    if kind == "bar":
        return "bars", SimpleNamespace(
            symbol=event["symbol"],
            open=event["o"],
            high=event["h"],
            low=event["l"],
            close=event["c"],
            volume=event["v"],
            trade_count=event.get("n"),
            vwap=event.get("vw"),
            timestamp=_ts(event["t"]),
        )
    if kind == "tradingstatus":
        return "statuses", SimpleNamespace(
            symbol=event["symbol"],
            status=event.get("status_code"),
            status_message=event.get("status_message"),
            reason_code=event.get("reason_code"),
            timestamp=_ts(event["t"]),
            tape="hub",
        )
    return None


class HubStream:
    """bb-stream-hub client with the StockDataStream surface streaming_tools uses."""

    def __init__(self, url: str | None = None) -> None:
        self.url = url or hub_url()
        self._handlers: dict[str, Handler] = {}
        self._symbols: dict[str, set[str]] = {t: set() for t in HUB_TYPES}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws: Any = None
        self._stopping = False
        self.gaps: list[tuple[str, str]] = []
        self.errors: list[str] = []

    # -- subscription surface (mirrors StockDataStream) ----------------------

    def _subscribe(self, kind: str, handler: Handler, symbols: tuple[str, ...]) -> None:
        self._handlers[kind] = handler
        new = {s.upper() for s in symbols} - self._symbols[kind]
        self._symbols[kind] |= new
        if new and self._loop is not None and self._ws is not None:
            asyncio.run_coroutine_threadsafe(self._send_subscribe({kind: new}), self._loop)

    def subscribe_trades(self, handler: Handler, *symbols: str) -> None:
        self._subscribe("trades", handler, symbols)

    def subscribe_quotes(self, handler: Handler, *symbols: str) -> None:
        self._subscribe("quotes", handler, symbols)

    def subscribe_bars(self, handler: Handler, *symbols: str) -> None:
        self._subscribe("bars", handler, symbols)

    def subscribe_trading_statuses(self, handler: Handler, *symbols: str) -> None:
        self._subscribe("statuses", handler, symbols)

    # -- lifecycle -------------------------------------------------------------

    def run(self) -> None:
        """Blocking, like StockDataStream.run(): call it from a worker thread."""
        asyncio.run(self._run())

    def stop(self) -> None:
        self._stopping = True
        if self._loop is not None and self._ws is not None:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)

    async def _send_subscribe(self, by_kind: dict[str, set[str]]) -> None:
        for kind, symbols in by_kind.items():
            if symbols:
                await self._ws.send(
                    json.dumps({"cmd": "subscribe", "symbols": sorted(symbols), "types": [kind]})
                )

    async def _run(self) -> None:
        self._loop = asyncio.get_running_loop()
        async with websockets.connect(self.url, max_size=None) as ws:  # type: ignore[attr-defined]
            self._ws = ws
            await self._send_subscribe(self._symbols)
            async for raw in ws:
                if self._stopping:
                    break
                try:
                    event = json.loads(raw)
                except (TypeError, ValueError):
                    continue
                kind = event.get("type")
                if kind == "gap":
                    self.gaps.append((event.get("from", ""), event.get("to", "")))
                    logger.warning("stream hub gap %s -> %s", event.get("from"), event.get("to"))
                    continue
                if kind == "error":
                    self.errors.append(f"{event.get('code')}: {event.get('message')}")
                    logger.error("stream hub error %s", self.errors[-1])
                    continue
                model = _to_model(event)
                if model is None:
                    continue
                handler = self._handlers.get(model[0])
                if handler is not None:
                    await handler(model[1])
        self._ws = None
