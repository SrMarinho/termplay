"""Testes para Room e RoomManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from termplay.engine.room import RoomManager, RoomPlayer


def _make_player(name: str = "P1") -> RoomPlayer:
    transport = MagicMock()
    transport.write = AsyncMock()
    return RoomPlayer(name=name, transport=transport)


class TestRoomManager:
    def setup_method(self) -> None:
        RoomManager.clear()

    def teardown_method(self) -> None:
        RoomManager.clear()

    def test_create_returns_room_with_host(self) -> None:
        host = _make_player()
        room = RoomManager.create(host)
        assert room.host is host
        assert host in room.players

    def test_create_generates_unique_code(self) -> None:
        codes = {RoomManager.create(_make_player()).code for _ in range(20)}
        assert len(codes) == 20

    def test_get_returns_room(self) -> None:
        host = _make_player()
        room = RoomManager.create(host)
        assert RoomManager.get(room.code) is room

    def test_get_case_insensitive(self) -> None:
        host = _make_player()
        room = RoomManager.create(host)
        assert RoomManager.get(room.code.lower()) is room

    def test_get_unknown_returns_none(self) -> None:
        assert RoomManager.get("ZZZZ") is None

    def test_remove_deletes_room(self) -> None:
        room = RoomManager.create(_make_player())
        RoomManager.remove(room.code)
        assert RoomManager.get(room.code) is None

    def test_clear_removes_all(self) -> None:
        for _ in range(3):
            RoomManager.create(_make_player())
        RoomManager.clear()
        assert RoomManager._rooms == {}


class TestRoom:
    def setup_method(self) -> None:
        RoomManager.clear()

    def teardown_method(self) -> None:
        RoomManager.clear()

    def test_add_player_increases_count(self) -> None:
        host = _make_player("Host")
        room = RoomManager.create(host, max_players=4)
        p2 = _make_player("P2")
        assert room.add_player(p2) is True
        assert room.player_count == 2

    def test_add_player_fails_when_full(self) -> None:
        host = _make_player("Host")
        room = RoomManager.create(host, max_players=2)
        room.add_player(_make_player("P2"))
        assert room.is_full
        assert room.add_player(_make_player("P3")) is False

    def test_remove_player(self) -> None:
        host = _make_player("Host")
        room = RoomManager.create(host, max_players=4)
        p2 = _make_player("P2")
        room.add_player(p2)
        room.remove_player(p2)
        assert room.player_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_writes_to_all(self) -> None:
        host = _make_player("Host")
        room = RoomManager.create(host, max_players=4)
        p2 = _make_player("P2")
        room.add_player(p2)
        await room.broadcast("hello")
        host.transport.write.assert_called_once_with("hello")
        p2.transport.write.assert_called_once_with("hello")

    def test_ready_event_starts_unset(self) -> None:
        room = RoomManager.create(_make_player())
        assert not room.ready.is_set()

    def test_game_complete_starts_unset(self) -> None:
        room = RoomManager.create(_make_player())
        assert not room.game_complete.is_set()
