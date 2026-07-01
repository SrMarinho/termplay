"""Reconnection: dropped players keep their seat for a grace period."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from termplay.engine.room import RoomManager, RoomPlayer
from termplay.engine.server import TermPlayServer


def _player(name: str, is_bot: bool = False) -> RoomPlayer:
    transport = MagicMock()
    transport.write = AsyncMock()
    return RoomPlayer(name=name, transport=transport, is_bot=is_bot)


class TestRoomTokens:
    def setup_method(self) -> None:
        RoomManager.clear()

    def teardown_method(self) -> None:
        RoomManager.clear()

    def test_players_get_unique_tokens(self) -> None:
        a, b = _player("A"), _player("B")
        assert a.token and b.token and a.token != b.token

    def test_find_player_by_token(self) -> None:
        host = _player("Host")
        room = RoomManager.create(host)
        guest = _player("Guest")
        room.add_player(guest)

        found = RoomManager.find_player(guest.token)
        assert found is not None
        assert found[0] is room
        assert found[1] is guest

    def test_find_player_unknown_token(self) -> None:
        RoomManager.create(_player("Host"))
        assert RoomManager.find_player("nope") is None

    @pytest.mark.asyncio
    async def test_broadcast_skips_disconnected(self) -> None:
        host = _player("Host")
        room = RoomManager.create(host)
        guest = _player("Guest")
        guest.connected = False
        room.add_player(guest)

        await room.broadcast("hello")

        host.transport.write.assert_awaited_once_with("hello")
        guest.transport.write.assert_not_awaited()


class TestGracePeriod:
    def setup_method(self) -> None:
        RoomManager.clear()

    def teardown_method(self) -> None:
        RoomManager.clear()

    @pytest.mark.asyncio
    async def test_disconnect_keeps_seat_during_grace(self) -> None:
        server = TermPlayServer(reconnect_grace=10)
        host = _player("Host")
        room = RoomManager.create(host)
        guest = _player("Guest")
        room.add_player(guest)

        server._on_disconnect(room, guest)
        await asyncio.sleep(0.05)

        assert guest in room.players
        assert guest.connected is False
        server._grace.pop(guest.token).cancel()

    @pytest.mark.asyncio
    async def test_grace_expiry_removes_seat(self) -> None:
        server = TermPlayServer(reconnect_grace=0.01)
        host = _player("Host")
        room = RoomManager.create(host)
        guest = _player("Guest")
        room.add_player(guest)

        server._on_disconnect(room, guest)
        await asyncio.sleep(0.1)

        assert guest not in room.players
        assert RoomManager.get(room.code) is room  # host still seated

    @pytest.mark.asyncio
    async def test_rebound_player_survives_grace_expiry(self) -> None:
        server = TermPlayServer(reconnect_grace=0.01)
        host = _player("Host")
        room = RoomManager.create(host)
        guest = _player("Guest")
        room.add_player(guest)

        server._on_disconnect(room, guest)
        guest.connected = True  # simulates a rebind before expiry
        await asyncio.sleep(0.1)

        assert guest in room.players

    @pytest.mark.asyncio
    async def test_midgame_expiry_defers_removal_until_match_end(self) -> None:
        server = TermPlayServer(reconnect_grace=0.01)
        host = _player("Host")
        room = RoomManager.create(host)
        guest = _player("Guest")
        room.add_player(guest)
        room.ready.set()  # match in progress

        server._on_disconnect(room, guest)
        await asyncio.sleep(0.1)
        assert guest in room.players  # controller still owns the transport

        room.game_complete.set()
        await asyncio.sleep(0.05)
        assert guest not in room.players


class TestAdapterRebind:
    @pytest.mark.asyncio
    async def test_rebind_preserves_identity_and_queue(self) -> None:
        from termplay.engine.protocol_adapter import ProtocolServerAdapter

        r1, w1 = MagicMock(), MagicMock()
        adapter = ProtocolServerAdapter(r1, w1)
        await adapter.input_queue.put("queued")
        adapter.last_render = "SNAPSHOT"

        r2, w2 = MagicMock(), MagicMock()
        adapter.rebind(r2, w2)

        assert adapter._reader is r2
        assert adapter._writer is w2
        assert await adapter.read_line() == "queued"
        assert adapter.last_render == "SNAPSHOT"
