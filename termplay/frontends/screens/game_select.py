"""GameSelectScreen — tabela de jogos com navegação por setas."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.events import Key
from textual.screen import Screen
from textual.widgets import DataTable, Header, Input

import termplay.games.blackjack.plugin
import termplay.games.hangman.plugin
import termplay.games.tictactoe.plugin
import termplay.games.uno.plugin  # noqa: F401
from termplay.engine.registry import GameRegistry


class GameSelectScreen(Screen[str | None]):
    """Game list: arrow keys navigate, type to filter, Enter to select."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "cancel", "Back")
    ]

    DEFAULT_CSS = """
    GameSelectScreen {
        layout: vertical;
    }
    GameSelectScreen #search {
        height: 3;
        dock: none;
    }
    GameSelectScreen DataTable {
        height: 1fr;
    }
    """

    def __init__(self, select_mode: bool = False) -> None:
        super().__init__()
        self._select_mode = select_mode
        self._all_games: list[tuple[str, str]] = GameRegistry.list_games()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Pesquisar...", id="search")
        yield DataTable(id="games", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one("#games", DataTable)
        table.add_column("Jogo", width=20)
        table.add_column("Descrição")
        for name, desc in self._all_games:
            table.add_row(name, desc, key=name)
        table.focus()

    def on_key(self, event: Key) -> None:
        search = self.query_one("#search", Input)
        if self.focused is search:
            return
        if event.is_printable and event.character:
            search.value += event.character
            self._apply_filter(search.value)
            event.prevent_default()
        elif event.key == "backspace":
            search.value = search.value[:-1]
            self._apply_filter(search.value)
            event.prevent_default()

    def _apply_filter(self, query: str) -> None:
        q = query.strip().lower()
        table = self.query_one("#games", DataTable)
        table.clear()
        for name, desc in self._all_games:
            if not q or q in name.lower() or q in desc.lower():
                table.add_row(name, desc, key=name)

    def on_input_changed(self, event: Input.Changed) -> None:
        self._apply_filter(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#games", DataTable).focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        game_name = str(event.row_key.value)
        if self._select_mode:
            self.dismiss(game_name)
            return
        game_class = GameRegistry.get(game_name)
        if game_class is None:
            return
        if game_name.lower() == "uno":
            from termplay.frontends.screens.uno_screen import BotCountModal, UnoSoloScreen

            def start(num: int | None) -> None:
                self.app.push_screen(UnoSoloScreen(num_bots=num or 1))

            self.app.push_screen(BotCountModal(), start)
        else:
            from termplay.frontends.screens.game import GameScreen
            self.app.push_screen(GameScreen(game_class))

    def action_cancel(self) -> None:
        if self._select_mode:
            self.dismiss(None)
        else:
            self.app.pop_screen()
