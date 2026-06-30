"""Round handler — deals hands, plays 3 tricks, awards points."""

from __future__ import annotations
import time
from termplay.games.truco.application.context import TrucoContext, player_team
from termplay.games.truco.application.state import TrucoState
from termplay.games.truco.application.trick_handler import play_trick
from termplay.games.truco.conf import TURN_TIMEOUT, WINNING_SCORE
from termplay.games.truco.display.broadcaster import broadcast
from termplay.games.truco.display.input_reader import get_mao_de_onze
from termplay.games.truco.domain.rules import round_winner


async def _check_mao_de_onze(ctx: TrucoContext) -> bool:
    """
    If a team has 11 pts and mao_de_onze rule is on, ask them to play or fold.
    Returns True if the round should proceed, False if someone folded.
    """
    if not ctx.rules.mao_de_onze:
        return True
    state: TrucoState = ctx.state

    for team_idx in range(2):
        if state.score[team_idx] != 11:
            continue
        # Ask each member of this team
        for player_idx in ctx.teams[team_idx]:
            player = ctx.players[player_idx]
            if not player.active:
                continue
            ctx.turn_deadline = time.time() + TURN_TIMEOUT
            ctx.message = f"{player.name}: jogar a mão-de-onze ou correr?"
            await broadcast(ctx, active_player=player_idx, phase="mao_de_onze")
            decision = await get_mao_de_onze(ctx, player)
            if not decision:
                opponent_team = 1 - team_idx
                state.score[opponent_team] += 1
                ctx.message = f"Time {team_idx + 1} correu da mão-de-onze — time {opponent_team + 1} ganha 1pt"
                ctx.log.event("mao_de_onze_fold", team=team_idx)
                return False
        return True  # team decided to play
    return True


async def play_round(ctx: TrucoContext) -> None:
    """Play one complete round (3 tricks). Updates score in place."""
    state: TrucoState = ctx.state

    proceed = await _check_mao_de_onze(ctx)
    if not proceed:
        return

    mao_team = player_team(ctx, state.mao)

    for trick_num in range(3):
        await broadcast(ctx, active_player=state.current_player)
        trick_team, folded = await play_trick(ctx)

        if folded:
            # Opponent ran from envite — score already awarded in negotiate_envite
            return

        state.tricks.append(trick_team)
        winner = round_winner(state.tricks, mao_team)

        if winner is not None:
            state.score[winner] += state.stake
            ctx.message = (
                f"Rodada para time {winner + 1}! +{state.stake}pt(s) "
                f"(placar: {state.score[0]}–{state.score[1]})"
            )
            ctx.log.event("round_over", winner=winner, stake=state.stake, score=state.score)
            await broadcast(ctx, active_player=state.current_player)
            return

        if trick_num < 2:
            # Find who leads next trick
            if trick_team is not None:
                # Winner of trick leads
                lead_candidates = [
                    i for i in state.trick_order if player_team(ctx, i) == trick_team
                ]
                lead = lead_candidates[0] if lead_candidates else state.trick_order[0]
            else:
                # Tie: same lead as before
                lead = state.trick_order[0]
            state.reset_table(lead)

    # Round ended without 2-win winner (shouldn't normally reach here)
    winner = round_winner(state.tricks, mao_team)
    if winner is None:
        winner = mao_team
    state.score[winner] += state.stake
    ctx.log.event("round_over", winner=winner, stake=state.stake, score=state.score)
