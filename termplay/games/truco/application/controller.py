"""TrucoController — orchestrates a Truco match."""

from __future__ import annotations
import random
from collections.abc import Sequence

from termplay.engine.game_log import GameLogger
from termplay.engine.interfaces import ITransportAdapter
from termplay.games.truco.application.context import TrucoContext, Player
from termplay.games.truco.application.round_handler import play_round
from termplay.games.truco.application.state import TrucoState
from termplay.games.truco.conf import WINNING_SCORE
from termplay.games.truco.display.broadcaster import broadcast_over
from termplay.games.truco.ruleset import TrucoRuleset


def _build_teams(n: int, mode: str) -> list[list[int]]:
    if mode == "1v1" or n == 2:
        return [[0], [1]]
    # 2v2: alternating seats — P0,P2 = team 0; P1,P3 = team 1
    return [[i for i in range(n) if i % 2 == 0], [i for i in range(n) if i % 2 == 1]]


class TrucoController:
    def __init__(
        self,
        transports: Sequence[ITransportAdapter],
        names: list[str] | None = None,
        stealth_flags: list[bool] | None = None,
        ruleset: TrucoRuleset | None = None,
    ) -> None:
        _names = names or [f"Player {i + 1}" for i in range(len(transports))]
        players = [Player(t, n) for t, n in zip(transports, _names)]
        rules = ruleset or TrucoRuleset()
        teams = _build_teams(len(players), rules.mode)
        log = GameLogger("truco")
        mao = random.randrange(len(players))
        state = TrucoState.new(len(players), mao)
        self._ctx = TrucoContext(
            players=players, teams=teams, state=state, rules=rules, log=log
        )
        log.event("match_start", players=[p.name for p in players], teams=teams, vira=str(state.vira))

    async def run(self) -> None:
        ctx = self._ctx
        state: TrucoState = ctx.state
        n = len(ctx.players)
        mao = state.mao

        while max(state.score) < WINNING_SCORE:
            active = sum(p.active for p in ctx.players)
            if active < 2:
                break

            # New round: reset state keeping score
            mao = (mao + 1) % n
            ctx.state = TrucoState.new(n, mao, score=state.score)
            state = ctx.state
            ctx.log.event("round_start", mao=ctx.players[mao].name, vira=str(state.vira))

            await play_round(ctx)
            state = ctx.state  # re-bind after round

        ctx.message = _winner_message(ctx)
        ctx.log.event("match_over", score=state.score)
        await broadcast_over(ctx)


def _winner_message(ctx: TrucoContext) -> str:
    state: TrucoState = ctx.state
    winner_team = 0 if state.score[0] >= WINNING_SCORE else 1
    names = [ctx.players[i].name for i in ctx.teams[winner_team]]
    return f"{' & '.join(names)} venceu(m) a partida! ({state.score[0]}–{state.score[1]})"
