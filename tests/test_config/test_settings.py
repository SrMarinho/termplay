"""Testes para persistência de settings do usuário."""

from __future__ import annotations

from pathlib import Path

import pytest

from termplay.config import settings


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


class TestNickname:
    def test_round_trip(self) -> None:
        settings.set_nickname("Ana")
        assert settings.get_nickname() == "Ana"

    def test_default_empty_when_missing(self) -> None:
        assert settings.get_nickname() == ""

    def test_overwrite_keeps_latest(self) -> None:
        settings.set_nickname("Ana")
        settings.set_nickname("Bob")
        assert settings.get_nickname() == "Bob"


class TestLoad:
    def test_missing_file_returns_empty(self) -> None:
        assert settings.load() == {}

    def test_corrupt_file_returns_empty(self) -> None:
        path = settings._config_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not valid json", encoding="utf-8")
        assert settings.load() == {}

    def test_set_nickname_merges_existing(self) -> None:
        settings.save({"other": 1})
        settings.set_nickname("Ana")
        data = settings.load()
        assert data["other"] == 1
        assert data["nickname"] == "Ana"
