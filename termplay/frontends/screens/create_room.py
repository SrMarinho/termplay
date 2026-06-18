"""CreateRoomScreen — select a game, start embedded P2P server, create room."""

from __future__ import annotations

import contextlib
import socket
from typing import TYPE_CHECKING, ClassVar, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Input, Label

from termplay.config.settings import get_nickname
from termplay.engine.protocol import ACTION_CREATE_ROOM

if TYPE_CHECKING:
    from termplay.frontends.textual_app import TermplayTUIApp


def _get_local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s, contextlib.suppress(
        Exception
    ):
        s.connect(("8.8.8.8", 80))
        return str(s.getsockname()[0])
    return "127.0.0.1"


class CreateRoomScreen(Screen[None]):
    """Collect name, pick a game, start embedded server, open waiting room."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "pop_screen", "Back")
    ]

    DEFAULT_CSS = """
    CreateRoomScreen {
        align: center middle;
    }
    CreateRoomScreen Vertical {
        width: 50;
        height: auto;
        border: round $primary;
        padding: 1 2;
    }
    CreateRoomScreen #status {
        color: $error;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Create Room"),
            Label(""),
            Label("Your name:"),
            Input(value=get_nickname(), id="name", placeholder="player name"),
            Label(""),
            Button("Select Game & Create", id="create", variant="primary"),
            Label("", id="status"),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            self.run_worker(self._create(), exclusive=True)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.run_worker(self._create(), exclusive=True)

    async def _create(self) -> None:
        name = self.query_one("#name", Input).value.strip() or "Host"
        app = cast("TermplayTUIApp", self.app)
        status = self.query_one("#status", Label)

        from termplay.frontends.screens.game_select import GameSelectScreen

        game_name: str | None = await app.push_screen_wait(
            GameSelectScreen(select_mode=True)
        )
        if not game_name:
            return

        status.update("Starting server...")
        try:
            port = await app.start_embedded_server(game_name=game_name)
        except Exception:
            status.update("Failed to start server.")
            return

        local_ip = _get_local_ip()
        ok = await app.connect_server("127.0.0.1", port)
        if not ok:
            await app.stop_embedded_server()
            status.update("Failed to connect to local server.")
            return

        assert app.connection is not None

        from termplay.frontends.screens.waiting_room import WaitingRoomScreen

        waiting = WaitingRoomScreen(
            my_name=name,
            is_host=True,
            host_addr=f"{local_ip}:{port}",
        )
        app.set_message_handler(waiting.on_server_message)
        await app.connection.send(action=ACTION_CREATE_ROOM, name=name)
        app.push_screen(waiting)

    def action_pop_screen(self) -> None:
        self.app.pop_screen()
