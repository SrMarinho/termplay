"""QueuedTransportAdapter — ITransportAdapter que lê de asyncio.Queue externa."""

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
