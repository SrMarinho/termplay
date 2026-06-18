"""WaitingRoomScreen — sala de espera nativa com lista de players e chat."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Input, RichLog, Static

from termplay.engine.protocol import (
    ACTION_CHAT,
    ACTION_START_GAME,
    TYPE_CHAT,
    TYPE_ERROR,
    TYPE_GAME_START,
    TYPE_ROOM_CREATED,
    TYPE_ROOM_JOINED,
    TYPE_ROOM_STATE,
)

if TYPE_CHECKING:
    from termplay.frontends.textual_app import TermplayTUIApp

_NICK_COLORS = ["cyan", "green", "magenta", "yellow", "blue", "red"]


def _nick_color(name: str) -> str:
    return _NICK_COLORS[hash(name) % len(_NICK_COLORS)]


def _chat_renderable(name: str, text: str, is_mine: bool) -> object:
    if is_mine:
        nick = Text(f"{name}", style="bold white on dark_blue")
    else:
        nick = Text(f"{name}", style=f"bold {_nick_color(name)}")
    return Text.assemble(nick, Text(f": {text}", style="white"))


class WaitingRoomScreen(Screen[None]):
    """Mostra players em tempo real; líder inicia quando atinge o mínimo."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "leave", "Sair da sala")
    ]

    DEFAULT_CSS = """
    WaitingRoomScreen #layout {
        height: 1fr;
    }
    WaitingRoomScreen #left {
        width: 55;
        min-width: 40;
        padding: 1 2;
        border-right: solid $primary;
    }
    WaitingRoomScreen #right {
        padding: 1 1;
    }
    WaitingRoomScreen #code {
        text-style: bold;
        margin-bottom: 1;
    }
    WaitingRoomScreen #players {
        border: round $primary;
        height: 1fr;
        padding: 0 1;
    }
    WaitingRoomScreen #start {
        margin-top: 1;
        width: 1fr;
    }
    WaitingRoomScreen #chat {
        height: 1fr;
        border: round $secondary;
    }
    WaitingRoomScreen #chat-input {
        height: auto;
        margin-top: 1;
    }
    """

    def __init__(self, my_name: str, is_host: bool, host_addr: str = "") -> None:
        super().__init__()
        self._my_name = my_name
        self._is_host = is_host
        self._host_addr = host_addr
        self._code = "----"
        self._mounted = False
        self._pending: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="layout"):
            with Vertical(id="left"):
                yield Static("Sala: ----", id="code")
                if self._is_host and self._host_addr:
                    yield Static(f"Compartilhe: {self._host_addr}", id="share")
                yield Static("Aguardando...", id="players")
                if self._is_host:
                    yield Button(
                        "Iniciar Partida", id="start", variant="success", disabled=True
                    )
            with Vertical(id="right"):
                yield RichLog(id="chat", markup=False, highlight=False, wrap=True)
                yield Input(placeholder="Mensagem de chat...", id="chat-input")

    def on_mount(self) -> None:
        app = cast("TermplayTUIApp", self.app)
        app.set_message_handler(self.on_server_message)
        self._mounted = True
        for msg in self._pending:
            self.run_worker(self.on_server_message(msg))
        self._pending.clear()
        self.query_one("#chat-input", Input).focus()

    # ── Mensagens do servidor ────────────────────────────────────────────────

    async def on_server_message(self, msg: dict[str, Any]) -> None:
        if not self._mounted:
            self._pending.append(msg)
            return
        mtype = msg.get("type")
        if mtype in (TYPE_ROOM_CREATED, TYPE_ROOM_JOINED):
            self._code = str(msg.get("code") or "----")
            self.query_one("#code", Static).update(f"Sala: {self._code}")
        elif mtype == TYPE_ROOM_STATE:
            self._update_state(msg)
        elif mtype == TYPE_CHAT:
            sender = str(msg.get("name") or "")
            text = str(msg.get("text") or "")
            self.query_one("#chat", RichLog).write(
                _chat_renderable(sender, text, sender == self._my_name)
            )
        elif mtype == TYPE_GAME_START:
            from termplay.frontends.screens.mp_game import MpGameScreen

            mp = MpGameScreen()
            cast("TermplayTUIApp", self.app).set_message_handler(mp.on_server_message)
            self.app.push_screen(mp)
        elif mtype == TYPE_ERROR:
            self.query_one("#chat", RichLog).write(f"[erro] {msg.get('message')}")
            if msg.get("fatal"):
                await self._teardown()
                self.app.pop_screen()

    def _update_state(self, msg: dict[str, Any]) -> None:
        players = msg.get("players") or []
        host = msg.get("host")
        count = msg.get("player_count", len(players))
        max_p = msg.get("max_players", 4)
        lines = [f"Players ({count}/{max_p}):"]
        for name in players:
            tag = " (líder)" if name == host else ""
            lines.append(f"  • {name}{tag}")
        self.query_one("#players", Static).update("\n".join(lines))
        if self._is_host:
            btn = self.query_one("#start", Button)
            btn.disabled = not bool(msg.get("can_start"))

    # ── Ações ────────────────────────────────────────────────────────────────

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start":
            app = cast("TermplayTUIApp", self.app)
            if app.connection is not None:
                await app.connection.send(action=ACTION_START_GAME)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.clear()
        if not text:
            return
        app = cast("TermplayTUIApp", self.app)
        if app.connection is not None:
            await app.connection.send(action=ACTION_CHAT, text=text)

    async def action_leave(self) -> None:
        await self._teardown()
        self.app.pop_screen()

    async def _teardown(self) -> None:
        app = cast("TermplayTUIApp", self.app)
        await app.disconnect_server()
