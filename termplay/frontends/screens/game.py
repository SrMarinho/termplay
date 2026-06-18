"""GameScreen — executa um jogo solo com TextualTransportAdapter."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Input, RichLog

from termplay.engine.game import IGame
from termplay.frontends.textual_adapter import TextualTransportAdapter


class GameScreen(Screen[None]):
    """Roda um IGame solo com I/O via RichLog + Input."""

    DEFAULT_CSS = """
    GameScreen RichLog {
        height: 1fr;
    }
    GameScreen Input {
        dock: bottom;
    }
    """

    def __init__(self, game_class: type[IGame]) -> None:
        super().__init__()
        self.game_class = game_class
        self._adapter: TextualTransportAdapter | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(
            id="game-log",
            auto_scroll=True,
            markup=False,
            highlight=False,
            wrap=False,
        )
        yield Input(
            placeholder="h=hit  s=stand  d=double  q=sair",
            id="cmd",
        )

    def on_mount(self) -> None:
        log = self.query_one("#game-log", RichLog)
        self._adapter = TextualTransportAdapter(app=self.app, log=log)
        self.run_worker(self._run_game(), exclusive=True)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._adapter is not None:
            self._adapter.feed(event.value)
        event.input.clear()

    async def _run_game(self) -> None:
        assert self._adapter is not None
        game = self.game_class()
        await game.run(self._adapter)
        self.app.pop_screen()

    async def action_request_quit(self) -> None:
        if self._adapter is not None:
            await self._adapter.close()
