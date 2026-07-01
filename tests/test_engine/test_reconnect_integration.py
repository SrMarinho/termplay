"""End-to-end reconnection over real TCP: drop a client, rebind with token."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from termplay.engine.protocol import decode, encode
from termplay.engine.room import RoomManager
from termplay.engine.server import TermPlayServer


class _Client:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    @classmethod
    async def connect(cls, port: int) -> _Client:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        return cls(reader, writer)

    async def send(self, **msg: object) -> None:
        self.writer.write(encode(msg))
        await self.writer.drain()

    async def recv(self, msg_type: str, timeout: float = 3.0) -> dict[str, Any]:
        """Read frames until one of the wanted type arrives."""
        async with asyncio.timeout(timeout):
            while True:
                line = await self.reader.readline()
                assert line, f"connection closed while waiting for {msg_type}"
                msg = decode(line)
                if msg.get("type") == msg_type:
                    return msg

    def drop(self) -> None:
        self.writer.close()


@pytest.mark.asyncio
async def test_guest_drops_and_rebinds_with_token() -> None:
    RoomManager.clear()
    server = TermPlayServer("127.0.0.1", 0, game_name="uno", reconnect_grace=5)
    await server.start()
    try:
        port = server.actual_port

        host = await _Client.connect(port)
        await host.send(action="create_room", name="Host", game="uno")
        created = await host.recv("room_created")
        code = created["code"]
        assert created["session_token"]

        guest = await _Client.connect(port)
        await guest.send(action="join_room", name="Guest", code=code)
        joined = await guest.recv("room_joined")
        token = joined["session_token"]
        assert token

        # Drop the guest's socket — seat must survive the grace window.
        guest.drop()
        state = await host.recv("room_state")
        # Wait until the server notices the drop (disconnected list fills).
        async with asyncio.timeout(3):
            while "Guest" not in state.get("disconnected", []):
                state = await host.recv("room_state")
        assert "Guest" in state["players"]

        # Rebind with the session token on a fresh connection.
        guest2 = await _Client.connect(port)
        await guest2.send(action="reconnect", token=token)
        rec = await guest2.recv("reconnected")
        assert rec["code"] == code
        assert rec["you"] == "Guest"
        assert rec["in_game"] is False

        state = await host.recv("room_state")
        async with asyncio.timeout(3):
            while state.get("disconnected"):
                state = await host.recv("room_state")
        assert "Guest" in state["players"]
        guest2.drop()
        host.drop()
    finally:
        await server.stop()
        RoomManager.clear()


@pytest.mark.asyncio
async def test_reconnect_with_bad_token_is_fatal() -> None:
    RoomManager.clear()
    server = TermPlayServer("127.0.0.1", 0, game_name="uno")
    await server.start()
    try:
        client = await _Client.connect(server.actual_port)
        await client.send(action="reconnect", token="deadbeef")
        err = await client.recv("error")
        assert err["fatal"] is True
        client.drop()
    finally:
        await server.stop()
        RoomManager.clear()


@pytest.mark.asyncio
async def test_grace_expiry_frees_the_seat() -> None:
    RoomManager.clear()
    server = TermPlayServer("127.0.0.1", 0, game_name="uno", reconnect_grace=0.05)
    await server.start()
    try:
        port = server.actual_port
        host = await _Client.connect(port)
        await host.send(action="create_room", name="Host", game="uno")
        created = await host.recv("room_created")

        guest = await _Client.connect(port)
        await guest.send(action="join_room", name="Guest", code=created["code"])
        await guest.recv("room_joined")
        guest.drop()

        state = await host.recv("room_state")
        async with asyncio.timeout(3):
            while "Guest" in state.get("players", []):
                state = await host.recv("room_state")
        assert "Guest" not in state["players"]
        host.drop()
    finally:
        await server.stop()
        RoomManager.clear()
