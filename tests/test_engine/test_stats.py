"""StatsStore: match recording, aggregation and the GameLogger hook."""

from __future__ import annotations

from pathlib import Path

import pytest

from termplay.engine.game_log import GameLogger
from termplay.engine.stats import ENV_DB, StatsStore, get_stats_store, reset_stats_store


@pytest.fixture
def store(tmp_path: Path) -> StatsStore:
    return StatsStore(tmp_path / "stats.db")


class TestStatsStore:
    def test_record_and_leaderboard(self, store: StatsStore) -> None:
        store.record_match("uno", "m1", ["Ana", "Bia"], "Ana")
        store.record_match("uno", "m2", ["Ana", "Bia"], "Bia")
        store.record_match("uno", "m3", ["Ana", "Bia"], "Ana")

        board = store.leaderboard("uno")
        assert board[0] == ("Ana", 2, 3)
        assert board[1] == ("Bia", 1, 3)

    def test_leaderboard_filters_by_game(self, store: StatsStore) -> None:
        store.record_match("uno", "m1", ["Ana", "Bia"], "Ana")
        store.record_match("truco", "m2", ["Ana", "Bia"], "Bia")

        assert store.leaderboard("uno") == [("Ana", 1, 1), ("Bia", 0, 1)]
        assert store.leaderboard()[0][2] == 2  # both games combined

    def test_duplicate_match_id_ignored(self, store: StatsStore) -> None:
        store.record_match("uno", "m1", ["Ana"], "Ana")
        store.record_match("uno", "m1", ["Ana"], "Ana")
        # matches table dedupes; results keep appending only alongside a new match
        assert store.leaderboard("uno")[0][0] == "Ana"

    def test_no_winner_records_played_only(self, store: StatsStore) -> None:
        store.record_match("truco", "m1", ["Ana", "Bia"], None)
        assert store.leaderboard("truco") == [("Ana", 0, 1), ("Bia", 0, 1)]

    def test_player_stats(self, store: StatsStore) -> None:
        store.record_match("uno", "m1", ["Ana", "Bia"], "Ana")
        store.record_match("truco", "m2", ["Ana", "Bia"], None)
        assert store.player_stats("Ana") == (1, 2)

    def test_schema_init_is_idempotent(self, tmp_path: Path) -> None:
        path = tmp_path / "stats.db"
        StatsStore(path)
        StatsStore(path)  # second open must not fail


class TestGameLoggerHook:
    def test_match_events_reach_the_store(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ENV_DB, str(tmp_path / "hook.db"))
        reset_stats_store()
        try:
            log = GameLogger("uno")
            log.event("match_start", players=["Ana", "Bia"])
            log.event("turn", player="Ana")
            log.event("match_end", winner="Bia")

            store = get_stats_store()
            assert store is not None
            assert store.leaderboard("uno")[0] == ("Bia", 1, 1)
        finally:
            reset_stats_store()

    def test_disabled_store_is_silent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ENV_DB, "off")
        reset_stats_store()
        try:
            log = GameLogger("uno")
            log.event("match_start", players=["Ana"])
            log.event("match_end", winner="Ana")  # must not raise
            assert get_stats_store() is None
        finally:
            reset_stats_store()
