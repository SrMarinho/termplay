"""UnoGameScreen — fully visual Textual UI for multiplayer Uno.

Renders the server's structured state with native widgets: clickable colored card
buttons for your hand, a draw pile, an opponent bar, and a modal color picker for
wild cards. No ANSI/text streaming — everything is real Textual.
"""

from __future__ import annotations

import contextlib
import json
from typing import TYPE_CHECKING, Any, ClassVar, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Header, Label, Static

from termplay.engine.protocol import (
    ACTION_GAME_INPUT,
    TYPE_GAME_OVER,
    TYPE_GAME_RENDER,
)

if TYPE_CHECKING:
    from termplay.frontends.textual_app import TermplayTUIApp

_FACE = {"skip": "⊘", "reverse": "⇄", "draw2": "+2", "wild": "★", "wild4": "+4"}
_COLOR_NAME = {"R": "VERMELHO", "G": "VERDE", "B": "AZUL", "Y": "AMARELO", "W": "?"}


def _face(value: str) -> str:
    return _FACE.get(value, value)


class UnoColorModal(ModalScreen[str]):
    """Modal asking which color a wild card becomes."""

    DEFAULT_CSS = """
    UnoColorModal {
        align: center middle;
    }
    UnoColorModal #box {
        width: 44;
        height: auto;
        padding: 1 2;
        border: thick $accent;
        background: $surface;
    }
    UnoColorModal #title {
        width: 1fr;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    UnoColorModal #picker {
        width: 1fr;
        height: 10;
        grid-size: 2 2;
        grid-gutter: 1;
    }
    UnoColorModal #picker Button {
        width: 1fr;
        height: 1fr;
    }
    UnoColorModal .col-R { background: red; color: white; }
    UnoColorModal .col-G { background: green; color: white; }
    UnoColorModal .col-B { background: blue; color: white; }
    UnoColorModal .col-Y { background: yellow; color: black; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label("Escolha a cor do coringa", id="title")
            with Grid(id="picker"):
                yield Button("🔴  Vermelho", id="R", classes="col-R")
                yield Button("🟢  Verde", id="G", classes="col-G")
                yield Button("🔵  Azul", id="B", classes="col-B")
                yield Button("🟡  Amarelo", id="Y", classes="col-Y")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(str(event.button.id))


class ConfirmModal(ModalScreen[bool]):
    """Yes/no confirmation dialog."""

    DEFAULT_CSS = """
    ConfirmModal {
        align: center middle;
    }
    ConfirmModal #box {
        width: 50;
        height: auto;
        padding: 1 2;
        border: thick $warning;
        background: $surface;
    }
    ConfirmModal #q {
        width: 1fr;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    ConfirmModal #row {
        width: 1fr;
        height: auto;
        align: center middle;
    }
    ConfirmModal #row Button {
        width: 1fr;
        height: 3;
        margin: 0 1;
    }
    """

    def __init__(self, question: str) -> None:
        super().__init__()
        self._question = question

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label(self._question, id="q")
            with Horizontal(id="row"):
                yield Button("Sair", id="yes", variant="error")
                yield Button("Continuar", id="no", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")


class UnoGameScreen(Screen[None]):
    """Visual Uno board driven by structured server state."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "leave", "Sair"),
    ]

    DEFAULT_CSS = """
    UnoGameScreen #board {
        height: 1fr;
        padding: 1 2;
        align: center middle;
    }
    UnoGameScreen #pilebar {
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }
    UnoGameScreen #pile {
        width: 18;
        height: 7;
        content-align: center middle;
        text-style: bold;
        border: heavy white;
        margin: 0 2;
    }
    UnoGameScreen #info {
        width: auto;
        height: 7;
        content-align: left middle;
        padding: 0 2;
    }
    UnoGameScreen #opponents {
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }
    UnoGameScreen #opponents Static {
        width: auto;
        padding: 0 2;
        margin: 0 1;
        border: round $panel-lighten-2;
        color: $text-muted;
    }
    UnoGameScreen .turn {
        border: round $success;
        color: $text;
        text-style: bold;
    }
    UnoGameScreen .turn-you {
        border: round $warning;
        color: $text;
        text-style: bold;
    }
    UnoGameScreen #status {
        height: auto;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    UnoGameScreen #hand {
        height: auto;
        max-height: 12;
        padding: 1 0;
    }
    UnoGameScreen .hand-row {
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }
    UnoGameScreen .hand-row Button {
        width: 8;
        min-width: 8;
        height: 3;
        margin: 0 1;
    }
    UnoGameScreen #controls {
        height: auto;
        align: center middle;
    }
    UnoGameScreen #controls Button {
        margin: 0 2;
    }
    UnoGameScreen .card-R { background: red; color: white; }
    UnoGameScreen .card-G { background: green; color: white; }
    UnoGameScreen .card-B { background: blue; color: white; }
    UnoGameScreen .card-Y { background: yellow; color: black; }
    UnoGameScreen .card-W {
        background: $panel;
        color: magenta;
        text-style: bold;
    }
    UnoGameScreen .pile-R { border: heavy red; color: red; }
    UnoGameScreen .pile-G { border: heavy green; color: green; }
    UnoGameScreen .pile-B { border: heavy blue; color: blue; }
    UnoGameScreen .pile-Y { border: heavy yellow; color: yellow; }
    UnoGameScreen .pile-W { border: heavy magenta; color: magenta; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._mounted = False
        self._pending: list[dict[str, Any]] = []
        self._asking_color = False
        self._your_turn = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="board"):
            with Horizontal(id="pilebar"):
                yield Static("—", id="pile")
                yield Static("", id="info")
            yield Horizontal(id="opponents")
            yield Static("Aguardando início...", id="status")
            yield ScrollableContainer(id="hand")
            with Horizontal(id="controls"):
                yield Button(
                    "Comprar carta", id="draw", variant="primary", disabled=True
                )
                yield Button("Sair", id="leave", variant="error")

    def on_mount(self) -> None:
        self._mounted = True
        for msg in self._pending:
            self.run_worker(self.on_server_message(msg))
        self._pending.clear()

    # ── server messages ───────────────────────────────────────────────────────

    async def on_server_message(self, msg: dict[str, Any]) -> None:
        if not self._mounted:
            self._pending.append(msg)
            return
        mtype = msg.get("type")
        if mtype == TYPE_GAME_RENDER:
            content = str(msg.get("content") or "").strip()
            try:
                data = json.loads(content)
            except (ValueError, TypeError):
                return
            await self._apply_state(data)
        elif mtype == TYPE_GAME_OVER:
            self._set_enabled(False)

    async def _apply_state(self, data: dict[str, Any]) -> None:
        phase = data.get("phase")
        if phase == "toast":
            msg = str(data.get("message") or "")
            if msg:
                self.query_one("#status", Static).update(msg)
            return
        if phase == "over":
            winner = str(data.get("winner") or "")
            banner = f"🏆 {winner} venceu o Uno!" if winner else "Partida encerrada."
            self.query_one("#status", Static).update(banner)
            self._set_enabled(False)
            await self._render_hand([], [], enabled=False)
            return

        self._update_pile(data)
        await self._update_opponents(data)
        self._update_status(data)
        self._your_turn = bool(data.get("your_turn"))
        await self._render_hand(
            [str(c) for c in data.get("hand", [])],
            [int(i) for i in data.get("playable", [])],
            enabled=self._your_turn,
        )
        self.query_one("#draw", Button).disabled = not self._your_turn
        if data.get("need_color") and not self._asking_color:
            self._ask_color()

    def _update_pile(self, data: dict[str, Any]) -> None:
        top = str(data.get("top") or ":")
        color, _, value = top.partition(":")
        pile = self.query_one("#pile", Static)
        pile.set_classes([f"pile-{color}"])
        pile.update(f"{color}\n{_face(value)}")
        active = str(data.get("color") or color)
        arrow = "→" if int(data.get("direction", 1)) == 1 else "←"
        self.query_one("#info", Static).update(
            f"Cor atual: [b]{_COLOR_NAME.get(active, active)}[/]\nSentido: {arrow}"
        )

    async def _update_opponents(self, data: dict[str, Any]) -> None:
        bar = self.query_one("#opponents", Horizontal)
        await bar.remove_children()
        current = int(data.get("current", -1))
        you = int(data.get("you", -1))
        players = data.get("players", [])
        n = len(players)
        if n == 0:
            return
        for i in range(n):
            entry = players[i]
            name, count = str(entry[0]), int(entry[1])
            is_turn = i == current
            is_you = i == you
            turn_mark = "* " if is_turn else "  "
            you_mark = " (você)" if is_you else ""
            label = f"{turn_mark}{name}{you_mark}\n  🂠 x{count}"
            chip = Static(label)
            if is_turn:
                chip.add_class("turn-you" if is_you else "turn")
            bar.mount(chip)

    def _update_status(self, data: dict[str, Any]) -> None:
        message = str(data.get("message") or "")
        current = int(data.get("current", -1))
        players = data.get("players", [])
        turn_name = str(players[current][0]) if 0 <= current < len(players) else "?"
        your_turn = bool(data.get("your_turn"))
        text = f"Vez de {turn_name}"
        if your_turn:
            text = "Sua vez — clique numa carta ou compre."
        if message:
            text = f"{message}   •   {text}"
        self.query_one("#status", Static).update(text)

    async def _render_hand(
        self, hand: list[str], playable: list[int], *, enabled: bool
    ) -> None:
        box = self.query_one("#hand", ScrollableContainer)
        await box.remove_children()
        playset = set(playable)
        row_size = 10
        rows = [hand[i : i + row_size] for i in range(0, len(hand), row_size)]
        for row_idx, row in enumerate(rows):
            row_widget = Horizontal(classes="hand-row")
            await box.mount(row_widget)
            for col_idx, face in enumerate(row):
                i = row_idx * row_size + col_idx
                color, _, value = face.partition(":")
                btn = Button(
                    f"{color} {_face(value)}", name=str(i), classes=f"card-{color}"
                )
                btn.disabled = not (enabled and i in playset)
                await row_widget.mount(btn)

    # ── input ─────────────────────────────────────────────────────────────────

    def _ask_color(self) -> None:
        self._asking_color = True

        def done(color: str | None) -> None:
            self._asking_color = False
            if color:
                self.run_worker(self._send(color))

        self.app.push_screen(UnoColorModal(), done)

    def _set_enabled(self, enabled: bool) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#draw", Button).disabled = not enabled
            for btn in self.query("#hand Button").results(Button):
                btn.disabled = not enabled

    async def _send(self, text: str) -> None:
        app = cast("TermplayTUIApp", self.app)
        if app.connection is not None:
            await app.connection.send(action=ACTION_GAME_INPUT, text=text)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = str(event.button.id or "")
        name = event.button.name
        if bid == "leave":
            await self.action_leave()
        elif bid == "draw" and self._your_turn:
            await self._send("d")
        elif name is not None and name.isdigit():
            await self._send(str(int(name) + 1))

    async def action_leave(self) -> None:
        def done(confirm: bool | None) -> None:
            if confirm:
                self.run_worker(self._leave())

        self.app.push_screen(ConfirmModal("Sair da partida de Uno?"), done)

    async def _leave(self) -> None:
        app = cast("TermplayTUIApp", self.app)
        await app.disconnect_server()
        self.app.pop_screen()


class BotCountModal(ModalScreen[int]):
    """Ask how many bots the player wants to face in solo mode."""

    DEFAULT_CSS = """
    BotCountModal { align: center middle; }
    BotCountModal #box {
        width: 40;
        height: auto;
        padding: 1 2;
        border: thick $accent;
        background: $surface;
    }
    BotCountModal #title {
        width: 1fr;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    BotCountModal #row {
        width: 1fr;
        height: auto;
        align: center middle;
    }
    BotCountModal #row Button {
        width: auto;
        min-width: 10;
        height: 3;
        margin: 0 2;
    }
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("right", "focus_next", show=False),
        Binding("down", "focus_next", show=False),
        Binding("left", "focus_previous", show=False),
        Binding("up", "focus_previous", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label("Quantos bots?", id="title")
            with Horizontal(id="row"):
                yield Button("1", id="b1", variant="primary")
                yield Button("2", id="b2", variant="primary")
                yield Button("3", id="b3", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#b1", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = str(event.button.id or "b1")
        self.dismiss(int(bid[1:]))


class UnoSoloScreen(UnoGameScreen):
    """UnoGameScreen wired to a local UnoController (solo vs bots, no server)."""

    def __init__(self, num_bots: int = 3) -> None:
        super().__init__()
        self._num_bots = max(1, min(num_bots, 9))
        from termplay.engine.local_transport import LocalTransportAdapter
        self._local = LocalTransportAdapter()

    def on_mount(self) -> None:
        async def on_write(text: str) -> None:
            for line in text.splitlines():
                line = line.strip()
                if line:
                    await self.on_server_message(
                        {"type": TYPE_GAME_RENDER, "content": line}
                    )

        self._local.set_write_callback(on_write)
        super().on_mount()
        self.run_worker(self._run_controller())

    async def _run_controller(self) -> None:
        from termplay.engine.bot_transport import BotTransportAdapter
        from termplay.engine.interfaces import ITransportAdapter
        from termplay.games.uno.controller import UnoController

        bot_names = [f"Bot {i + 1}" for i in range(self._num_bots)]
        bots: list[ITransportAdapter] = [BotTransportAdapter(n) for n in bot_names]
        transports: list[ITransportAdapter] = [self._local, *bots]
        names = ["Você"] + bot_names
        controller = UnoController(
            transports,
            names=names,
            stealth_flags=[False] * len(names),
        )
        await controller.run()
        await self.on_server_message({"type": TYPE_GAME_OVER})

    async def _send(self, text: str) -> None:
        await self._local.feed(text)

    async def _leave(self) -> None:
        await self._local.feed("q")
        self.app.pop_screen()
