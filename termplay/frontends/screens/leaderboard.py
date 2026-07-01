"""LeaderboardScreen — local match statistics (wins/played per player)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Label

from termplay.engine.stats import get_stats_store


class LeaderboardScreen(Screen[None]):
    """Ranking table built from the persistent stats store."""

    DEFAULT_CSS = """
    LeaderboardScreen {
        align: center middle;
    }
    LeaderboardScreen Vertical {
        width: 60;
        height: auto;
        border: solid green;
        padding: 1 2;
    }
    LeaderboardScreen Label#title {
        content-align: center middle;
        width: 100%;
        text-style: bold;
        margin-bottom: 1;
    }
    LeaderboardScreen DataTable {
        height: auto;
        max-height: 16;
        margin-bottom: 1;
    }
    LeaderboardScreen Button {
        width: 100%;
    }
    """

    BINDINGS = [("escape", "back", "Voltar")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("🏆  Ranking", id="title"),
            DataTable(id="table", cursor_type="none"),
            Label("", id="empty"),
            Button("Voltar", id="back", variant="primary"),
        )

    def on_mount(self) -> None:
        table = self.query_one("#table", DataTable)
        table.add_columns("#", "Jogador", "Vitórias", "Partidas")
        store = get_stats_store()
        rows = store.leaderboard(limit=15) if store is not None else []
        if not rows:
            table.display = False
            self.query_one("#empty", Label).update(
                "Nenhuma partida registrada ainda."
            )
            return
        for i, (name, wins, played) in enumerate(rows, start=1):
            table.add_row(str(i), name, str(wins), str(played))

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
