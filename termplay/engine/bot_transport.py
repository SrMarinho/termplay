"""BotTransportAdapter — CPU bot that plays Uno via the standard transport interface.

The Uno controller communicates via write() (JSON state) and read_line() (move).
The bot parses incoming state snapshots and returns moves automatically.
"""

from __future__ import annotations

import asyncio
import json
import random
from collections import Counter

from typing_extensions import override

from termplay.engine.interfaces import ITransportAdapter

_THINK_DELAY = 0.8  # seconds between receiving state and responding
_MINIGAME_REACTION = (0.4, 2.6)  # bot reaction time range for the tap minigame
_UNO_TAG = "uno.state"
_COLORS = ("R", "G", "B", "Y")


def _best_color(hand_faces: list[str]) -> str:
    non_wild = [f.split(":")[0] for f in hand_faces if not f.startswith("W")]
    if not non_wild:
        return _COLORS[0]
    return Counter(non_wild).most_common(1)[0][0]


class BotTransportAdapter(ITransportAdapter):
    """Simulated player transport driven by simple Uno AI."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._playable: list[int] = []
        self._need_color = False
        self._need_target = False
        self._targets: list[int] = []
        self._counts: list[int] = []
        self._hand: list[str] = []
        self._phase = "play"
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
            if data.get("v") != _UNO_TAG:
                continue
            phase = data.get("phase")
            if phase == "play":
                self._phase = "play"
                self._playable = [int(i) for i in data.get("playable", [])]
                self._need_color = bool(data.get("need_color"))
                self._need_target = bool(data.get("need_target"))
                self._targets = [int(i) for i in data.get("targets", [])]
                self._counts = [int(p[1]) for p in data.get("players", [])]
                self._hand = [str(c) for c in data.get("hand", [])]
                self._move_ready.set()
            elif phase == "minigame":
                # Only react while still in play (not yet tapped this round).
                if not data.get("you_safe"):
                    self._phase = "minigame"
                    self._move_ready.set()
            elif phase in ("toast", "over"):
                pass  # ignore

    @override
    async def read_line(self) -> str:
        await self._move_ready.wait()
        self._move_ready.clear()

        if self._phase == "minigame":
            # Random reaction time so bots aren't always the slowest (or fastest).
            await asyncio.sleep(random.uniform(*_MINIGAME_REACTION))
            return "tap"

        await asyncio.sleep(_THINK_DELAY)

        if self._need_color:
            return _best_color(self._hand)

        if self._need_target and self._targets:
            # Swap with the smallest hand to steal the advantage.
            best = min(
                self._targets,
                key=lambda i: self._counts[i] if i < len(self._counts) else 1 << 30,
            )
            return str(best + 1)  # 1-indexed global player

        if self._playable:
            idx = self._playable[0]
            return str(idx + 1)  # 1-indexed

        return "d"  # draw

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
