"""MpGameScreen — renderiza o jogo multiplayer (ANSI via game_render)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Input, RichLog

from termplay.engine.protocol import (
    ACTION_GAME_INPUT,
    TYPE_ERROR,
    TYPE_GAME_OVER,
    TYPE_GAME_RENDER,
)

if TYPE_CHECKING:
    from termplay.frontends.textual_app import TermplayTUIApp

_BOX_CHARS = ("╭", "╰", "╔", "╚", "┌", "└")


class MpGameScreen(Screen[None]):
    """Mostra o render ANSI enviado pelo servidor e envia inputs do jogador."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "leave", "Sair")
    ]

    DEFAULT_CSS = """
    MpGameScreen RichLog {
        height: 1fr;
    }
    MpGameScreen Input {
        dock: bottom;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(
            id="out", auto_scroll=True, markup=False, highlight=False, wrap=False
        )
        yield Input(placeholder="h=hit  s=stand  d=double  q=sair", id="cmd")

    def on_mount(self) -> None:
        app = cast("TermplayTUIApp", self.app)
        app.set_message_handler(self.on_server_message)
        self.query_one("#cmd", Input).focus()

    async def on_server_message(self, msg: dict[str, Any]) -> None:
        mtype = msg.get("type")
        log = self.query_one("#out", RichLog)
        if mtype == TYPE_GAME_RENDER:
            content = str(msg.get("content") or "")
            clean = content.replace("\r\n", "\n").replace("\r", "\n")
            if any(c in clean for c in _BOX_CHARS):
                log.clear()
            log.write(Text.from_ansi(clean))
        elif mtype == TYPE_GAME_OVER:
            log.write(Text.from_ansi("\n=== FIM DE JOGO === (Esc para sair)\n"))
        elif mtype == TYPE_ERROR:
            log.write(f"[erro] {msg.get('message')}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value
        event.input.clear()
        app = cast("TermplayTUIApp", self.app)
        if app.connection is not None:
            await app.connection.send(action=ACTION_GAME_INPUT, text=value)

    async def action_leave(self) -> None:
        app = cast("TermplayTUIApp", self.app)
        await app.disconnect_server()
        self.app.pop_screen()
