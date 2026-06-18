"""Testes para TextualTransportAdapter."""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest

from termplay.frontends.textual_adapter import TextualTransportAdapter


def _make_adapter() -> tuple[TextualTransportAdapter, MagicMock, MagicMock]:
    mock_app = MagicMock()
    mock_app.size.width = 120
    mock_log = MagicMock()
    return TextualTransportAdapter(app=mock_app, log=mock_log), mock_app, mock_log


class TestWrite:
    @pytest.mark.asyncio
    async def test_write_calls_log_write(self) -> None:
        adapter, _, mock_log = _make_adapter()
        await adapter.write("\x1b[1mhello\x1b[0m\n")
        mock_log.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_noop_when_closed(self) -> None:
        adapter, _, mock_log = _make_adapter()
        await adapter.close()
        await adapter.write("ignored")
        mock_log.write.assert_not_called()


class TestReadLine:
    @pytest.mark.asyncio
    async def test_returns_fed_value(self) -> None:
        adapter, _, _ = _make_adapter()
        adapter.feed("50")
        assert await adapter.read_line() == "50"

    @pytest.mark.asyncio
    async def test_strips_whitespace(self) -> None:
        adapter, _, _ = _make_adapter()
        adapter.feed("  h  ")
        assert await adapter.read_line() == "h"

    @pytest.mark.asyncio
    async def test_raises_when_closed(self) -> None:
        adapter, _, _ = _make_adapter()
        await adapter.close()
        with pytest.raises(ConnectionError):
            await adapter.read_line()


class TestReadChar:
    @pytest.mark.asyncio
    async def test_returns_first_char(self) -> None:
        adapter, _, _ = _make_adapter()
        adapter.feed("hit")
        assert await adapter.read_char() == "h"

    @pytest.mark.asyncio
    async def test_returns_newline_on_empty_feed(self) -> None:
        adapter, _, _ = _make_adapter()
        adapter.feed("")
        assert await adapter.read_char() == "\n"

    @pytest.mark.asyncio
    async def test_raises_when_closed(self) -> None:
        adapter, _, _ = _make_adapter()
        await adapter.close()
        with pytest.raises(ConnectionError):
            await adapter.read_char()


class TestWidth:
    def test_returns_app_size_width(self) -> None:
        adapter, mock_app, _ = _make_adapter()
        mock_app.size.width = 120
        assert adapter.width == 120

    def test_fallback_80_when_zero(self) -> None:
        adapter, mock_app, _ = _make_adapter()
        mock_app.size.width = 0
        assert adapter.width == 80


class TestClose:
    @pytest.mark.asyncio
    async def test_marks_closed(self) -> None:
        adapter, _, _ = _make_adapter()
        await adapter.close()
        assert adapter._closed is True

    @pytest.mark.asyncio
    async def test_calls_app_exit_via_call_later(self) -> None:
        adapter, mock_app, _ = _make_adapter()
        await adapter.close()
        mock_app.call_later.assert_called_once_with(mock_app.exit)

    @pytest.mark.asyncio
    async def test_idempotent(self) -> None:
        adapter, mock_app, _ = _make_adapter()
        await adapter.close()
        await adapter.close()
        mock_app.call_later.assert_called_once()


class TestIsolation:
    def test_no_subprocess_import(self) -> None:
        from termplay.frontends import textual_adapter
        source = inspect.getsource(textual_adapter)
        assert "import subprocess" not in source
        assert "from subprocess" not in source

    def test_no_shell_invocation(self) -> None:
        from termplay.frontends import textual_adapter
        source = inspect.getsource(textual_adapter)
        for pattern in ("/bin/sh", "shell=True", "Popen", "pty."):
            assert pattern not in source
