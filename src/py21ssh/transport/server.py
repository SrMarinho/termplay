"""TCPServer — servidor TCP que aceita conexões e inicia sessões de jogo.

Sem shell, sem subprocess, sem eval.
Apenas asyncio.start_server que entrega StreamReader/Writer para o TCPAdapter.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from py21ssh.application.session_manager import run_session
from py21ssh.display.renderer import RichRenderer
from py21ssh.transport.tcp_adapter import TCPAdapter

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class TCPServer:
    """Servidor TCP que aceita conexões e inicia sessões de Blackjack.

    Attributes:
        host: IP para escutar (padrão: todas interfaces).
        port: porta TCP (padrão: 4443).
        max_concurrent: máximo de sessões simultâneas.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 4443,
        max_concurrent: int = 10,
    ) -> None:
        self.host = host
        self.port = port
        self._max_concurrent = max_concurrent
        self._server: asyncio.AbstractServer | None = None
        self._active_sessions: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        """Inicia o servidor TCP."""
        self._server = await asyncio.start_server(
            self._on_connect,
            host=self.host,
            port=self.port,
        )
        addr = (
            self._server.sockets[0].getsockname()
            if self._server.sockets
            else ("?", "?")
        )
        logger.info(
            "Servidor TCP rodando em %s:%s — máximo %d sessões simultâneas",
            addr[0],
            addr[1],
            self._max_concurrent,
        )

    async def serve_forever(self) -> None:
        """Mantém o servidor rodando até ser interrompido."""
        if self._server is None:
            raise RuntimeError("Servidor não iniciado. Chame start() primeiro.")
        try:
            await self._server.serve_forever()
        except asyncio.CancelledError:
            logger.info("Servidor interrompido")
            await self.stop()

    async def stop(self) -> None:
        """Para o servidor e todas as sessões ativas."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Cancela sessões ativas
        if self._active_sessions:
            for task in self._active_sessions:
                task.cancel()
            await asyncio.gather(*self._active_sessions, return_exceptions=True)
            self._active_sessions.clear()

        logger.info("Servidor parou. Sessões ativas encerradas.")

    async def _on_connect(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Callback chamado para cada nova conexão TCP.

        Cria um TCPAdapter, um RichRenderer, e inicia a sessão.
        """
        addr = writer.get_extra_info("peername") or ("desconhecido", 0)
        logger.info("Nova conexão de %s:%s", addr[0], addr[1])

        # Verifica limite de sessões
        if len(self._active_sessions) >= self._max_concurrent:
            logger.warning(
                "Limite de sessões atingido — rejeitando %s:%s",
                addr[0],
                addr[1],
            )
            try:
                writer.write(b"Limite de jogadores atingido. Tente mais tarde.\n")
                await writer.drain()
            except OSError:
                pass
            writer.close()
            return

        adapter = TCPAdapter(reader, writer)
        renderer = RichRenderer(width=adapter.terminal_width)

        task = asyncio.create_task(
            self._run_session_task(adapter, renderer, addr),
            name=f"sessao-{addr[0]}:{addr[1]}",
        )
        self._active_sessions.add(task)
        task.add_done_callback(self._active_sessions.discard)

    async def _run_session_task(
        self,
        adapter: TCPAdapter,
        renderer: RichRenderer,
        addr: tuple[str | int, int],
    ) -> None:
        """Executa a sessão em uma task isolada."""
        try:
            await run_session(adapter, renderer)
        except asyncio.CancelledError:
            logger.info("Sessão %s:%s cancelada", addr[0], addr[1])
        except Exception:
            logger.exception("Erro na sessão %s:%s", addr[0], addr[1])
        finally:
            await adapter.close()
