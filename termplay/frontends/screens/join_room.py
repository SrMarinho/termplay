"""JoinRoomScreen — discover LAN rooms via UDP and connect to selected host."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, ClassVar, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Input, Label

from termplay.config.settings import (
    get_last_host,
    get_nickname,
    get_stealth,
    set_last_host,
)
from termplay.engine.discovery import DiscoveredRoom, RoomDiscoverer
from termplay.engine.protocol import ACTION_JOIN_ROOM, ACTION_SPECTATE

if TYPE_CHECKING:
    from termplay.frontends.textual_app import TermplayTUIApp


class JoinRoomScreen(Screen[None]):
    """Shows a live table of LAN rooms; select one to join, or type IP manually."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "pop_screen", "Back"),
        ("w", "spectate_selected", "Watch"),
    ]

    DEFAULT_CSS = """
    JoinRoomScreen {
        layout: vertical;
    }
    JoinRoomScreen #rooms {
        height: 1fr;
        border: round $primary;
        margin: 0 1;
    }
    JoinRoomScreen #manual {
        height: auto;
        border: round $secondary;
        margin: 0 1;
        padding: 0 1;
    }
    JoinRoomScreen #manual Label {
        margin-top: 1;
    }
    JoinRoomScreen #manual Horizontal {
        height: auto;
        margin-top: 1;
    }
    JoinRoomScreen #manual Horizontal Button {
        width: auto;
    }
    JoinRoomScreen #status {
        color: $error;
        margin: 0 1;
        height: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._discoverer = RoomDiscoverer()
        self._refresh_task: asyncio.Task[None] | None = None
        self._discovered: list[DiscoveredRoom] = []
        last_host, last_port = get_last_host()
        self._last_host = last_host
        self._last_port = last_port

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="rooms", cursor_type="row")
        with Vertical(id="manual"):
            yield Label("Manual connection:")
            yield Input(
                value=get_nickname(), id="name", placeholder="your name"
            )
            with Horizontal():
                yield Input(
                    value=self._last_host,
                    id="host",
                    placeholder="host IP (e.g. 192.168.1.42)",
                )
                yield Input(
                    value=str(self._last_port), id="port", placeholder="4443"
                )
                yield Button("Connect", id="connect", variant="primary")
        yield Label("", id="status")

    def on_mount(self) -> None:
        table = self.query_one("#rooms", DataTable)
        table.add_column("Host",    width=14)
        table.add_column("Game",    width=14)
        table.add_column("Players", width=10)
        table.add_column("Status",  width=12)
        table.add_column("IP",      width=16)
        table.focus()
        self.run_worker(self._start_discovery(), exclusive=False)

    async def on_unmount(self) -> None:
        if self._refresh_task is not None:
            self._refresh_task.cancel()
        await self._discoverer.stop()

    async def _start_discovery(self) -> None:
        try:
            await self._discoverer.start()
        except OSError:
            self.query_one("#status", Label).update(
                "UDP discovery unavailable — use manual connection."
            )
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def _refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            self._discovered = self._discoverer.rooms()
            self._update_table()

    def _update_table(self) -> None:
        table = self.query_one("#rooms", DataTable)
        table.clear()
        for room in self._discovered:
            players_str = f"{room.players}/{room.max_players}"
            table.add_row(
                room.host,
                room.game,
                players_str,
                room.status,
                room.ip,
                key=room.ip,
            )

    # ── table selection ──────────────────────────────────────────────────────

    async def on_data_table_row_selected(
        self, event: DataTable.RowSelected
    ) -> None:
        ip = str(event.row_key.value)
        matching = [r for r in self._discovered if r.ip == ip]
        if not matching:
            return
        room = matching[0]
        name = self.query_one("#name", Input).value.strip() or "Player"
        await self._join(name, room.ip, room.port)

    async def action_spectate_selected(self) -> None:
        """Join the highlighted room as a watcher (no seat taken)."""
        table = self.query_one("#rooms", DataTable)
        if table.cursor_row is None or table.cursor_row >= len(self._discovered):
            return
        room = self._discovered[table.cursor_row]
        name = self.query_one("#name", Input).value.strip() or "Watcher"
        await self._connect_and_enter(name, room.ip, room.port, spectate=True)

    # ── manual connection ────────────────────────────────────────────────────

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "connect":
            await self._manual_join()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "name":
            self.query_one("#host", Input).focus()
        elif event.input.id == "host":
            self.query_one("#port", Input).focus()
        elif event.input.id == "port":
            await self._manual_join()

    async def _manual_join(self) -> None:
        name = self.query_one("#name", Input).value.strip() or "Player"
        host = self.query_one("#host", Input).value.strip()
        if not host:
            self.query_one("#status", Label).update("Enter the host IP.")
            return
        try:
            port = int(self.query_one("#port", Input).value.strip())
        except ValueError:
            port = 4443
        await self._join(name, host, port)

    async def _join(self, name: str, host: str, port: int) -> None:
        await self._connect_and_enter(name, host, port, spectate=False)

    async def _connect_and_enter(
        self, name: str, host: str, port: int, *, spectate: bool
    ) -> None:
        set_last_host(host, port)
        app = cast("TermplayTUIApp", self.app)
        ok = await app.connect_server(host, port)
        if not ok:
            self.query_one("#status", Label).update(
                f"Failed to connect to {host}:{port}"
            )
            return

        assert app.connection is not None

        from termplay.frontends.screens.waiting_room import WaitingRoomScreen

        waiting = WaitingRoomScreen(my_name=name, is_host=False)
        app.set_message_handler(waiting.on_server_message)
        if spectate:
            await app.connection.send(action=ACTION_SPECTATE, name=name, code="")
        else:
            await app.connection.send(
                action=ACTION_JOIN_ROOM, name=name, code="", stealth=get_stealth()
            )
        app.push_screen(waiting)

    def action_pop_screen(self) -> None:
        self.app.pop_screen()
