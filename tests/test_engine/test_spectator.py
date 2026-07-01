"""Spectator mode: watchers get the public feed without taking a seat."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from termplay.engine.protocol import decode, encode
from termplay.engine.room import RoomManager, RoomPlayer
from termplay.engine.server import TermPlayServer
from unittest.mock import AsyncMock, MagicMock


def _player(name: str, spectator: bool = False) -> RoomPlayer:
    transport = MagicMock()
    transport.write = AsyncMock()
    return RoomPlayer(name=name, transport=transport, is_spectator=spectator)


class TestRoomSeats:
    def setup_method(self) -> None:
        RoomManager.clear()

    def teardown_method(self) -> None:
        RoomManager.clear()

    def test_spectators_do_not_occupy_seats(self) -> None:
        room = RoomManager.create(_player("Host"), max_players=2)
        room.add_player(_player("Guest"))
        room.players.append(_player("Watcher", spectator=True))

        assert room.is_full  # 2 seats taken
        assert room.player_count == 2
        assert [p.name for p in room.spectators] == ["Watcher"]


class TestSpectateFlow:
    def setup_method(self) -> None:
        RoomManager.clear()

    def teardown_method(self) -> None:
        RoomManager.clear()

    @pytest.mark.asyncio
    async def test_spectate_join_and_room_state(self) -> None:
        server = TermPlayServer("127.0.0.1", 0, game_name="uno")
        await server.start()
        try:
            port = server.actual_port
            hr, hw = await asyncio.open_connection("127.0.0.1", port)
            hw.write(encode({"action": "create_room", "name": "Host", "game": "uno"}))
            await hw.drain()
            created = await _recv(hr, "room_created")
            code = created["code"]

            sr, sw = await asyncio.open_connection("127.0.0.1", port)
            sw.write(encode({"action": "spectate", "name": "Watcher", "code": code}))
            await sw.drain()
            joined = await _recv(sr, "spectate_joined")
            assert joined["code"] == code
            assert joined["you"] == "Watcher"

            state = await _recv(hr, "room_state")
            while "Watcher" not in state.get("spectators", []):
                state = await _recv(hr, "room_state")
            assert "Watcher" not in state["players"]  # no seat taken
            assert state["player_count"] == 1

            room = RoomManager.get(code)
            assert room is not None
            assert len(room.spectator_feed) == 1
            sw.close()
            hw.close()
        finally:
            await server.stop()
            RoomManager.clear()


class TestUnoSpectatorFeed:
    @pytest.mark.asyncio
    async def test_spectator_payload_hides_hands(self) -> None:
        from termplay.engine.transport.queued_adapter import QueuedAdapter
        from termplay.games.uno.broadcaster import broadcast
        from termplay.games.uno.controller import UnoController

        adapters = [QueuedAdapter(), QueuedAdapter()]
        ctrl = UnoController(adapters, ["A", "B"])

        class _Sink:
            def __init__(self) -> None:
                self.writes: list[str] = []

            async def write(self, text: str) -> None:
                self.writes.append(text)

        sink = _Sink()
        ctrl.add_spectators([sink])
        await broadcast(ctrl._ctx, active_idx=0)

        assert sink.writes, "spectator received no feed"
        payload: dict[str, Any] = json.loads(sink.writes[-1])
        assert payload["you"] == -1
        assert payload["hand"] == []
        assert payload["playable"] == []
        assert payload["your_turn"] is False
        assert payload["spectator"] is True
        # public info is still there
        assert len(payload["players"]) == 2
        assert payload["top"]


async def _recv(reader: asyncio.StreamReader, msg_type: str) -> dict[str, Any]:
    async with asyncio.timeout(3):
        while True:
            line = await reader.readline()
            assert line, f"connection closed waiting for {msg_type}"
            msg = decode(line)
            if msg.get("type") == msg_type:
                return msg
