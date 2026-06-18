"""JoinRoomScreen — conecta ao servidor e entra em sala existente."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Input, Label

from termplay.config.settings import get_nickname
from termplay.engine.protocol import ACTION_JOIN_ROOM

if TYPE_CHECKING:
    from termplay.frontends.textual_app import TermplayTUIApp


class JoinRoomScreen(Screen[None]):
    """Coleta nome + código, conecta e entra na sala de espera."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "pop_screen", "Voltar")
    ]

    DEFAULT_CSS = """
    JoinRoomScreen {
        align: center middle;
    }
    JoinRoomScreen Vertical {
        width: 50;
        height: auto;
        border: round $primary;
        padding: 1 2;
    }
    JoinRoomScreen #status {
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
            Label("Entrar em Sala"),
            Label(""),
            Label("Seu nome:"),
            Input(value=get_nickname(), id="name", placeholder="nome do jogador"),
            Label("Código da sala:"),
            Input(id="code", placeholder="ex: AB12", max_length=4),
            Label(""),
            Button("Entrar", id="join", variant="primary"),
            Label("", id="status"),
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "join":
            await self._join()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "name":
            self.query_one("#code", Input).focus()
        else:
            await self._join()

    async def _join(self) -> None:
        name = self.query_one("#name", Input).value.strip() or "Player"
        code = self.query_one("#code", Input).value.strip().upper()
        if not code:
            self.query_one("#status", Label).update("Digite o código da sala.")
            return
        app = cast("TermplayTUIApp", self.app)
        ok = await app.connect_server(self._host, self._port)
        if not ok:
            self.query_one("#status", Label).update(
                f"Falha ao conectar em {self._host}:{self._port}"
            )
            return
        assert app.connection is not None
        await app.connection.send(action=ACTION_JOIN_ROOM, name=name, code=code)
        from termplay.frontends.screens.waiting_room import WaitingRoomScreen

        app.push_screen(WaitingRoomScreen(my_name=name, is_host=False))

    def action_pop_screen(self) -> None:
        self.app.pop_screen()
