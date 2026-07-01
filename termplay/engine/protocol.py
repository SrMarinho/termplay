"""Protocolo de mensagens JSON entre TUI cliente e servidor multiplayer.

Cada mensagem é um objeto JSON em uma linha terminada por '\\n'.
Cliente → servidor usa a chave "action"; servidor → cliente usa "type".
"""

from __future__ import annotations

import json
from typing import Any

# Ações cliente → servidor
# create_room / join_room accept an optional "stealth": bool field — when true
# the server renders that player's game as plain log lines (disguise mode).
ACTION_CREATE_ROOM = "create_room"
ACTION_JOIN_ROOM = "join_room"
ACTION_START_GAME = "start_game"
ACTION_CHAT = "chat"
ACTION_LEAVE = "leave"
ACTION_GAME_INPUT = "game_input"
ACTION_ADD_BOT = "add_bot"    # host only: add a CPU bot to the room
ACTION_KICK = "kick"          # host only: remove player by name (field: "target")
ACTION_RECONNECT = "reconnect"  # fields: "token" (required), "code" (optional hint)

# Tipos servidor → cliente
TYPE_ROOM_CREATED = "room_created"
TYPE_ROOM_JOINED = "room_joined"
TYPE_ROOM_STATE = "room_state"
TYPE_CHAT = "chat"
TYPE_GAME_START = "game_start"
TYPE_GAME_RENDER = "game_render"
TYPE_GAME_OVER = "game_over"
TYPE_ERROR = "error"
TYPE_RECONNECTED = "reconnected"  # fields: code, you, in_game


def encode(msg: dict[str, Any]) -> bytes:
    """Serializa uma mensagem em uma linha JSON terminada por newline."""
    return (json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8")


def decode(line: bytes | str) -> dict[str, Any]:
    """Desserializa uma linha JSON em dict. Lança ValueError se inválida."""
    if isinstance(line, bytes):
        line = line.decode("utf-8")
    result = json.loads(line)
    if not isinstance(result, dict):
        raise ValueError("Mensagem de protocolo deve ser um objeto JSON")
    return result
