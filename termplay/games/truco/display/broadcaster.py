from __future__ import annotations
import asyncio
import json
from termplay.games.truco.application.context import TrucoContext, player_team, partner_idx


def _card_str(card: object) -> str | None:
    return str(card) if card is not None else None


def _payload(ctx: TrucoContext, player_idx: int, *, your_turn: bool, phase: str) -> str:
    state = ctx.state
    partner = partner_idx(ctx, player_idx)
    partner_hand = (
        [str(c) for c in state.hands[partner]]
        if partner is not None and ctx.rules.mode == "2v2"
        else None
    )
    return json.dumps({
        "v": "truco.state",
        "phase": phase,
        "your_hand": [str(c) for c in state.hands[player_idx]],
        "partner_hand": partner_hand,
        "vira": str(state.vira),
        "table": [_card_str(c) for c in state.table],
        "trick_order": state.trick_order,
        "tricks": state.tricks,
        "score": state.score,
        "stake": state.stake,
        "envite": state.envite,
        "mao": state.mao,
        "current": state.current_player,
        "your_turn": your_turn,
        "deadline": ctx.turn_deadline,
        "you": player_idx,
        "players": ctx.names,
        "teams": ctx.teams,
        "mode": ctx.rules.mode,
        "message": ctx.message,
    })


async def _safe_write(ctx: TrucoContext, player: object, text: str) -> None:
    try:
        await player.transport.write(text)
    except ConnectionError:
        player.active = False


async def broadcast(ctx: TrucoContext, *, active_player: int, phase: str = "play") -> None:
    coros = [
        _safe_write(ctx, player, _payload(ctx, i, your_turn=(i == active_player), phase=phase))
        for i, player in enumerate(ctx.players)
        if player.active
    ]
    await asyncio.gather(*coros)


async def broadcast_over(ctx: TrucoContext) -> None:
    coros = [
        _safe_write(ctx, player, _payload(ctx, i, your_turn=False, phase="over"))
        for i, player in enumerate(ctx.players)
        if player.active
    ]
    await asyncio.gather(*coros)


async def notify(ctx: TrucoContext, player: object, text: str) -> None:
    await _safe_write(ctx, player, text)
