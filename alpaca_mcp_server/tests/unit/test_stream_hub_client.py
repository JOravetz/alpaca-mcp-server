"""HubStream against a fake bb-stream-hub (a local websocket server on a free port).

Nothing here touches Alpaca or the real hub: the fake speaks the hub's protocol
(bb-stream-hub/src/protocol.rs) and the test checks what HubStream subscribes to
and what it hands the handlers.
"""

import asyncio
import json
import threading

import pytest
import websockets

from alpaca_mcp_server.utils.stream_hub_client import HubStream, hub_available

EVENTS = [
    {"type": "trade", "symbol": "SNTI", "price": 0.1568, "size": 115, "i": 361, "x": "P",
     "c": ["@", "T"], "t": "2026-11-07T00:17:40.81282526Z"},
    {"type": "quote", "symbol": "SNTI", "bid": 0.151, "ask": 0.1568, "bid_size": 700,
     "ask_size": 100, "t": "2026-11-07T00:50:33.955730591Z"},
    {"type": "bar", "symbol": "SNTI", "o": 0.1568, "h": 0.1568, "l": 0.1568, "c": 0.1568,
     "v": 115, "n": 1, "vw": 0.1568, "t": "2026-11-07T00:17:00Z"},
    {"type": "gap", "from": "2026-11-07T00:18:00Z", "to": "2026-11-07T00:19:00Z"},
    {"type": "tradingstatus", "symbol": "SNTI", "status_code": "H", "status_message": "Halted",
     "reason_code": "T1", "reason_message": "News pending", "t": "2026-11-07T00:20:00Z"},
]


class FakeHub:
    """Records subscribe commands, then replays EVENTS and closes."""

    def __init__(self) -> None:
        self.commands: list[dict] = []
        self.url = ""
        self._server = None

    async def handler(self, ws, *_):
        # The client sends one subscribe per stream type it holds (trades, quotes, bars, statuses).
        try:
            for _ in range(4):
                self.commands.append(json.loads(await ws.recv()))
            for event in EVENTS:
                await ws.send(json.dumps(event))
            await ws.close()
        except websockets.ConnectionClosed:
            return  # a probe (hub_available) connects and leaves at once

    async def __aenter__(self):
        self._server = await websockets.serve(self.handler, "127.0.0.1", 0)
        port = self._server.sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}/ws"
        return self

    async def __aexit__(self, *exc):
        self._server.close()
        await self._server.wait_closed()


@pytest.mark.asyncio
async def test_subscribes_and_translates_events():
    received: dict[str, list] = {"trades": [], "quotes": [], "bars": [], "statuses": []}

    def collector(kind):
        async def handle(obj):
            received[kind].append(obj)

        return handle

    async with FakeHub() as hub:
        stream = HubStream(hub.url)
        stream.subscribe_trades(collector("trades"), "snti")
        stream.subscribe_quotes(collector("quotes"), "SNTI")
        stream.subscribe_bars(collector("bars"), "SNTI")
        stream.subscribe_trading_statuses(collector("statuses"), "SNTI")

        worker = threading.Thread(target=stream.run, daemon=True)
        worker.start()
        await asyncio.to_thread(worker.join, 10)
        assert not worker.is_alive(), "HubStream.run did not return after the hub closed"

    assert sorted(c["types"][0] for c in hub.commands) == ["bars", "quotes", "statuses", "trades"]
    assert all(c["cmd"] == "subscribe" and c["symbols"] == ["SNTI"] for c in hub.commands)

    (trade,) = received["trades"]
    assert (trade.symbol, trade.price, trade.size, trade.exchange) == ("SNTI", 0.1568, 115, "P")
    assert trade.timestamp.tzinfo is not None  # aware, so to_et() renders it in ET
    (quote,) = received["quotes"]
    assert (quote.bid_price, quote.ask_price, quote.bid_size, quote.ask_size) == (0.151, 0.1568, 700, 100)
    (bar,) = received["bars"]
    assert (bar.open, bar.close, bar.volume, bar.trade_count, bar.vwap) == (0.1568, 0.1568, 115, 1, 0.1568)
    (status,) = received["statuses"]
    assert (status.status, status.reason_code) == ("H", "T1")
    assert stream.gaps == [("2026-11-07T00:18:00Z", "2026-11-07T00:19:00Z")]


@pytest.mark.asyncio
async def test_hub_available_true_and_false():
    async with FakeHub() as hub:
        assert await hub_available(hub.url)
    # nothing listens on port 9 of loopback
    assert not await hub_available("ws://127.0.0.1:9/ws", timeout=0.5)


# ── start_global_stock_stream source selection (never a real Alpaca socket) ──


class _DirectStub:
    """Stands in for alpaca-py's StockDataStream so no test opens a real socket."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __getattr__(self, name):  # subscribe_* / run / stop
        return lambda *a, **k: None


@pytest.fixture
def streaming(monkeypatch):
    from alpaca_mcp_server.tools import streaming_tools

    monkeypatch.setattr(streaming_tools, "StockDataStream", _DirectStub)
    return streaming_tools


async def _start_then_stop(streaming, **kwargs):
    result = await streaming.start_global_stock_stream(**kwargs)
    stream = streaming._settings_module._global_stock_stream
    await streaming.stop_global_stock_stream()
    return result, stream


@pytest.mark.asyncio
async def test_uses_hub_when_running(streaming, monkeypatch):
    async with FakeHub() as hub:
        monkeypatch.setenv("BB_STREAM_HUB", hub.url)
        result, stream = await _start_then_stop(streaming, symbols=["SNTI"], data_types=["trades"])
    assert isinstance(stream, HubStream)
    assert "bb-stream-hub" in result


@pytest.mark.asyncio
async def test_falls_back_to_direct_without_hub(streaming, monkeypatch):
    monkeypatch.setenv("BB_STREAM_HUB", "ws://127.0.0.1:9/ws")  # nothing listens here
    result, stream = await _start_then_stop(streaming, symbols=["SNTI"], data_types=["trades"])
    assert isinstance(stream, _DirectStub)
    assert "hub not running" in result


@pytest.mark.asyncio
async def test_direct_when_hub_cannot_serve_type(streaming, monkeypatch):
    async with FakeHub() as hub:
        monkeypatch.setenv("BB_STREAM_HUB", hub.url)
        result, stream = await _start_then_stop(streaming, symbols=["SNTI"], data_types=["daily_bars"])
    assert isinstance(stream, _DirectStub)
    assert "hub serves" in result


@pytest.mark.asyncio
async def test_iex_rejected(streaming):
    result = await streaming.start_global_stock_stream(symbols=["SNTI"], feed="iex")
    assert "IEX is not used" in result
