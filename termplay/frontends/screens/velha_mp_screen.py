"""VelhaMpScreen — multiplayer Velha TUI. Renders JSON state from server."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Button, Header, Label, RichLog, Static

from termplay.config.settings import get_stealth
from termplay.engine.protocol import ACTION_GAME_INPUT, TYPE_ERROR, TYPE_GAME_OVER, TYPE_GAME_RENDER

if TYPE_CHECKING:
    from termplay.frontends.textual_app import TermplayTUIApp

_VELHA_TAG = "velha.state"


class VelhaMpScreen(Screen[None]):
    """Multiplayer Velha: native grid + arrow-key navigation. Sends moves to server."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "leave", "Quit"),
    ]

    DEFAULT_CSS = """
    VelhaMpScreen {
        align: center middle;
    }
    VelhaMpScreen #outer {
        width: auto;
        height: auto;
        align: center middle;
    }
    VelhaMpScreen #board {
        grid-size: 3 3;
        grid-gutter: 1;
        width: 21;
        height: 11;
        margin: 0 auto;
    }
    VelhaMpScreen .cell {
        width: 5;
        height: 3;
        border: solid $panel;
        content-align: center middle;
        text-align: center;
        text-style: bold;
    }
    VelhaMpScreen .cell.cursor {
        border: solid $accent;
        background: $accent 20%;
    }
    VelhaMpScreen .cell.mark-x {
        color: $error;
    }
    VelhaMpScreen .cell.mark-o {
        color: $primary;
    }
    VelhaMpScreen #status {
        text-align: center;
        width: 1fr;
        margin-top: 1;
    }
    VelhaMpScreen #quit-btn {
        margin-top: 1;
        width: auto;
    }
    VelhaMpScreen #stealth-log {
        display: none;
        height: 1fr;
    }
    VelhaMpScreen.stealth #outer {
        display: none;
    }
    VelhaMpScreen.stealth #stealth-log {
        display: block;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._cursor = 4
        self._cells: list[str] = [" "] * 9
        self._my_mark = ""
        self._my_turn = False
        self._game_over = False
        self._mounted = False
        self._pending: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="outer"):
            yield Label("TIC-TAC-TOE", id="title")
            with Grid(id="board"):
                for i in range(9):
                    yield Static(str(i + 1), id=f"cell-{i}", classes="cell")
            yield Label("Waiting...", id="status")
            yield Button("Quit [Esc]", id="quit-btn", variant="error")
        yield RichLog(id="stealth-log", markup=False, highlight=False, wrap=False)

    def on_mount(self) -> None:
        app = cast("TermplayTUIApp", self.app)
        app.set_message_handler(self.on_server_message)
        if get_stealth():
            self.add_class("stealth")
        self._mounted = True
        for msg in self._pending:
            self.run_worker(self.on_server_message(msg))
        self._pending.clear()

    async def on_server_message(self, msg: dict[str, Any]) -> None:
        if not self._mounted:
            self._pending.append(msg)
            return
        mtype = msg.get("type")
        if mtype == TYPE_GAME_RENDER:
            content = str(msg.get("content") or "")
            if get_stealth():
                self.query_one("#stealth-log", RichLog).write(content)
                return
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if data.get("v") == _VELHA_TAG:
                    self._apply_state(data)
        elif mtype == TYPE_GAME_OVER:
            self._game_over = True
            if not get_stealth():
                self.query_one("#status", Label).update("Game over (Esc to quit)")
        elif mtype == TYPE_ERROR:
            if msg.get("fatal"):
                await self._disconnect()
                self.app.pop_screen()

    def _apply_state(self, data: dict[str, Any]) -> None:
        self._cells = list(data.get("cells", [" "] * 9))
        self._my_mark = str(data.get("your_mark", ""))
        turn = str(data.get("turn", ""))
        self._my_turn = bool(turn and turn == self._my_mark)
        self._game_over = data.get("phase") == "over"
        winner = data.get("winner")

        if self._game_over:
            if winner == self._my_mark:
                status = "You win! 🏆"
            elif winner:
                status = "Opponent wins!"
            else:
                status = "Draw!"
        elif self._my_turn:
            status = f"Your turn ({self._my_mark})! Arrows + Enter"
        else:
            status = f"Opponent's turn ({turn})..."
        self.query_one("#status", Label).update(status)
        self._refresh_board()

    def _refresh_board(self) -> None:
        for i in range(9):
            w = self.query_one(f"#cell-{i}", Static)
            c = self._cells[i]
            w.remove_class("cursor", "mark-x", "mark-o")
            if c == "X":
                w.update("X")
                w.add_class("mark-x")
            elif c == "O":
                w.update("O")
                w.add_class("mark-o")
            else:
                w.update(str(i + 1))
                if i == self._cursor and self._my_turn and not self._game_over:
                    w.add_class("cursor")

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            return
        if event.key not in ("up", "down", "left", "right", "enter"):
            return
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
        elif event.key == "enter":
            if self._my_turn and not self._game_over and self._cells[self._cursor] == " ":
                self.run_worker(self._send_move(self._cursor))

    async def _send_move(self, idx: int) -> None:
        app = cast("TermplayTUIApp", self.app)
        if app.connection is not None:
            await app.connection.send(action=ACTION_GAME_INPUT, text=str(idx + 1))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit-btn":
            await self.action_leave()

    async def action_leave(self) -> None:
        app = cast("TermplayTUIApp", self.app)
        if app.connection is not None:
            await app.connection.send(action=ACTION_GAME_INPUT, text="q")
        await self._disconnect()
        self.app.pop_screen()

    async def _disconnect(self) -> None:
        app = cast("TermplayTUIApp", self.app)
        await app.disconnect_server()
