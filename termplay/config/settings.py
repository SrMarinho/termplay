"""Persistência de configurações do usuário entre execuções.

Grava JSON no diretório de config do SO (Windows: %APPDATA%; POSIX: ~/.config).
Sem dependências externas — só pathlib + variáveis de ambiente.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_NAME = "termplay"


def _config_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_NAME


def _config_file() -> Path:
    return _config_dir() / "config.json"


def load() -> dict[str, Any]:
    path = _config_file()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(data: dict[str, Any]) -> None:
    path = _config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_nickname() -> str:
    return str(load().get("nickname", ""))


def set_nickname(name: str) -> None:
    data = load()
    data["nickname"] = name
    save(data)


def get_stealth() -> bool:
    return bool(load().get("stealth", False))


def set_stealth(value: bool) -> None:
    data = load()
    data["stealth"] = value
    save(data)


def get_last_host() -> tuple[str, int]:
    data = load()
    return str(data.get("last_host", "")), int(data.get("last_port", 4443))


def set_last_host(host: str, port: int) -> None:
    data = load()
    data["last_host"] = host
    data["last_port"] = port
    save(data)
