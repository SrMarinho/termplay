"""JoinRoomScreen — conecta direto ao host P2P e entra na sala."""

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
    """Coleta nome + IP:porta do host, conecta e entra na sala de espera."""

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

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Entrar em Sala"),
            Label(""),
            Label("Seu nome:"),
            Input(value=get_nickname(), id="name", placeholder="nome do jogador"),
            Label("IP do host:"),
            Input(id="host", placeholder="ex: 192.168.1.42"),
            Label("Porta:"),
            Input(value="4443", id="port", placeholder="4443"),
            Label(""),
            Button("Entrar", id="join", variant="primary"),
            Label("", id="status"),
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "join":
            await self._join()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "name":
            self.query_one("#host", Input).focus()
        elif event.input.id == "host":
            self.query_one("#port", Input).focus()
        else:
            await self._join()

    async def _join(self) -> None:
        name = self.query_one("#name", Input).value.strip() or "Player"
        host = self.query_one("#host", Input).value.strip()
        if not host:
            self.query_one("#status", Label).update("Digite o IP do host.")
            return
        try:
            port = int(self.query_one("#port", Input).value.strip())
        except ValueError:
            port = 4443

        app = cast("TermplayTUIApp", self.app)
        ok = await app.connect_server(host, port)
        if not ok:
            self.query_one("#status", Label).update(
                f"Falha ao conectar em {host}:{port}"
            )
            return

        assert app.connection is not None
        # Envia código vazio → server P2P auto-join na única sala disponível
        await app.connection.send(action=ACTION_JOIN_ROOM, name=name, code="")

        from termplay.frontends.screens.waiting_room import WaitingRoomScreen

        app.push_screen(WaitingRoomScreen(my_name=name, is_host=False))

    def action_pop_screen(self) -> None:
        self.app.pop_screen()
