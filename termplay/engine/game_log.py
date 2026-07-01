"""Structured game event log — an append-only audit trail per match.

Distinct from player-facing rendering: this records the rule-relevant state
transitions of a match (turns, moves, effects, results) as JSON events so each
game's behavior can be replayed and validated independently of any interface.

Events go to the ``termplay.gamelog`` logger and, when ``TERMPLAY_GAMELOG_DIR``
is set, to a per-match JSONL file (``<dir>/<game>-<match_id>.jsonl``). One JSON
object per line, sorted keys, append-only.
"""

from __future__ import annotations

import itertools
import json
import logging
import os
import time
import uuid
from pathlib import Path

logger = logging.getLogger("termplay.gamelog")

ENV_DIR = "TERMPLAY_GAMELOG_DIR"


class GameLogger:
    """Append-only structured event log scoped to a single match."""

    def __init__(self, game: str, *, match_id: str | None = None) -> None:
        self.game = game
        self.match_id = match_id or uuid.uuid4().hex[:8]
        self._seq = itertools.count(1)
        self._path = self._resolve_path()
        self._players: list[str] = []

    def _resolve_path(self) -> Path | None:
        root = os.environ.get(ENV_DIR)
        if not root:
            return None
        try:
            directory = Path(root)
            directory.mkdir(parents=True, exist_ok=True)
            return directory / f"{self.game}-{self.match_id}.jsonl"
        except OSError:
            logger.warning("gamelog: cannot use dir %s", root, exc_info=True)
            return None

    def event(self, event: str, **fields: object) -> dict[str, object]:
        """Record one event; returns the immutable record that was written."""
        record: dict[str, object] = {
            "ts": round(time.time(), 3),
            "game": self.game,
            "match": self.match_id,
            "seq": next(self._seq),
            "event": event,
            **fields,
        }
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        logger.info("%s", line)
        if self._path is not None:
            try:
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError:
                logger.warning("gamelog: write failed", exc_info=True)
        self._notify_stats(event, record)
        return record

    def _notify_stats(self, event: str, record: dict[str, object]) -> None:
        """Feed match results into the persistent stats store (best-effort:
        a stats failure must never take a running match down)."""
        if event == "match_start":
            players = record.get("players")
            if isinstance(players, list):
                self._players = [str(p) for p in players]
            return
        if event not in ("match_end", "match_over") or not self._players:
            return
        try:
            from termplay.engine.stats import get_stats_store

            store = get_stats_store()
            if store is not None:
                winner = record.get("winner")
                store.record_match(
                    self.game,
                    self.match_id,
                    self._players,
                    str(winner) if winner else None,
                )
        except Exception:
            logger.warning("stats: record_match failed", exc_info=True)
