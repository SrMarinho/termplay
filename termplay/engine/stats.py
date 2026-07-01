"""Persistent match statistics — SQLite-backed wins/played aggregates.

Results are captured through GameLogger's match_start/match_end events, so
individual games never talk to this module directly. The database lives at
``~/.termplay/stats.db`` unless ``TERMPLAY_STATS_DB`` points elsewhere; set it
to ``off`` to disable persistence entirely.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger("termplay.stats")

ENV_DB = "TERMPLAY_STATS_DB"
_DISABLED_VALUES = {"off", "0", "none", "disabled"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    match_id    TEXT PRIMARY KEY,
    game        TEXT NOT NULL,
    finished_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS results (
    match_id TEXT NOT NULL REFERENCES matches(match_id),
    player   TEXT NOT NULL,
    won      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_results_player ON results(player);
"""


class StatsStore:
    """Append-only match results with win/played aggregation."""

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def record_match(
        self,
        game: str,
        match_id: str,
        players: list[str],
        winner: str | None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO matches (match_id, game, finished_at)"
                " VALUES (?, ?, ?)",
                (match_id, game, round(time.time(), 3)),
            )
            conn.executemany(
                "INSERT INTO results (match_id, player, won) VALUES (?, ?, ?)",
                [(match_id, name, int(name == winner)) for name in players],
            )

    def leaderboard(
        self, game: str | None = None, limit: int = 10
    ) -> list[tuple[str, int, int]]:
        """Top players as (name, wins, played), best win count first."""
        query = (
            "SELECT r.player, SUM(r.won) AS wins, COUNT(*) AS played"
            " FROM results r JOIN matches m ON m.match_id = r.match_id"
        )
        params: tuple[object, ...] = ()
        if game:
            query += " WHERE m.game = ?"
            params = (game,)
        query += " GROUP BY r.player ORDER BY wins DESC, played ASC LIMIT ?"
        with self._connect() as conn:
            rows = conn.execute(query, (*params, limit)).fetchall()
        return [(str(name), int(wins), int(played)) for name, wins, played in rows]

    def player_stats(self, name: str) -> tuple[int, int]:
        """(wins, played) across every game for one player."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(won), 0), COUNT(*) FROM results WHERE player = ?",
                (name,),
            ).fetchone()
        return int(row[0]), int(row[1])


_store: StatsStore | None = None
_store_failed = False


def get_stats_store() -> StatsStore | None:
    """Process-wide store, or None when disabled/unavailable."""
    global _store, _store_failed
    if _store is not None or _store_failed:
        return _store
    configured = os.environ.get(ENV_DB, "")
    if configured.strip().lower() in _DISABLED_VALUES:
        _store_failed = True
        return None
    path = Path(configured) if configured else Path.home() / ".termplay" / "stats.db"
    try:
        _store = StatsStore(path)
    except (OSError, sqlite3.Error):
        logger.warning("stats: cannot open db at %s", path, exc_info=True)
        _store_failed = True
    return _store


def reset_stats_store() -> None:
    """Forget the cached store (used by tests to repoint ENV_DB)."""
    global _store, _store_failed
    _store = None
    _store_failed = False
