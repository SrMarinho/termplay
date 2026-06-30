from __future__ import annotations
from dataclasses import dataclass
from termplay.engine.game_log import GameLogger
from termplay.engine.interfaces import ITransportAdapter
from termplay.games.truco.ruleset import TrucoRuleset


@dataclass
class Player:
    transport: ITransportAdapter
    name: str
    active: bool = True


@dataclass
class TrucoContext:
    players: list[Player]
    teams: list[list[int]]  # [[0,2],[1,3]] or [[0],[1]]
    state: object           # TrucoState — typed as object to avoid circular import
    rules: TrucoRuleset
    log: GameLogger
    message: str = ""
    turn_deadline: float = 0.0

    @property
    def names(self) -> list[str]:
        return [p.name for p in self.players]


def player_team(ctx: TrucoContext, player_idx: int) -> int:
    for team_idx, members in enumerate(ctx.teams):
        if player_idx in members:
            return team_idx
    raise ValueError(f"Player {player_idx} not in any team")


def partner_idx(ctx: TrucoContext, player_idx: int) -> int | None:
    team = player_team(ctx, player_idx)
    members = [m for m in ctx.teams[team] if m != player_idx]
    return members[0] if members else None
