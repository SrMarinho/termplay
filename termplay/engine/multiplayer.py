"""Multiplayer controller registry.

Solo games implement IGame (engine/game.py). Multiplayer games register a
factory here keyed by the same lowercase game name used by GameRegistry, so the
server can build the right controller from the room's selected game.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import ClassVar, Protocol

from termplay.engine.interfaces import ITransportAdapter


class IMultiplayerController(Protocol):
    """Anything the server can run for a multiplayer room."""

    async def run(self) -> None: ...


MpFactory = Callable[
    [Sequence[ITransportAdapter], list[str], list[bool]], IMultiplayerController
]


class MultiplayerRegistry:
    """Maps a game name to a factory that builds its multiplayer controller."""

    _factories: ClassVar[dict[str, MpFactory]] = {}

    @classmethod
    def register(cls, name: str, factory: MpFactory) -> None:
        cls._factories[name.lower()] = factory

    @classmethod
    def get(cls, name: str) -> MpFactory | None:
        return cls._factories.get(name.lower())
