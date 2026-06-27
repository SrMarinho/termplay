"""Host migration: leadership passes to another player when the host leaves."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from termplay.engine.room import RoomManager, RoomPlayer
from termplay.engine.server import TermPlayServer


def _player(name: str, is_bot: bool = False) -> RoomPlayer:
    transport = MagicMock()
    transport.write = AsyncMock()
    return RoomPlayer(name=name, transport=transport, is_bot=is_bot)


class TestHostMigration:
    def setup_method(self) -> None:
        RoomManager.clear()

    def teardown_method(self) -> None:
        RoomManager.clear()

    @pytest.mark.asyncio
    async def test_host_leaving_promotes_next_human(self) -> None:
        server = TermPlayServer()
        host = _player("Host")
        room = RoomManager.create(host)
        guest = _player("Guest")
        room.add_player(guest)

        await server._handle_departure(room, host)

        assert room.host is guest
        assert host not in room.players
        assert RoomManager.get(room.code) is room  # room survives

    @pytest.mark.asyncio
    async def test_host_leaving_skips_bots(self) -> None:
        server = TermPlayServer()
        host = _player("Host")
        room = RoomManager.create(host)
        bot = _player("Bot 1", is_bot=True)
        human = _player("Human")
        room.add_player(bot)
        room.add_player(human)

        await server._handle_departure(room, host)

        assert room.host is human  # bot is not eligible to lead

    @pytest.mark.asyncio
    async def test_room_dropped_when_no_humans_remain(self) -> None:
        server = TermPlayServer()
        host = _player("Host")
        room = RoomManager.create(host)
        bot = _player("Bot 1", is_bot=True)
        room.add_player(bot)

        await server._handle_departure(room, host)

        assert RoomManager.get(room.code) is None  # only a bot left → drop room

    @pytest.mark.asyncio
    async def test_non_host_leaving_keeps_host(self) -> None:
        server = TermPlayServer()
        host = _player("Host")
        room = RoomManager.create(host)
        guest = _player("Guest")
        room.add_player(guest)

        await server._handle_departure(room, guest)

        assert room.host is host
        assert guest not in room.players
