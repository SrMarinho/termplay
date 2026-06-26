"""WebGateway relay and room-list synthesis tests."""

from __future__ import annotations

import asyncio

from termplay.engine.discovery import DiscoveredRoom
from termplay.engine.protocol import ACTION_CREATE_ROOM, ACTION_JOIN_ROOM
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


def test_room_list_message_includes_server_info() -> None:
    gateway = WebGateway(game_server=("10.0.0.1", 5000))
    msg = gateway.room_list_message()
    assert msg["server"] == {"ip": "10.0.0.1", "port": 5000}


def test_build_connect_payload_join() -> None:
    msg: dict[str, object] = {
        "action": "join_room", "name": "Bob",
        "ip": "10.0.0.5", "port": 4443, "code": "AB",
    }
    payload = WebGateway._build_connect_payload(msg)
    assert payload["action"] == ACTION_JOIN_ROOM
    assert payload["name"] == "Bob"
    assert payload["code"] == "AB"


def test_build_connect_payload_create() -> None:
    msg: dict[str, object] = {"action": "create_room", "name": "Alice"}
    payload = WebGateway._build_connect_payload(msg)
    assert payload["action"] == ACTION_CREATE_ROOM
    assert payload["name"] == "Alice"
    assert "code" not in payload


def test_resolve_server_create_uses_configured() -> None:
    gateway = WebGateway(game_server=("192.168.1.1", 9999))
    msg: dict[str, object] = {"action": "create_room", "name": "Alice"}
    assert gateway._resolve_server(msg) == ("192.168.1.1", 9999)


def test_resolve_server_join_uses_room_address() -> None:
    gateway = WebGateway(game_server=("192.168.1.1", 9999))
    msg: dict[str, object] = {"action": "join_room", "ip": "10.0.0.5", "port": 4443}
    assert gateway._resolve_server(msg) == ("10.0.0.5", 4443)


async def test_relay_forwards_both_directions() -> None:
    gateway = WebGateway()
    ws = _FakeWS(inbound=['{"action":"chat","text":"hi"}'])
    tcp_reader = _reader_with(b'{"type":"game_render","content":"{}"}\n')
    tcp_writer = _FakeWriter()

    await gateway._relay(ws, tcp_reader, tcp_writer)  # type: ignore[arg-type]

    assert '{"type":"game_render","content":"{}"}' in ws.sent
    assert tcp_writer.buffer == b'{"action":"chat","text":"hi"}\n'


async def test_await_connect_accepts_create_room() -> None:
    gateway = WebGateway()
    ws = _FakeWS(inbound=['{"action":"create_room","name":"Alice"}'])
    result = await gateway._await_connect(ws)
    assert result is not None
    assert result.get("action") == "create_room"


async def test_await_connect_skips_unknown_then_accepts_join() -> None:
    gateway = WebGateway()
    ws = _FakeWS(inbound=[
        '{"action":"unknown"}',
        '{"action":"join_room","name":"Bob","ip":"10.0.0.1","port":4443}',
    ])
    result = await gateway._await_connect(ws)
    assert result is not None
    assert result.get("action") == "join_room"
