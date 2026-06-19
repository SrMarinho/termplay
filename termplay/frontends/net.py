"""ServerConnection — cliente do protocolo JSON (lado TUI)."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from termplay.engine.protocol import decode, encode


class ServerConnection:
    """Conexão TCP com o servidor termplay falando mensagens JSON por linha."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        self._reader = reader
        self._writer = writer

    @classmethod
    async def connect(cls, host: str, port: int) -> ServerConnection:
        reader, writer = await asyncio.open_connection(host, port)
        return cls(reader, writer)

    async def send(self, **msg: object) -> None:
        if self._writer.is_closing():
            return
        self._writer.write(encode(msg))
        await self._writer.drain()

    async def recv(self) -> dict[str, Any] | None:
        line = await self._reader.readline()
        if not line:
            return None
        try:
            return decode(line)
        except ValueError:
            return {}

    async def close(self) -> None:
        if not self._writer.is_closing():
            self._writer.close()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self._writer.wait_closed(), timeout=2.0)
