"""VelhaScreen — native Textual TUI for solo Velha with bot opponent."""

from __future__ import annotations

import asyncio
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.events import Key
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Header, Label, Static

from termplay.games.tictactoe.bot import VelhaBot
from termplay.games.tictactoe.state import TicTacToeState


class VelhaDifficultyModal(ModalScreen[str]):
    """Difficulty picker — dismisses with 'easy' or 'hard'."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("left",  "focus_previous", ""),
        ("right", "focus_next",     ""),
        ("up",    "focus_previous", ""),
        ("down",  "focus_next",     ""),
    ]

    DEFAULT_CSS = """
    VelhaDifficultyModal {
        align: center middle;
    }
    VelhaDifficultyModal #box {
        width: 36;
        height: auto;
        padding: 1 2;
        border: thick $accent;
        background: $surface;
    }
    VelhaDifficultyModal #title {
        width: 1fr;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    VelhaDifficultyModal #btns {
        height: auto;
        width: 1fr;
        margin-top: 1;
    }
    VelhaDifficultyModal #btns Button {
        width: 1fr;
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label("Difficulty", id="title")
            with Horizontal(id="btns"):
                yield Button("Easy", id="easy", variant="success")
                yield Button("Hard", id="hard", variant="error")

    def on_mount(self) -> None:
        self.query_one("#easy", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id or "easy")

    def action_focus_next(self) -> None:
        self.focus_next()

    def action_focus_previous(self) -> None:
        self.focus_previous()


class VelhaScreen(Screen[None]):
    """Solo Velha: human (X) vs bot (O). Arrow keys move cursor, Enter places mark."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "leave", "Quit"),
    ]

    DEFAULT_CSS = """
    VelhaScreen {
        align: center middle;
    }
    VelhaScreen #outer {
        width: auto;
        height: auto;
        align: center middle;
    }
    VelhaScreen #info {
        text-align: center;
        width: 1fr;
        margin-bottom: 1;
    }
    VelhaScreen #board {
        grid-size: 3 3;
        grid-gutter: 1;
        width: 21;
        height: 11;
        margin: 0 auto;
    }
    VelhaScreen .cell {
        width: 5;
        height: 3;
        border: solid $panel;
        content-align: center middle;
        text-align: center;
        text-style: bold;
    }
    VelhaScreen .cell.cursor {
        border: solid $accent;
        background: $accent 20%;
    }
    VelhaScreen .cell.mark-x {
        color: $error;
    }
    VelhaScreen .cell.mark-o {
        color: $primary;
    }
    VelhaScreen #status {
        text-align: center;
        width: 1fr;
        margin-top: 1;
    }
    VelhaScreen #actions {
        display: none;
        height: auto;
        align: center middle;
        margin-top: 1;
        width: 1fr;
    }
    VelhaScreen #actions Button {
        margin: 0 1;
    }
    """

    def __init__(self, difficulty: str = "easy") -> None:
        super().__init__()
        self._difficulty = difficulty
        self._state = TicTacToeState()
        self._cursor = 4
        self._game_over = False
        self._bot_thinking = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="outer"):
            yield Label("You: X   Bot: O", id="info")
            with Grid(id="board"):
                for i in range(9):
                    yield Static(str(i + 1), id=f"cell-{i}", classes="cell")
            yield Label("Your turn (X)", id="status")
            with Horizontal(id="actions"):
                yield Button("New Game", id="restart", variant="success")
                yield Button("Quit", id="quit", variant="error")

    def on_mount(self) -> None:
        self._refresh_board()

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            return
        if self._game_over:
            return
        if event.key in ("up", "down", "left", "right", "enter", "space"):
            event.stop()
        if event.key == "up":
            self._cursor = (self._cursor - 3) % 9
            self._refresh_board()
        elif event.key == "down":
            self._cursor = (self._cursor + 3) % 9
            self._refresh_board()
        elif event.key == "left":
            row, col = divmod(self._cursor, 3)
            self._cursor = row * 3 + (col - 1) % 3
            self._refresh_board()
        elif event.key == "right":
            row, col = divmod(self._cursor, 3)
            self._cursor = row * 3 + (col + 1) % 3
            self._refresh_board()
        elif event.key in ("enter", "space"):
            self._try_place()

    def _try_place(self) -> None:
        if self._bot_thinking:
            return
        if self._state.cells[self._cursor] != " ":
            return
        self._state.place(self._cursor, "X")
        self._refresh_board()
        if self._check_end():
            return
        self._bot_thinking = True
        self.query_one("#status", Label).update("Bot thinking...")
        self.run_worker(self._bot_turn(), exclusive=True)

    async def _bot_turn(self) -> None:
        await asyncio.sleep(0.4)
        if self._difficulty == "hard":
            idx = VelhaBot.hard_move(self._state.cells[:], "O")
        else:
            idx = VelhaBot.easy_move(self._state.cells[:])
        self._state.place(idx, "O")
        self._bot_thinking = False
        self._refresh_board()
        self._check_end()

    def _check_end(self) -> bool:
        winner = self._state.winner()
        if winner:
            self._game_over = True
            msg = "You win! 🏆" if winner == "X" else "Bot wins!"
            self.query_one("#status", Label).update(msg)
            self.query_one("#actions").display = True
            return True
        if self._state.is_full:
            self._game_over = True
            self.query_one("#status", Label).update("Draw!")
            self.query_one("#actions").display = True
            return True
        self.query_one("#status", Label).update("Your turn (X)")
        return False

    def _refresh_board(self) -> None:
        for i in range(9):
            w = self.query_one(f"#cell-{i}", Static)
            c = self._state.cells[i]
            w.remove_class("cursor", "mark-x", "mark-o")
            if c == "X":
                w.update("X")
                w.add_class("mark-x")
            elif c == "O":
                w.update("O")
                w.add_class("mark-o")
            else:
                w.update(str(i + 1))
                if i == self._cursor:
                    w.add_class("cursor")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "restart":
            self._state = TicTacToeState()
            self._game_over = False
            self._bot_thinking = False
            self._cursor = 4
            self.query_one("#actions").display = False
            self.query_one("#status", Label).update("Your turn (X)")
            self._refresh_board()
        elif event.button.id == "quit":
            self.app.pop_screen()

    def action_leave(self) -> None:
        self.app.pop_screen()
