"""Testes do adaptador TCP — o mais crítico para segurança.

Verifica:
- Isolamento: sem shell, sem subprocess, sem eval
- Escrita/leitura correta
- Tratamento de desconexão e erros
- Interface ITransportAdapter respeitada
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from termplay.engine.transport.tcp_adapter import TCPAdapter, create_tcp_adapter


class TestTCPAdapterIsolation:
    """Testes de isolamento — o adaptador NÃO deve expor shell/OS."""

    def test_no_subprocess_import(self) -> None:
        """O adaptador não deve importar subprocess."""
        import termplay.engine.transport.tcp_adapter as mod

        source = ""
        if mod.__file__:
            with open(mod.__file__) as f:
                source = f.read()
        assert "import subprocess" not in source
        assert "from subprocess" not in source
        assert "os.system" not in source
        assert "eval(" not in source
        assert "exec(" not in source

    def test_no_shell_invocation(self) -> None:
        """Verifica que o código não referencia shell."""
        import termplay.engine.transport.tcp_adapter as mod

        source = ""
        if mod.__file__:
            with open(mod.__file__) as f:
                source = f.read()
        for dangerous in ("/bin/sh", "/bin/bash", "shell=True", "Popen", "pty."):
            assert dangerous not in source


# ── Helpers ──────────────────────────────────────────────


def _make_mock_writer() -> MagicMock:
    """Cria um StreamWriter mockado para testes."""
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    return writer


def _make_mock_reader(data: bytes | None = None) -> MagicMock:
    """Cria um StreamReader mockado."""
    reader = MagicMock()
    reader.readline = AsyncMock(return_value=data or b"")
    reader.read = AsyncMock(return_value=data or b"")
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
    async def test_write_handles_connection_error_silently(self) -> None:
        """Write em conexão quebrada não deve levantar exceção."""
        reader = _make_mock_reader()
        writer = _make_mock_writer()
        writer.drain = AsyncMock(side_effect=ConnectionError("desconectado"))
        adapter = TCPAdapter(reader, writer)

        # Não deve levantar exceção
        await adapter.write("qualquer coisa")

    @pytest.mark.asyncio
    async def test_read_line_returns_data(self) -> None:
        """read_line retorna dados decodificados."""
        reader = _make_mock_reader(b"hit\n")
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        result = await adapter.read_line()
        assert result == "hit"

    @pytest.mark.asyncio
    async def test_read_line_raises_on_eof(self) -> None:
        """read_line lança ConnectionError em EOF."""
        reader = _make_mock_reader(b"")  # EOF
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        with pytest.raises(ConnectionError):
            await adapter.read_line()

    @pytest.mark.asyncio
    async def test_read_line_raises_when_closed(self) -> None:
        """read_line lança ConnectionError quando já fechado."""
        reader = _make_mock_reader()
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        await adapter.close()
        with pytest.raises(ConnectionError):
            await adapter.read_line()

    @pytest.mark.asyncio
    async def test_read_char_returns_char(self) -> None:
        """read_char retorna um caractere."""
        reader = _make_mock_reader()
        reader.read = AsyncMock(return_value=b"h")
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        result = await adapter.read_char()
        assert result == "h"

    @pytest.mark.asyncio
    async def test_read_char_raises_on_disconnect(self) -> None:
        """read_char lança ConnectionError em desconexão."""
        reader = _make_mock_reader()
        reader.read = AsyncMock(return_value=b"")  # EOF
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        with pytest.raises(ConnectionError):
            await adapter.read_char()

    def test_width_default_80(self) -> None:
        """Largura padrão do terminal é 80."""
        adapter = TCPAdapter(reader=MagicMock(), writer=MagicMock())
        assert adapter.width == 80

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self) -> None:
        """close() pode ser chamado múltiplas vezes sem erro."""
        reader = _make_mock_reader()
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        await adapter.close()
        await adapter.close()  # segunda chamada não deve falhar
        # writer.close chamado 1x na primeira, não novamente
        assert writer.close.call_count == 1

    @pytest.mark.asyncio
    async def test_write_after_close_is_safe(self) -> None:
        """write após close não deve falhar e não deve escrever."""
        reader = _make_mock_reader()
        writer = _make_mock_writer()
        adapter = TCPAdapter(reader, writer)

        await adapter.close()
        await adapter.write("depois de fechado")  # log warning, sem erro
        writer.write.assert_not_called()

    @pytest.mark.asyncio
    async def test_factory_creates_adapter(self) -> None:
        """create_tcp_adapter retorna um TCPAdapter válido."""
        reader = _make_mock_reader()
        writer = _make_mock_writer()
        adapter = create_tcp_adapter(reader, writer)

        assert isinstance(adapter, TCPAdapter)
        assert adapter.width == 80
