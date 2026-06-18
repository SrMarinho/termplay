"""MultiplayerMenuScreen — escolha criar ou entrar em sala."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Label


class MultiplayerMenuScreen(Screen[None]):
    """Lobby multiplayer: cria sala (P2P host) ou entra em sala existente."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "pop_screen", "Voltar"),
        ("left",  "focus_previous", ""),
        ("right", "focus_next",     ""),
        ("up",    "focus_previous", ""),
        ("down",  "focus_next",     ""),
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
            Label("Multiplayer"),
            Horizontal(
                Button("Criar Sala", id="create", variant="primary"),
                Button("Entrar em Sala", id="join", variant="default"),
            ),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            from termplay.frontends.screens.create_room import CreateRoomScreen

            self.app.push_screen(CreateRoomScreen())
        elif event.button.id == "join":
            from termplay.frontends.screens.join_room import JoinRoomScreen

            self.app.push_screen(JoinRoomScreen())

    def action_pop_screen(self) -> None:
        self.app.pop_screen()

    def action_focus_next(self) -> None:
        self.focus_next()

    def action_focus_previous(self) -> None:
        self.focus_previous()
