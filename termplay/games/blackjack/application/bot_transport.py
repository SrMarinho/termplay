"""BlackjackBotTransportAdapter — CPU player for player-vs-player Blackjack.

The versus controller talks via write() (JSON ``blackjack.state``) and read_line()
(action). The bot uses the classic dealer policy: hit while its hand value is
below 17, otherwise stand.
"""

from __future__ import annotations

import asyncio
import json
import random

from typing_extensions import override

from termplay.engine.interfaces import ITransportAdapter

_BJ_TAG = "blackjack.state"
_STAND_ON = 17
_REACTION = (0.5, 1.3)  # seconds, so the bot feels human


class BlackjackBotTransportAdapter(ITransportAdapter):
    """Simulated Blackjack player: hit below 17, else stand."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._value = 0
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
            if data.get("v") != _BJ_TAG:
                continue
            if data.get("phase") == "play" and data.get("your_turn"):
                self._value = int(data.get("hand_value", 0))
                self._move_ready.set()

    @override
    async def read_line(self) -> str:
        await self._move_ready.wait()
        self._move_ready.clear()
        await asyncio.sleep(random.uniform(*_REACTION))
        return "h" if self._value < _STAND_ON else "s"

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
