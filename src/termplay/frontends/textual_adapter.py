"""TextualTransportAdapter — ITransportAdapter backed by Textual widgets."""

from __future__ import annotations

import asyncio
from typing import Any

from rich.text import Text
from textual.app import App
from textual.widgets import RichLog
from typing_extensions import override

from termplay.engine.interfaces import ITransportAdapter


class TextualTransportAdapter(ITransportAdapter):
    """Adapta ITransportAdapter para widgets Textual (RichLog + asyncio.Queue).

    write() → RichLog.write(Text.from_ansi(...))
    read_line/read_char → asyncio.Queue; alimentada por feed() via on_input_submitted
    """

    def __init__(self, app: App[Any], log: RichLog) -> None:
        self._app: App[Any] = app
        self._log = log
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._closed = False

    def feed(self, value: str) -> None:
        """Enfileira linha do Input. Chamado pelo App em on_input_submitted."""
        if not self._closed:
            self._queue.put_nowait(value.strip())

    @override
    async def write(self, text: str) -> None:
        if self._closed:
            return
        # Rich Panels usam box-drawing chars — detectar frame completo e limpar
        clean = text.replace("\r\n", "\n").replace("\r", "\n")
        if any(c in clean for c in ("╭", "╰", "╔", "╚", "┌", "└")):
            self._log.clear()
        self._log.write(Text.from_ansi(clean))

    @override
    async def read_line(self) -> str:
        if self._closed:
            raise ConnectionError("Transporte fechado")
        return await self._queue.get()

    @override
    async def read_char(self) -> str:
        if self._closed:
            raise ConnectionError("Transporte fechado")
        line = await self._queue.get()
        return line[0] if line else "\n"

    @override
    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._app.call_later(self._app.exit)

    @property
    @override
    def width(self) -> int:
        return self._app.size.width or 80
