"""ProtocolServerAdapter — transporte server-side baseado em mensagens JSON.

Durante o lobby usa send_control/recv_control (mensagens estruturadas).
Durante o jogo, implementa ITransportAdapter: write() encapsula o render ANSI
em mensagem game_render; read_line() consome de input_queue (alimentada pelo relay).
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

from termplay.engine.interfaces import ITransportAdapter
from termplay.engine.protocol import TYPE_GAME_RENDER, decode, encode

if TYPE_CHECKING:
    import asyncio as _asyncio


class ProtocolServerAdapter(ITransportAdapter):
    """Adaptador que fala o protocolo JSON com o cliente TUI."""

    def __init__(
        self,
        reader: _asyncio.StreamReader,
        writer: _asyncio.StreamWriter,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self.input_queue: asyncio.Queue[str] = asyncio.Queue()
        self._width = 80
        self.last_render: str | None = None

    def rebind(self, reader: _asyncio.StreamReader, writer: _asyncio.StreamWriter) -> None:
        """Swap the underlying streams after a reconnect. The adapter object is
        what game controllers hold on to, so its identity (and input_queue)
        must survive the connection swap."""
        self._reader = reader
        self._writer = writer

    # ── Protocolo (lobby) ────────────────────────────────────────────────────

    async def send_control(self, **fields: object) -> None:
        if self._writer.is_closing():
            return
        try:
            self._writer.write(encode(fields))
            await self._writer.drain()
        except (ConnectionError, OSError):
            # Peer dropped mid-write; the read side will surface the disconnect.
            pass

    async def recv_control(self) -> dict[str, Any] | None:
        try:
            line = await self._reader.readline()
        except OSError:
            return None
        if not line:
            return None
        try:
            return decode(line)
        except ValueError:
            return {}

    # ── ITransportAdapter (jogo) ─────────────────────────────────────────────

    async def write(self, text: str) -> None:
        self.last_render = text
        await self.send_control(type=TYPE_GAME_RENDER, content=text)

    async def read_line(self) -> str:
        return await self.input_queue.get()

    async def read_char(self) -> str:
        line = await self.input_queue.get()
        return line[0] if line else "\n"

    async def close(self) -> None:
        if not self._writer.is_closing():
            self._writer.close()
            with contextlib.suppress(Exception):
                await self._writer.wait_closed()

    @property
    def width(self) -> int:
        return self._width
