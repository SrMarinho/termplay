"""TCPAdapter — adaptador de transporte sobre asyncio TCP.

NÃO possui shell, NÃO executa subprocessos.
Apenas conecta asyncio.StreamReader/Writer ao protocolo ITransportAdapter.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from py21ssh.conf import CONSOLE_WIDTH

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class TCPAdapter:
    """Adaptador que conecta um socket TCP ao protocolo ITransportAdapter.

    Lê linhas do cliente, escreve ANSI para o cliente.
    Zero shell, zero subprocess, zero eval.
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        *,
        width: int = CONSOLE_WIDTH,
        encoding: str = "utf-8",
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._encoding = encoding
        self._width = width
        self._closed = False

    async def write(self, text: str) -> None:
        """Envia texto ANSI para o cliente."""
        if self._closed:
            logger.warning("Tentativa de escrever em socket fechado")
            return
        try:
            self._writer.write(text.encode(self._encoding))
            await self._writer.drain()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as exc:
            logger.info("Cliente desconectado durante write: %s", exc)
            self._closed = True
        except OSError as exc:
            logger.warning("Erro de I/O no write: %s", exc)
            self._closed = True

    async def read_line(self) -> str:
        """Lê uma linha de entrada do cliente (terminada em \\n).

        Returns:
            Linha decodificada e sem espaços extras, ou string vazia se EOF.

        Raises:
            ConnectionError: se a conexão foi fechada.
        """
        if self._closed:
            return ""
        try:
            data = await asyncio.wait_for(self._reader.readline(), timeout=300)
            if not data:
                self._closed = True
                return ""
            return data.decode(self._encoding).strip("\r\n")
        except TimeoutError:
            logger.info("Timeout de leitura — encerrando sessão")
            self._closed = True
            return ""
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as exc:
            logger.info("Cliente desconectado durante leitura: %s", exc)
            self._closed = True
            return ""

    async def read_char(self) -> str:
        """Lê um caractere do cliente (sem esperar Enter).

        Nota: em TCP puro (nc/telnet), caracteres são enviados por linha.
        Esta implementação lê 1 byte por vez.

        Returns:
            Caractere lido, ou string vazia se EOF/timeout.
        """
        if self._closed:
            return ""
        try:
            data = await asyncio.wait_for(self._reader.readexactly(1), timeout=300)
            return data.decode(self._encoding)
        except asyncio.IncompleteReadError:
            self._closed = True
            return ""
        except TimeoutError:
            logger.info("Timeout de leitura char")
            self._closed = True
            return ""
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as exc:
            logger.info("Cliente desconectado: %s", exc)
            self._closed = True
            return ""

    @property
    def terminal_width(self) -> int:
        """Largura do terminal do cliente (fixa para TCP)."""
        return self._width

    async def close(self) -> None:
        """Fecha a conexão TCP."""
        if self._closed:
            return
        self._closed = True
        with contextlib.suppress(OSError):
            self._writer.close()
