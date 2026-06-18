"""HomeScreen — tela inicial do termplay-tui."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Button, Header, Label


class HomeScreen(Screen[None]):
    """Tela inicial: solo ou multiplayer."""

    DEFAULT_CSS = """
    HomeScreen {
        align: center middle;
    }
    HomeScreen Vertical {
        width: 44;
        height: auto;
        border: solid green;
        padding: 2 4;
        align: center middle;
    }
    HomeScreen Label#title {
        content-align: center middle;
        width: 100%;
        text-style: bold;
        margin-bottom: 2;
    }
    HomeScreen Button {
        width: 100%;
        margin-bottom: 1;
    }
    """

    _BUTTONS: ClassVar[list[str]] = ["solo", "multi", "config", "quit"]

    def on_mount(self) -> None:
        self.query_one("#solo", Button).focus()

    def on_key(self, event: Key) -> None:
        focused = self.focused
        if not isinstance(focused, Button) or focused.id not in self._BUTTONS:
            return
        idx = self._BUTTONS.index(focused.id)
        if event.key == "down":
            nxt = self._BUTTONS[(idx + 1) % len(self._BUTTONS)]
            self.query_one(f"#{nxt}", Button).focus()
            event.prevent_default()
        elif event.key == "up":
            prv = self._BUTTONS[(idx - 1) % len(self._BUTTONS)]
            self.query_one(f"#{prv}", Button).focus()
            event.prevent_default()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("🎮  termplay", id="title"),
            Button("Jogar Solo", id="solo", variant="primary"),
            Button("🌐 Multiplayer", id="multi", variant="default"),
            Button("⚙ Configuração", id="config", variant="default"),
            Button("Sair", id="quit", variant="warning"),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "solo":
            from termplay.frontends.screens.game_select import GameSelectScreen

            self.app.push_screen(GameSelectScreen())
        elif event.button.id == "multi":
            from termplay.frontends.screens.multiplayer_menu import (
                MultiplayerMenuScreen,
            )
            self.app.push_screen(MultiplayerMenuScreen())
        elif event.button.id == "config":
            from termplay.frontends.screens.settings import SettingsScreen

            self.app.push_screen(SettingsScreen())
        elif event.button.id == "quit":
            self.app.exit()
