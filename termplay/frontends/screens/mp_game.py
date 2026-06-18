"""MpGameScreen — renderiza o jogo multiplayer com botões de ação."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Header, Input, RichLog

from termplay.config.settings import get_stealth
from termplay.engine.protocol import (
    ACTION_GAME_INPUT,
    TYPE_ERROR,
    TYPE_GAME_OVER,
    TYPE_GAME_RENDER,
)

if TYPE_CHECKING:
    from termplay.frontends.textual_app import TermplayTUIApp

_BOX_CHARS = ("╭", "╰", "╔", "╚", "┌", "└")
_ACTION_MARKER = "Sua vez"


class MpGameScreen(Screen[None]):
    """Mostra o render ANSI do servidor; botões e teclas para ações do jogo."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "leave",          "Sair"),
        ("1",      "act_hit",        "Hit"),
        ("h",      "act_hit",        "Hit"),
        ("2",      "act_stand",      "Stand"),
        ("s",      "act_stand",      "Stand"),
        ("3",      "act_double",     "Double"),
        ("d",      "act_double",     "Double"),
        ("left",   "focus_previous", ""),
        ("right",  "focus_next",     ""),
        ("up",     "focus_previous", ""),
        ("down",   "focus_next",     ""),
    ]

    DEFAULT_CSS = """
    MpGameScreen RichLog {
        height: 1fr;
    }
    MpGameScreen #actions {
        height: auto;
        align: center middle;
        padding: 0 1;
    }
    MpGameScreen #actions Button {
        width: auto;
        margin: 0 1;
    }
    MpGameScreen Input {
        dock: bottom;
    }
    MpGameScreen.stealth Header {
        display: none;
    }
    MpGameScreen.stealth #actions {
        display: none;
    }
    MpGameScreen.stealth #out {
        border: none;
        background: $surface;
    }
    MpGameScreen.generic #actions {
        display: none;
    }
    """

    def __init__(self, game: str = "blackjack") -> None:
        super().__init__()
        self._mounted = False
        self._pending: list[dict[str, Any]] = []
        self._stealth = get_stealth()
        self._game = game.lower()

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(
            id="out", auto_scroll=True, markup=False, highlight=False, wrap=False
        )
        with Horizontal(id="actions"):
            yield Button("Hit [1]",    id="hit",    variant="success", disabled=True)
            yield Button("Stand [2]",  id="stand",  variant="primary", disabled=True)
            yield Button("Double [3]", id="double", variant="warning", disabled=True)
            yield Button("Sair",       id="quit",   variant="error")
        yield Input(placeholder="aposta (valor)...", id="cmd")

    def on_mount(self) -> None:
        self._mounted = True
        if self._game != "blackjack":
            self.add_class("generic")
            self.query_one("#cmd", Input).placeholder = "digite e Enter..."
        if self._stealth:
            self.add_class("stealth")
            self.query_one("#cmd", Input).placeholder = "user@host:~$ "
        self.query_one("#cmd", Input).focus()
        for msg in self._pending:
            self.run_worker(self.on_server_message(msg))
        self._pending.clear()

    # ── mensagens do servidor ────────────────────────────────────────────────

    async def on_server_message(self, msg: dict[str, Any]) -> None:
        if not self._mounted:
            self._pending.append(msg)
            return
        mtype = msg.get("type")
        log = self.query_one("#out", RichLog)
        if mtype == TYPE_GAME_RENDER:
            content = str(msg.get("content") or "")
            clean = content.replace("\r\n", "\n").replace("\r", "\n")
            if not self._stealth and any(c in clean for c in _BOX_CHARS):
                log.clear()
            log.write(Text.from_ansi(clean))
            self._set_actions_enabled(_ACTION_MARKER in content)
        elif mtype == TYPE_GAME_OVER:
            if self._stealth:
                log.write(Text.from_ansi("[INFO ] session.close reason=eof\n"))
            else:
                log.write(Text.from_ansi("\n=== FIM DE JOGO === (Esc para sair)\n"))
            self._set_actions_enabled(False)
        elif mtype == TYPE_ERROR:
            log.write(f"[erro] {msg.get('message')}")

    # ── controle de botões ───────────────────────────────────────────────────

    def _set_actions_enabled(self, enabled: bool) -> None:
        if self._stealth or self._game != "blackjack":
            return  # buttons hidden; play via typed input
        for btn_id in ("hit", "stand", "double"):
            self.query_one(f"#{btn_id}", Button).disabled = not enabled
        if enabled:
            self.query_one("#hit", Button).focus()

    # ── envio de ação ────────────────────────────────────────────────────────

    async def _send(self, text: str) -> None:
        self._set_actions_enabled(False)
        app = cast("TermplayTUIApp", self.app)
        if app.connection is not None:
            await app.connection.send(action=ACTION_GAME_INPUT, text=text)

    async def action_act_hit(self) -> None:
        await self._send("h")

    async def action_act_stand(self) -> None:
        await self._send("s")

    async def action_act_double(self) -> None:
        await self._send("d")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        mapping = {"hit": "h", "stand": "s", "double": "d"}
        if event.button.id in mapping:
            await self._send(mapping[event.button.id])
        elif event.button.id == "quit":
            await self.action_leave()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        event.input.clear()
        if value:
            await self._send(value)

    def action_focus_next(self) -> None:
        self.focus_next()

    def action_focus_previous(self) -> None:
        self.focus_previous()

    async def action_leave(self) -> None:
        app = cast("TermplayTUIApp", self.app)
        await app.disconnect_server()
        self.app.pop_screen()
