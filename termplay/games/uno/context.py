"""Shared runtime context passed to every UNO subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field

from termplay.engine.game_log import GameLogger
from termplay.engine.interfaces import ITransportAdapter
from termplay.games.uno.ruleset import UnoRuleset
from termplay.games.uno.state import Card, UnoState

UNO_STATE_TAG = "uno.state"
TURN_TIMEOUT = 10
MINIGAME_TIMEOUT = 15


def face(card: Card) -> str:
    return f"{card.color}:{card.value}"


@dataclass
class Player:
    transport: ITransportAdapter
    name: str
    stealth: bool = False
    active: bool = True


@dataclass
class UnoContext:
    players: list[Player]
    state: UnoState
    rules: UnoRuleset
    log: GameLogger
    message: str = ""
    turn_deadline: float = 0.0
    # Live spectator transports (owned by the room). Watchers get the public
    # table view — no hands, no prompts.
    spectators: list[ITransportAdapter] = field(default_factory=list)

    @property
    def names(self) -> list[str]:
        return [p.name for p in self.players]
