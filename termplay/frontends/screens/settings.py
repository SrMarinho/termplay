"""SettingsScreen — configuração do usuário (nickname)."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Input, Label, Switch

from termplay.config.settings import (
    get_nickname,
    get_stealth,
    set_nickname,
    set_stealth,
)


class SettingsScreen(Screen[None]):
    """Permite alterar e salvar o nickname entre execuções."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "pop_screen", "Voltar")
    ]

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
    }
    SettingsScreen Vertical {
        width: 50;
        height: auto;
        border: round $primary;
        padding: 1 2;
    }
    SettingsScreen #stealth-row {
        height: auto;
        margin-top: 1;
    }
    SettingsScreen #stealth-row Label {
        width: 1fr;
        content-align: left middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Configuração"),
            Label(""),
            Label("Nickname:"),
            Input(value=get_nickname(), id="nick", placeholder="seu nickname"),
            Horizontal(
                Label("Modo disfarce (logs):"),
                Switch(value=get_stealth(), id="stealth"),
                id="stealth-row",
            ),
            Label(""),
            Button("Salvar", id="save", variant="primary"),
        )

    def on_mount(self) -> None:
        self.query_one("#nick", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self._save()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._save()

    def _save(self) -> None:
        nick = self.query_one("#nick", Input).value.strip()
        set_nickname(nick)
        set_stealth(self.query_one("#stealth", Switch).value)
        self.app.pop_screen()

    def action_pop_screen(self) -> None:
        self.app.pop_screen()
