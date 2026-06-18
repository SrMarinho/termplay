"""Testes para QueuedTransportAdapter."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from termplay.engine.transport.queued_adapter import QueuedTransportAdapter


def _make_adapter() -> tuple[QueuedTransportAdapter, MagicMock, asyncio.Queue[str]]:
    mock_transport = MagicMock()
    mock_transport.write = AsyncMock()
    mock_transport.close = AsyncMock()
    mock_transport.width = 80
    queue: asyncio.Queue[str] = asyncio.Queue()
    return QueuedTransportAdapter(mock_transport, queue), mock_transport, queue


class TestQueuedAdapterWrite:
    @pytest.mark.asyncio
    async def test_write_delegates_to_transport(self) -> None:
        adapter, mock, _ = _make_adapter()
        await adapter.write("hello")
        mock.write.assert_called_once_with("hello")


class TestQueuedAdapterReadLine:
    @pytest.mark.asyncio
    async def test_read_line_from_queue(self) -> None:
        adapter, _, queue = _make_adapter()
        await queue.put("50")
        assert await adapter.read_line() == "50"

    @pytest.mark.asyncio
    async def test_read_line_blocks_until_put(self) -> None:
        adapter, _, queue = _make_adapter()

        async def feed() -> None:
            await asyncio.sleep(0.01)
            await queue.put("test")

        task = asyncio.create_task(feed())
        result = await adapter.read_line()
        assert result == "test"
        await task


class TestQueuedAdapterReadChar:
    @pytest.mark.asyncio
    async def test_read_char_returns_first_char(self) -> None:
        adapter, _, queue = _make_adapter()
        await queue.put("hit")
        assert await adapter.read_char() == "h"

    @pytest.mark.asyncio
    async def test_read_char_empty_returns_newline(self) -> None:
        adapter, _, queue = _make_adapter()
        await queue.put("")
        assert await adapter.read_char() == "\n"


class TestQueuedAdapterWidth:
    def test_delegates_width_to_transport(self) -> None:
        adapter, mock, _ = _make_adapter()
        mock.width = 120
        assert adapter.width == 120


class TestQueuedAdapterClose:
    @pytest.mark.asyncio
    async def test_close_delegates_to_transport(self) -> None:
        adapter, mock, _ = _make_adapter()
        await adapter.close()
        mock.close.assert_called_once()
