"""Envite negotiation — Truco → Seis → Nove → Doze."""

from __future__ import annotations
import time
from termplay.games.truco.application.context import TrucoContext, player_team
from termplay.games.truco.conf import ENVITE_LADDER, RUN_VALUES, TURN_TIMEOUT
from termplay.games.truco.display.broadcaster import broadcast
from termplay.games.truco.display.input_reader import get_envite_response


def _next_offer(current: int) -> int | None:
    idx = ENVITE_LADDER.index(current)
    return ENVITE_LADDER[idx + 1] if idx + 1 < len(ENVITE_LADDER) else None


async def negotiate_envite(ctx: TrucoContext, asker_idx: int) -> int | None:
    """
    Negotiate envite starting with asker calling 'truco' (offer=3).
    Returns final stake if envite resolved (accepted or raised to max),
    or None if the asker's team already lost (opponent ran — asker gets RUN_VALUES[offer]).

    After this call, ctx.state.stake is updated and ctx.state.envite is cleared.
    The return value is the pts awarded to the asker's team IF they won the round,
    OR None signals the round ended (folded team loses pts per RUN_VALUES).
    """
    state = ctx.state
    asker_team = player_team(ctx, asker_idx)
    responder_team = 1 - asker_team

    offer = ENVITE_LADDER[0]  # 3
    state.envite = {"asker": asker_idx, "offer": offer}
    ctx.message = f"{ctx.players[asker_idx].name} pediu Truco!"

    while True:
        ctx.turn_deadline = time.time() + TURN_TIMEOUT
        await broadcast(ctx, active_player=asker_idx, phase="envite")

        # Collect responses from all opponents
        responder_indices = [i for i, _ in enumerate(ctx.players) if player_team(ctx, i) == responder_team and ctx.players[i].active]
        if not responder_indices:
            break

        # In 2v2 any opponent can respond; use first active responder
        # (proper 2v2 would need concurrent read, simplified here)
        resp_idx = responder_indices[0]
        resp_player = ctx.players[resp_idx]

        decision = await get_envite_response(ctx, resp_player, offer)

        if decision == "run":
            pts = RUN_VALUES[offer]
            state.score[asker_team] += pts
            state.envite = None
            ctx.message = f"{resp_player.name} correu — {ctx.players[asker_idx].name} ganha {pts} pt(s)"
            ctx.log.event("envite_run", asker=ctx.players[asker_idx].name, offer=offer, pts=pts)
            return None  # round over, points already awarded

        if decision == "accept":
            state.stake = offer
            state.envite = None
            ctx.message = f"{resp_player.name} aceitou — rodada vale {offer} pt(s)"
            ctx.log.event("envite_accept", asker=ctx.players[asker_idx].name, offer=offer)
            return offer

        # raise
        next_offer = _next_offer(offer)
        if next_offer is None:
            # Can't raise beyond doze — treat as accept
            state.stake = offer
            state.envite = None
            return offer

        offer = next_offer
        state.envite = {"asker": resp_idx, "offer": offer}
        ctx.message = f"{resp_player.name} aumentou para {_offer_name(offer)}!"
        ctx.log.event("envite_raise", player=resp_player.name, offer=offer)
        asker_idx = resp_idx
        asker_team, responder_team = responder_team, asker_team

    state.envite = None
    return state.stake


def _offer_name(offer: int) -> str:
    return {3: "Truco", 6: "Seis", 9: "Nove", 12: "Doze"}.get(offer, str(offer))
