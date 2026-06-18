"""MultiplayerMenuScreen — escolha criar ou entrar em sala."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Input, Label


class MultiplayerMenuScreen(Screen[None]):
    """Lobby multiplayer: configura servidor e cria ou entra em sala."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "pop_screen", "Voltar")
    ]

    DEFAULT_CSS = """
    MultiplayerMenuScreen {
        align: center middle;
    }
    MultiplayerMenuScreen Vertical {
        width: 50;
        height: auto;
        border: round $primary;
        padding: 1 2;
    }
    MultiplayerMenuScreen Label.section {
        margin-top: 1;
        color: $text-muted;
    }
    MultiplayerMenuScreen Horizontal {
        height: auto;
        margin-top: 1;
    }
    MultiplayerMenuScreen Horizontal Button {
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Servidor", classes="section"),
            Input(value="127.0.0.1", id="host", placeholder="host ou IP"),
            Input(value="4443", id="port", placeholder="porta"),
            Horizontal(
                Button("Criar Sala", id="create", variant="primary"),
                Button("Entrar em Sala", id="join", variant="default"),
            ),
        )

    def _server(self) -> tuple[str, int]:
        host = self.query_one("#host", Input).value.strip() or "127.0.0.1"
        try:
            port = int(self.query_one("#port", Input).value.strip())
        except ValueError:
            port = 4443
        return host, port

    def on_button_pressed(self, event: Button.Pressed) -> None:
        host, port = self._server()
        if event.button.id == "create":
            from termplay.frontends.screens.create_room import CreateRoomScreen
            self.app.push_screen(CreateRoomScreen(host, port))
        elif event.button.id == "join":
            from termplay.frontends.screens.join_room import JoinRoomScreen
            self.app.push_screen(JoinRoomScreen(host, port))

    def action_pop_screen(self) -> None:
        self.app.pop_screen()
