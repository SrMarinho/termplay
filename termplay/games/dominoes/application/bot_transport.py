"""CPU bot for dominoes — greedy: plays the highest-pip playable tile."""

from __future__ import annotations

import asyncio
import json

from typing_extensions import override

from termplay.engine.interfaces import ITransportAdapter
from termplay.games.dominoes.application.broadcaster import DOMINOES_STATE_TAG

_THINK_DELAY = 0.8


class DominoesBotTransportAdapter(ITransportAdapter):
    """Simulated player driven by JSON state snapshots (wants_json)."""

    wants_json = True

    def __init__(self, name: str) -> None:
        self._name = name
        self._hand: list[list[int]] = []
        self._playable: list[int] = []
        self._move_ready = asyncio.Event()

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
            if data.get("v") != DOMINOES_STATE_TAG or not data.get("your_turn"):
                continue
            self._hand = [list(t) for t in data.get("hand", [])]
            self._playable = [int(i) for i in data.get("playable", [])]
            self._move_ready.set()

    @override
    async def read_line(self) -> str:
        await self._move_ready.wait()
        self._move_ready.clear()
        await asyncio.sleep(_THINK_DELAY)
        if not self._playable:
            return "q"  # defensive: controller never asks without a playable
        best = max(self._playable, key=lambda i: sum(self._hand[i]))
        return str(best + 1)

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
