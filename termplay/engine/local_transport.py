"""LocalTransportAdapter — in-process transport that bridges a game controller
to a Textual screen via asyncio queues and a write callback."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from typing_extensions import override

from termplay.engine.interfaces import ITransportAdapter

WriteCallback = Callable[[str], Awaitable[None]]


class LocalTransportAdapter(ITransportAdapter):
    """Connects a local game controller to a Textual UI without a network hop."""

    def __init__(self) -> None:
        self._input: asyncio.Queue[str] = asyncio.Queue()
        self._write_cb: WriteCallback | None = None

    def set_write_callback(self, cb: WriteCallback) -> None:
        self._write_cb = cb

    async def feed(self, line: str) -> None:
        """Push a line of input into the controller's read queue."""
        await self._input.put(line)

    @override
    async def write(self, text: str) -> None:
        if self._write_cb is not None:
            await self._write_cb(text)

    @override
    async def read_line(self) -> str:
        return await self._input.get()

    @override
    async def read_char(self) -> str:
        return await self.read_line()

    @override
    async def close(self) -> None:
        pass

    @property
    @override
    def width(self) -> int:
        return 80
