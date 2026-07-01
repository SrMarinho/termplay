"""Frontend TUI para termplay via Textual — solo embedded e multiplayer."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from textual.app import App
from textual.binding import Binding

import termplay.games.blackjack.plugin  # registra Blackjack no GameRegistry
import termplay.games.dominoes.plugin  # registra Dominó
import termplay.games.hangman.plugin  # registra Forca
import termplay.games.tictactoe.plugin  # registra Velha
import termplay.games.uno.plugin    # noqa: F401  # registra Uno
import termplay.games.truco.plugin  # noqa: F401  # registra Truco
from termplay.engine.protocol import ACTION_RECONNECT
from termplay.frontends.net import ServerConnection
from termplay.frontends.screens.home import HomeScreen

MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]


class TermplayTUIApp(App[None]):
    """TUI completo para termplay — solo e multiplayer."""

    TITLE = "termplay"

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("ctrl+q", "quit", "Sair", priority=True),
        Binding("ctrl+c", "quit", "Sair", priority=True, show=False),
        Binding("right", "focus_next", show=False),
        Binding("down", "focus_next", show=False),
        Binding("left", "focus_previous", show=False),
        Binding("up", "focus_previous", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.connection: ServerConnection | None = None
        self._msg_handler: MessageHandler | None = None
        self._embedded_server: object = None  # TermPlayServer | None, lazy import
        self._session_token: str | None = None
        self._last_addr: tuple[str, int] | None = None

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())

    def set_message_handler(self, handler: MessageHandler) -> None:
        """Registra quem recebe as próximas mensagens do servidor."""
        self._msg_handler = handler

    async def connect_server(self, host: str, port: int) -> bool:
        """Conecta ao servidor e inicia o listener central. False se falhar."""
        try:
            self.connection = await ServerConnection.connect(host, port)
        except OSError:
            return False
        self._last_addr = (host, port)
        self.run_worker(self._listen(), exclusive=False)
        return True

    async def start_embedded_server(
        self, port: int = 4443, game_name: str = "blackjack"
    ) -> int:
        """Inicia servidor TCP embutido (lazy). Retorna porta real em uso."""
        from termplay.engine.server import TermPlayServer

        server = TermPlayServer("0.0.0.0", port, game_name=game_name)
        try:
            await server.start()
        except OSError:
            server = TermPlayServer("0.0.0.0", 0, game_name=game_name)
            await server.start()
        self._embedded_server = server
        return server.actual_port

    async def stop_embedded_server(self) -> None:
        if self._embedded_server is not None:
            from termplay.engine.server import TermPlayServer

            if isinstance(self._embedded_server, TermPlayServer):
                # Bounded: never let a stuck shutdown freeze the terminal.
                with contextlib.suppress(TimeoutError, Exception):
                    await asyncio.wait_for(self._embedded_server.stop(), timeout=3.0)
            self._embedded_server = None

    async def action_quit(self) -> None:
        """Tear down networking with a timeout, then exit so the TTY restores."""
        with contextlib.suppress(Exception):
            await self.disconnect_server()
        self.exit()

    async def disconnect_server(self) -> None:
        self._session_token = None
        if self.connection is not None:
            await self.connection.close()
            self.connection = None
        self._msg_handler = None
        await self.stop_embedded_server()

    async def _listen(self) -> None:
        conn = self.connection
        while conn is not None:
            msg = await conn.recv()
            if msg is None:
                if await self._try_reconnect(conn):
                    conn = self.connection
                    continue
                if self._msg_handler is not None:
                    await self._msg_handler(
                        {"type": "error", "message": "Conexão encerrada", "fatal": True}
                    )
                break
            token = msg.get("session_token")
            if token:
                self._session_token = str(token)
            if self._msg_handler is not None:
                await self._msg_handler(msg)

    async def _try_reconnect(self, old_conn: ServerConnection) -> bool:
        """Rebind the session after a dropped connection. False when the drop
        was user-initiated, no token is known, or every attempt failed."""
        if self._session_token is None or self._last_addr is None:
            return False
        host, port = self._last_addr
        for delay in (0.5, 1.0, 2.0, 4.0):
            if self.connection is not old_conn:
                return False  # replaced or intentionally disconnected meanwhile
            await asyncio.sleep(delay)
            try:
                new_conn = await ServerConnection.connect(host, port)
            except OSError:
                continue
            await new_conn.send(action=ACTION_RECONNECT, token=self._session_token)
            self.connection = new_conn
            return True
        return False


def main() -> None:
    TermplayTUIApp().run()
