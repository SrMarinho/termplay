"""Testes do adaptador TCP — o mais crítico para segurança.

Verifica:
- Isolamento: sem shell, sem subprocess, sem eval
- Escrita/leitura correta
- Tratamento de desconexão
- Timeout
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from py21ssh.transport.tcp_adapter import TCPAdapter


class TestTCPAdapterIsolation:
    """Testes de isolamento — o adaptador NÃO deve expor shell/OS."""

    def test_no_subprocess_import(self) -> None:
        """O adaptador não deve importar subprocess."""
        import py21ssh.transport.tcp_adapter as mod

        source = ""
        if mod.__file__:
            with open(mod.__file__) as f:
                source = f.read()
        # Verifica import real, não a palavra no docstring
        assert "import subprocess" not in source
        assert "from subprocess" not in source
        assert "os.system" not in source
        assert "eval(" not in source
        assert "exec(" not in source

    def test_no_shell_invocation(self) -> None:
        """Verifica que o código não referencia shell."""
        import py21ssh.transport.tcp_adapter as mod

        source = ""
        if mod.__file__:
            with open(mod.__file__) as f:
                source = f.read()
        for dangerous in ("/bin/sh", "/bin/bash", "shell=True", "Popen", "pty."):
            assert dangerous not in source


# ── Helpers ──────────────────────────────────────────────


def _make_mock_writer() -> AsyncMock:
    """Cria um StreamWriter mockado para testes."""
    writer = MagicMock(spec=asyncio.StreamWriter)
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    return writer


def _make_mock_reader(data: bytes | None = None) -> AsyncMock:
    """Cria um StreamReader mockado."""
    reader = MagicMock(spec=asyncio.StreamReader)
    reader.readline = AsyncMock(return_value=data or b"")
    reader.readexactly = AsyncMock(return_value=data or b"")
    return reader


class TestTCPAdapterIO:
    """Testes de I/O do adaptador."""

    @pytest.mark.asyncio
    async def test_write_receives_data(self) -> None:
        """Escrever no adapter chama writer.write."""
        reader = _make_mock_reader()
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        await adapter.write("teste\n")
        writer.write.assert_called_once_with(b"teste\n")
        writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_write_handles_disconnect_silently(self) -> None:
        """Write em socket fechado não deve levantar exceção."""
        reader = _make_mock_reader()
        writer = _make_mock_writer()
        writer.drain = AsyncMock(side_effect=BrokenPipeError("desconectado"))
        adapter = TCPAdapter(reader, writer)

        # Não deve levantar exceção
        await adapter.write("qualquer coisa")
        # Deve marcar como fechado
        assert adapter._closed

    @pytest.mark.asyncio
    async def test_read_line_returns_data(self) -> None:
        """read_line retorna dados decodificados."""
        reader = _make_mock_reader(b"hit\n")
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        result = await adapter.read_line()
        assert result == "hit"

    @pytest.mark.asyncio
    async def test_read_line_empty_on_eof(self) -> None:
        """read_line retorna string vazia em EOF."""
        reader = _make_mock_reader(b"")  # EOF
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        result = await adapter.read_line()
        assert result == ""

    @pytest.mark.asyncio
    async def test_read_line_empty_when_closed(self) -> None:
        """read_line retorna string vazia quando já fechado."""
        reader = _make_mock_reader()
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        await adapter.close()
        result = await adapter.read_line()
        assert result == ""

    @pytest.mark.asyncio
    async def test_read_char_returns_char(self) -> None:
        """read_char retorna um caractere."""
        reader = _make_mock_reader(b"h")
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        result = await adapter.read_char()
        assert result == "h"

    @pytest.mark.asyncio
    async def test_read_char_handles_disconnect(self) -> None:
        """read_char retorna vazio em desconexão."""
        reader = _make_mock_reader()
        reader.readexactly = AsyncMock(side_effect=asyncio.IncompleteReadError(b"", 1))
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        result = await adapter.read_char()
        assert result == ""

    def test_terminal_width_default(self) -> None:
        """Largura padrão do terminal é 80."""
        adapter = TCPAdapter(reader=MagicMock(), writer=MagicMock())
        assert adapter.terminal_width == 80

    def test_terminal_width_custom(self) -> None:
        """Largura customizada é respeitada."""
        adapter = TCPAdapter(reader=MagicMock(), writer=MagicMock(), width=120)
        assert adapter.terminal_width == 120

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self) -> None:
        """close() pode ser chamado múltiplas vezes."""
        reader = _make_mock_reader()
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        await adapter.close()
        await adapter.close()  # segunda chamada não deve falhar
        assert writer.close.call_count == 1  # chamado só uma vez

    @pytest.mark.asyncio
    async def test_write_after_close_is_safe(self) -> None:
        """write após close não deve falhar."""
        reader = _make_mock_reader()
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        await adapter.close()
        # write após close não deve chamar writer.write (early return)
        await adapter.write("depois de fechado")  # apenas log warning
        writer.write.assert_not_called()  # close não escreve, write aborta

    @pytest.mark.asyncio
    async def test_read_line_handles_timeout(self) -> None:
        """read_line lida com timeout retornando vazio."""
        reader = _make_mock_reader()
        reader.readline = AsyncMock(side_effect=asyncio.TimeoutError)
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        result = await adapter.read_line()
        assert result == ""

    @pytest.mark.asyncio
    async def test_read_line_handles_connection_error(self) -> None:
        """read_line lida com ConnectionResetError."""
        reader = _make_mock_reader()
        reader.readline = AsyncMock(side_effect=ConnectionResetError("reset"))
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        result = await adapter.read_line()
        assert result == ""

    @pytest.mark.asyncio
    async def test_write_handles_oserror(self) -> None:
        """write lida com OSError genérico."""
        reader = _make_mock_reader()
        writer = _make_mock_writer()
        writer.drain = AsyncMock(side_effect=OSError("erro"))
        adapter = TCPAdapter(reader, writer)

        await adapter.write("dado")  # não deve levantar
        assert adapter._closed
