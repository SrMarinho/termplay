"""CreateRoomScreen — inicia servidor P2P embutido e cria a sala."""

from __future__ import annotations

import contextlib
import socket
from typing import TYPE_CHECKING, ClassVar, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Input, Label

from termplay.config.settings import get_nickname
from termplay.engine.protocol import ACTION_CREATE_ROOM

if TYPE_CHECKING:
    from termplay.frontends.textual_app import TermplayTUIApp


def _get_local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s, contextlib.suppress(
        Exception
    ):
        s.connect(("8.8.8.8", 80))
        return str(s.getsockname()[0])
    return "127.0.0.1"


class CreateRoomScreen(Screen[None]):
    """Coleta o nome, inicia servidor embutido e abre a sala de espera."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "pop_screen", "Voltar")
    ]

    DEFAULT_CSS = """
    CreateRoomScreen {
        align: center middle;
    }
    CreateRoomScreen Vertical {
        width: 50;
        height: auto;
        border: round $primary;
        padding: 1 2;
    }
    CreateRoomScreen #status {
        color: $error;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Criar Sala"),
            Label(""),
            Label("Seu nome:"),
            Input(value=get_nickname(), id="name", placeholder="nome do jogador"),
            Label(""),
            Button("Criar", id="create", variant="primary"),
            Label("", id="status"),
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            await self._create()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self._create()

    async def _create(self) -> None:
        name = self.query_one("#name", Input).value.strip() or "Host"
        app = cast("TermplayTUIApp", self.app)

        status = self.query_one("#status", Label)
        status.update("Iniciando servidor...")

        try:
            port = await app.start_embedded_server()
        except Exception:
            status.update("Falha ao iniciar o servidor.")
            return

        local_ip = _get_local_ip()
        ok = await app.connect_server("127.0.0.1", port)
        if not ok:
            await app.stop_embedded_server()
            status.update("Falha ao conectar ao servidor local.")
            return

        assert app.connection is not None
        await app.connection.send(action=ACTION_CREATE_ROOM, name=name)

        from termplay.frontends.screens.waiting_room import WaitingRoomScreen

        app.push_screen(
            WaitingRoomScreen(
                my_name=name,
                is_host=True,
                host_addr=f"{local_ip}:{port}",
            )
        )

    def action_pop_screen(self) -> None:
        self.app.pop_screen()
