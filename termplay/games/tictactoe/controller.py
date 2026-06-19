"""TicTacToeController — 2-player multiplayer Velha. Emits JSON state."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass

from termplay.engine.game_log import GameLogger
from termplay.engine.interfaces import ITransportAdapter
from termplay.games.tictactoe.state import TicTacToeState


@dataclass
class _Player:
    transport: ITransportAdapter
    name: str
    mark: str = ""
    active: bool = True


def _state_json(state: TicTacToeState, phase: str, turn: str, player: _Player) -> str:
    return json.dumps({
        "v": "velha.state",
        "cells": state.cells,
        "turn": turn,
        "phase": phase,
        "your_mark": player.mark,
        "winner": state.winner(),
    }) + "\r\n"


class TicTacToeController:
    """Coordinates a multiplayer Velha match over player transports."""

    def __init__(
        self,
        transports: Sequence[ITransportAdapter],
        names: list[str] | None = None,
        stealth_flags: list[bool] | None = None,
    ) -> None:
        _names = names or [f"Player {i + 1}" for i in range(len(transports))]
        self._players = [
            _Player(t, n)
            for t, n in zip(transports, _names, strict=False)
        ]
        for i, p in enumerate(self._players[:2]):
            p.mark = ["X", "O"][i]
        self._state = TicTacToeState()
        self._log = GameLogger("velha")
        self._log.event(
            "match_start",
            players=[p.name for p in self._players],
            marks={p.name: p.mark for p in self._players if p.mark},
        )

    async def run(self) -> None:
        contenders = [p for p in self._players if p.mark]
        if len(contenders) < 2:
            await self._broadcast("play", "")
            return
        await self._broadcast("play", "")
        turn = 0
        while self._state.winner() is None and not self._state.is_full:
            player = contenders[turn % 2]
            if not player.active:
                break
            await self._broadcast("play", player.mark)
            idx = await self._get_move(player)
            if idx is None:
                player.active = False
                self._log.event("leave", player=player.name)
                break
            self._state.place(idx, player.mark)
            self._log.event("move", player=player.name, mark=player.mark, cell=idx + 1)
            turn += 1
        await self._broadcast("over", "")
        win_mark = self._state.winner()
        winner = next((p for p in contenders if p.mark == win_mark), None)
        self._log.event(
            "match_end",
            outcome="win" if win_mark else "draw",
            winner=winner.name if winner else None,
        )

    async def _broadcast(self, phase: str, turn: str) -> None:
        await asyncio.gather(*(
            p.transport.write(_state_json(self._state, phase, turn, p))
            for p in self._players
        ))

    async def _get_move(self, player: _Player) -> int | None:
        while True:
            try:
                raw = (await player.transport.read_line()).strip().lower()
            except ConnectionError:
                return None
            if raw in ("q", "quit"):
                return None
            if raw.isdigit() and 1 <= int(raw) <= 9:
                idx = int(raw) - 1
                if self._state.cells[idx] == " ":
                    return idx
