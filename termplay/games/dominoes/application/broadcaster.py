"""Dominoes rendering: pretty ANSI for humans, JSON snapshots for bots.

Bot transports mark themselves with ``wants_json = True`` (duck-typed) and get
one machine-readable line per broadcast instead of the drawn board.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from termplay.engine.interfaces import ITransportAdapter
from termplay.games.dominoes.domain.match_state import MatchState

DOMINOES_STATE_TAG = "dominoes.state"


@dataclass
class Seat:
    transport: ITransportAdapter
    name: str
    stealth: bool = False
    active: bool = True


def _board_line(state: MatchState) -> str:
    if state.board.is_empty:
        return "(mesa vazia — jogue a primeira pedra)"
    return " ".join(str(t) for t in state.board.line)


def _hand_view(state: MatchState, idx: int) -> str:
    playable = set(state.playable_indices(idx))
    parts = []
    for i, tile in enumerate(state.hands[idx]):
        mark = "▶" if i in playable else " "
        parts.append(f" {mark}{i + 1}:{tile}")
    return "".join(parts)


def render_pretty(state: MatchState, seats: list[Seat], idx: int, message: str) -> str:
    counts = "  ".join(
        f"{s.name}: {len(state.hands[i])}{' ◀' if i == state.current else ''}"
        for i, s in enumerate(seats)
    )
    your_turn = state.current == idx
    lines = [
        "┌─ DOMINÓ ─────────────────────────────────────────┐",
        f"  {counts}   dorme: {len(state.boneyard)}",
        "",
        f"  mesa: {_board_line(state)}",
        "",
        f"  sua mão:{_hand_view(state, idx)}",
        f"  {message}" if message else "",
        "  ▶ Sua vez! Número da pedra (+' e' p/ esquerda). "
        if your_turn
        else f"  aguardando {seats[state.current].name}…",
        "└──────────────────────────────────────────────────┘",
    ]
    return "\r\n" + "\r\n".join(line for line in lines if line) + "\r\n"


def render_json(state: MatchState, seats: list[Seat], idx: int, message: str) -> str:
    data = {
        "v": DOMINOES_STATE_TAG,
        "phase": "play",
        "you": idx,
        "current": state.current,
        "your_turn": state.current == idx,
        "players": [[s.name, len(state.hands[i])] for i, s in enumerate(seats)],
        "board": [[t.a, t.b] for t in state.board.line],
        "left_end": state.board.left_end,
        "right_end": state.board.right_end,
        "hand": [[t.a, t.b] for t in state.hands[idx]],
        "playable": state.playable_indices(idx),
        "boneyard": len(state.boneyard),
        "message": message,
    }
    return json.dumps(data) + "\n"


async def broadcast(state: MatchState, seats: list[Seat], message: str = "") -> None:
    async def send(i: int, seat: Seat) -> None:
        if not seat.active:
            return
        try:
            if getattr(seat.transport, "wants_json", False):
                await seat.transport.write(render_json(state, seats, i, message))
            else:
                await seat.transport.write(render_pretty(state, seats, i, message))
        except (ConnectionError, OSError):
            seat.active = False

    await asyncio.gather(*(send(i, s) for i, s in enumerate(seats)))


async def broadcast_text(seats: list[Seat], text: str) -> None:
    async def send(seat: Seat) -> None:
        if not seat.active:
            return
        try:
            if getattr(seat.transport, "wants_json", False):
                return  # bots only consume state snapshots
            await seat.transport.write(f"\r\n{text}\r\n")
        except (ConnectionError, OSError):
            seat.active = False

    await asyncio.gather(*(send(s) for s in seats))
