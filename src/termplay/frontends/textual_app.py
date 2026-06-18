"""Frontend TUI para termplay via Textual — solo embedded e multiplayer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from textual.app import App

import termplay.games.blackjack.plugin  # noqa: F401  # registra Blackjack no GameRegistry
from termplay.frontends.net import ServerConnection
from termplay.frontends.screens.home import HomeScreen

MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]


class TermplayTUIApp(App[None]):
    """TUI completo para termplay — solo e multiplayer."""

    TITLE = "termplay"

    def __init__(self) -> None:
        super().__init__()
        self.connection: ServerConnection | None = None
        self._msg_handler: MessageHandler | None = None

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
        self.run_worker(self._listen(), exclusive=False)
        return True

    async def disconnect_server(self) -> None:
        if self.connection is not None:
            await self.connection.close()
            self.connection = None
        self._msg_handler = None

    async def _listen(self) -> None:
        conn = self.connection
        while conn is not None:
            msg = await conn.recv()
            if msg is None:
                if self._msg_handler is not None:
                    await self._msg_handler(
                        {"type": "error", "message": "Conexão encerrada", "fatal": True}
                    )
                break
            if self._msg_handler is not None:
                await self._msg_handler(msg)


def main() -> None:
    TermplayTUIApp().run()
