"""CreateRoomScreen — conecta ao servidor e cria sala."""

from __future__ import annotations

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


class CreateRoomScreen(Screen[None]):
    """Coleta o nome, conecta ao servidor e abre a sala de espera."""

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

    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self._host = host
        self._port = port

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
        ok = await app.connect_server(self._host, self._port)
        if not ok:
            self.query_one("#status", Label).update(
                f"Falha ao conectar em {self._host}:{self._port}"
            )
            return
        assert app.connection is not None
        await app.connection.send(action=ACTION_CREATE_ROOM, name=name)
        from termplay.frontends.screens.waiting_room import WaitingRoomScreen

        app.push_screen(WaitingRoomScreen(my_name=name, is_host=True))

    def action_pop_screen(self) -> None:
        self.app.pop_screen()
