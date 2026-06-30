"""Play a single trick: collect one card from each player, resolve winner."""

from __future__ import annotations
import time
from termplay.games.truco.application.context import TrucoContext, player_team
from termplay.games.truco.application.envite import negotiate_envite
from termplay.games.truco.application.state import TrucoState
from termplay.games.truco.conf import TURN_TIMEOUT
from termplay.games.truco.display.broadcaster import broadcast
from termplay.games.truco.display.input_reader import get_play
from termplay.games.truco.domain.rules import trick_winner


async def play_trick(ctx: TrucoContext) -> tuple[int | None, bool]:
    """
    Each active player plays one card in trick_order.
    Returns (winning_team | None for tie, envite_folded: bool).
    envite_folded=True means opponent ran from truco and round should end.
    """
    state: TrucoState = ctx.state
    n = len(ctx.players)

    for _ in range(n):
        player_idx = state.current_player
        player = ctx.players[player_idx]

        if not player.active:
            # Auto-play first available card for disconnected player
            if state.hands[player_idx]:
                state.table[player_idx] = state.hands[player_idx].pop(0)
            state.current += 1
            continue

        ctx.turn_deadline = time.time() + TURN_TIMEOUT
        await broadcast(ctx, active_player=player_idx)
        ctx.log.event("turn", player=player.name, hand=len(state.hands[player_idx]))

        action, value = await get_play(ctx, player, player_idx)

        if action == "quit":
            player.active = False
            ctx.message = f"{player.name} saiu"
            state.current += 1
            continue

        if action == "timeout":
            card_idx = 0
            card = state.hands[player_idx].pop(card_idx)
            state.table[player_idx] = card
            ctx.message = f"{player.name} jogou {card} (tempo esgotado)"
            ctx.log.event("play_timeout", player=player.name, card=str(card))
            state.current += 1
            continue

        if action == "truco":
            result = await negotiate_envite(ctx, player_idx)
            if result is None:
                # Opponent ran — round over
                return None, True
            # Envite accepted or raised — continue with same player's turn
            ctx.turn_deadline = time.time() + TURN_TIMEOUT
            await broadcast(ctx, active_player=player_idx)
            action, value = await get_play(ctx, player, player_idx)
            if action in ("quit", "timeout") or value is None:
                card = state.hands[player_idx].pop(0)
                state.table[player_idx] = card
                ctx.message = f"{player.name} jogou {card}"
                ctx.log.event("play", player=player.name, card=str(card))
                state.current += 1
                continue

        # action == "play"
        assert value is not None
        card = state.hands[player_idx].pop(value)
        state.table[player_idx] = card
        ctx.message = f"{player.name} jogou {card}"
        ctx.log.event("play", player=player.name, card=str(card))
        state.current += 1

    # Resolve trick
    plays = [
        (player_team(ctx, i), card)
        for i, card in enumerate(state.table)
        if card is not None
    ]
    winner_team = trick_winner(plays, state.vira)
    ctx.log.event("trick", winner_team=winner_team, plays=[(t, str(c)) for t, c in plays])
    return winner_team, False
