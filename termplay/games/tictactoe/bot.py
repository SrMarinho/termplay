"""VelhaBot — AI for Tic-Tac-Toe. Easy: random. Hard: minimax."""

from __future__ import annotations

import asyncio
import json
import random

from typing_extensions import override

from termplay.engine.interfaces import ITransportAdapter

_LINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
)
_THINK_DELAY = 0.6


def _winner(cells: list[str]) -> str | None:
    for a, b, c in _LINES:
        if cells[a] != " " and cells[a] == cells[b] == cells[c]:
            return cells[a]
    return None


def _minimax(cells: list[str], bot_mark: str, is_max: bool) -> int:
    opp = "O" if bot_mark == "X" else "X"
    w = _winner(cells)
    if w == bot_mark:
        return 10
    if w == opp:
        return -10
    if all(c != " " for c in cells):
        return 0
    scores = []
    for i in range(9):
        if cells[i] == " ":
            cells[i] = bot_mark if is_max else opp
            scores.append(_minimax(cells, bot_mark, not is_max))
            cells[i] = " "
    return max(scores) if is_max else min(scores)


class VelhaBot:
    @staticmethod
    def easy_move(cells: list[str]) -> int:
        empty = [i for i, c in enumerate(cells) if c == " "]
        return random.choice(empty)

    @staticmethod
    def hard_move(cells: list[str], mark: str) -> int:
        best_score = -100
        best_idx = -1
        for i in range(9):
            if cells[i] == " ":
                cells[i] = mark
                score = _minimax(cells, mark, False)
                cells[i] = " "
                if score > best_score:
                    best_score = score
                    best_idx = i
        return best_idx


class VelhaBotTransportAdapter(ITransportAdapter):
    """Transport adapter that plugs into TicTacToeController as a bot player."""

    def __init__(self, difficulty: str = "easy") -> None:
        self._difficulty = difficulty
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    @override
    async def write(self, text: str) -> None:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except (ValueError, TypeError):
                continue
            if data.get("v") != "velha.state":
                continue
            if data.get("phase") != "play":
                continue
            my_mark = str(data.get("your_mark", ""))
            if not my_mark or data.get("turn") != my_mark:
                continue
            cells = list(data.get("cells", [" "] * 9))
            await asyncio.sleep(_THINK_DELAY)
            if self._difficulty == "hard":
                idx = VelhaBot.hard_move(cells[:], my_mark)
            else:
                idx = VelhaBot.easy_move(cells)
            await self._queue.put(str(idx + 1))

    @override
    async def read_line(self) -> str:
        return await self._queue.get()

    @override
    async def read_char(self) -> str:
        return await self.read_line()

    @override
    async def close(self) -> None:
        pass

    @property
    @override
    def width(self) -> int:
        return 80
