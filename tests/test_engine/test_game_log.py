"""Tests for the structured game event log."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from termplay.engine.game_log import ENV_DIR, GameLogger


def test_event_returns_record_with_sequence() -> None:
    log = GameLogger("uno", match_id="abc")
    first = log.event("match_start", players=["A", "B"])
    second = log.event("turn", player="A")
    assert first["game"] == "uno"
    assert first["match"] == "abc"
    assert first["seq"] == 1
    assert second["seq"] == 2
    assert first["players"] == ["A", "B"]


def test_writes_jsonl_when_dir_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_DIR, str(tmp_path))
    log = GameLogger("velha", match_id="xyz")
    log.event("move", player="A", cell=5)
    log.event("match_end", outcome="win")
    path = tmp_path / "velha-xyz.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rows = [json.loads(line) for line in lines]
    assert rows[0]["event"] == "move"
    assert rows[0]["cell"] == 5
    assert rows[1]["event"] == "match_end"


def test_no_file_without_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENV_DIR, raising=False)
    log = GameLogger("forca", match_id="nofile")
    log.event("guess", value="A")
    assert not list(tmp_path.glob("*.jsonl"))
