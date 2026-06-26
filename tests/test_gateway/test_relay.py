"""WebGateway relay and room-list synthesis tests."""

from __future__ import annotations

import asyncio

from termplay.engine.discovery import DiscoveredRoom
from termplay.gateway.server import WebGateway, _safe_json
from termplay.gateway.ws import WebSocketClosed


class _FakeWS:
    """Minimal WebSocket double: inbound queue, captured outbound texts."""

    def __init__(self, inbound: list[str]) -> None:
        self._inbound = list(inbound)
        self.sent: list[str] = []
        self.closed = False

    async def recv_text(self) -> str:
        if not self._inbound:
            raise WebSocketClosed
        return self._inbound.pop(0)

    async def send_text(self, text: str) -> None:
        self.sent.append(text)

    async def close(self) -> None:
        self.closed = True


class _FakeWriter:
    def __init__(self) -> None:
        self.buffer = bytearray()

    def write(self, data: bytes) -> None:
        self.buffer += data

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        return None


def _reader_with(data: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


def test_safe_json_handles_garbage() -> None:
    assert _safe_json("not json") == {}
    assert _safe_json("[1,2]") == {}
    assert _safe_json('{"a":1}') == {"a": 1}


def test_room_list_message_maps_discovered_rooms() -> None:
    gateway = WebGateway()
    room = DiscoveredRoom(
        ip="10.0.0.5", port=4443, host="Ana", game="uno",
        players=1, max_players=4, status="waiting",
    )
    gateway._discoverer._rooms = {"10.0.0.5": room}  # type: ignore[attr-defined]
    msg = gateway.room_list_message()
    assert msg["type"] == "room_list"
    assert msg["rooms"] == [
        {
            "ip": "10.0.0.5", "port": 4443, "host": "Ana", "game": "uno",
            "players": 1, "max_players": 4, "status": "waiting",
        }
    ]


async def test_relay_forwards_both_directions() -> None:
    gateway = WebGateway()
    ws = _FakeWS(inbound=['{"action":"chat","text":"hi"}'])
    tcp_reader = _reader_with(b'{"type":"game_render","content":"{}"}\n')
    tcp_writer = _FakeWriter()

    await gateway._relay(ws, tcp_reader, tcp_writer)  # type: ignore[arg-type]

    # tcp -> ws: server line delivered to the browser (newline stripped)
    assert '{"type":"game_render","content":"{}"}' in ws.sent
    # ws -> tcp: browser action written as a JSON line
    assert tcp_writer.buffer == b'{"action":"chat","text":"hi"}\n'
