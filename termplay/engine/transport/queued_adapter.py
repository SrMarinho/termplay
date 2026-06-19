"""Transport adapters backed by asyncio.Queue.

QueuedTransportAdapter — relay: delegates writes to a real transport, reads from queue.
QueuedAdapter           — standalone test double: captures writes, feeds reads.
"""

from __future__ import annotations

import asyncio

from typing_extensions import override

from termplay.engine.interfaces import ITransportAdapter


class QueuedTransportAdapter(ITransportAdapter):
    """Wraps ITransportAdapter delegando writes ao real e reads à queue.

    Usado em multiplayer: session relay task preenche a queue,
    MultiplayerGameController lê dela sem disputar o socket.
    """

    def __init__(
        self,
        transport: ITransportAdapter,
        queue: asyncio.Queue[str],
    ) -> None:
        self._transport = transport
        self._queue = queue

    @override
    async def write(self, text: str) -> None:
        await self._transport.write(text)

    @override
    async def read_line(self) -> str:
        return await self._queue.get()

    @override
    async def read_char(self) -> str:
        line = await self._queue.get()
        return line[0] if line else "\n"

    @override
    async def close(self) -> None:
        await self._transport.close()

    @property
    @override
    def width(self) -> int:
        return self._transport.width


class QueuedAdapter(ITransportAdapter):
    """Standalone test double: feeds reads from a queue, captures writes to output_queue."""

    def __init__(self) -> None:
        self._input: asyncio.Queue[str] = asyncio.Queue()
        self.output_queue: asyncio.Queue[str] = asyncio.Queue()

    def feed(self, text: str) -> None:
        """Pre-load a line that read_line() / read_char() will return."""
        self._input.put_nowait(text)

    @override
    async def write(self, text: str) -> None:
        await self.output_queue.put(text)

    @override
    async def read_line(self) -> str:
        return await self._input.get()

    @override
    async def read_char(self) -> str:
        line = await self._input.get()
        return line[0] if line else "\n"

    @override
    async def close(self) -> None:
        pass

    @property
    @override
    def width(self) -> int:
        return 80
