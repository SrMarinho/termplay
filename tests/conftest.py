"""Global test fixtures."""

from __future__ import annotations

import pytest

from termplay.engine.stats import ENV_DB, reset_stats_store


@pytest.fixture(autouse=True)
def _isolate_stats_store(monkeypatch: pytest.MonkeyPatch):
    """Keep test matches out of the user's real ~/.termplay/stats.db.

    Tests that need a live store re-point ENV_DB themselves and call
    reset_stats_store() (see test_stats.py).
    """
    monkeypatch.setenv(ENV_DB, "off")
    reset_stats_store()
    yield
    reset_stats_store()
