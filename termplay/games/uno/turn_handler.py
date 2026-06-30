"""UNO turn handler — resolves draw, play, and pending-draw actions."""

from __future__ import annotations

import time

from termplay.games.uno.broadcaster import broadcast, notify_private
from termplay.games.uno.br_rules import do_multi_play, do_one_minigame, do_zero_swap
from termplay.games.uno.context import TURN_TIMEOUT, UnoContext, Player, face
from termplay.games.uno.effects import apply_effect, can_stack
from termplay.games.uno.input_reader import (
    choose_color,
    get_drawn_decision,
    wait_for_draw_confirm,
)
from termplay.games.uno.state import Card


async def handle_draw(ctx: UnoContext, player: Player, idx: int) -> None:
    if ctx.rules.draw_until_play:
        while True:
            drawn = ctx.state.draw(idx, 1)
            if not drawn:
                break
            if ctx.state.playable(drawn[0]):
                ctx.log.event("draw_until", player=player.name, card=face(drawn[0]))
                await apply_move(ctx, player, idx, len(ctx.state.hands[idx]) - 1)
                return
        ctx.message = f"{player.name} não conseguiu jogar"
        ctx.state.advance()
        return

    drawn = ctx.state.draw(idx, 1)
    f = face(drawn[0]) if drawn else "—"
    ctx.log.event("draw", player=player.name, card=f, hand=len(ctx.state.hands[idx]))

    if ctx.rules.draw_then_play and drawn and ctx.state.playable(drawn[0]):
        drawn_idx = len(ctx.state.hands[idx]) - 1
        ctx.message = f"{player.name} comprou — pode jogar"
        ctx.turn_deadline = time.time() + TURN_TIMEOUT
        await broadcast(ctx, active_idx=idx, may_play_drawn=drawn_idx)
        await notify_private(ctx, player, idx, f"Você comprou: {f}")
        decision = await get_drawn_decision(ctx, player, idx, drawn_idx)
        if decision == "play":
            await apply_move(ctx, player, idx, drawn_idx)
        else:
            ctx.message = f"{player.name} passou"
            ctx.log.event("pass_drawn", player=player.name)
            ctx.state.advance()
        return

    ctx.message = f"{player.name} comprou uma carta"
    await notify_private(ctx, player, idx, f"Você comprou: {f}")
    ctx.state.advance()


async def take_pending(ctx: UnoContext, player: Player, idx: int) -> None:
    count = ctx.state.pending_draws
    ctx.state.pending_draws = 0
    ctx.state.pending_draw_value = ""
    ctx.log.event("take_pending", player=player.name, count=count)

    if ctx.rules.manual_draw and count > 1:
        for k in range(count):
            ctx.state.draw(idx, 1)
            remaining = count - k - 1
            ctx.message = (
                f"{player.name} está comprando… ({k + 1}/{count})"
                if remaining else f"{player.name} comprou {count} cartas"
            )
            await broadcast(ctx, active_idx=idx, draws_remaining=remaining)
            if remaining:
                await wait_for_draw_confirm(ctx, player)
    else:
        ctx.state.draw(idx, count)
        ctx.message = f"{player.name} comprou {count} cartas"
        await notify_private(ctx, player, idx, f"Você comprou {count} cartas")

    ctx.state.advance()


async def apply_move(ctx: UnoContext, player: Player, idx: int, move: int) -> None:
    card = ctx.state.hands[idx][move]
    chosen = ""
    if card.is_wild:
        await broadcast(ctx, active_idx=idx, need_color_for=idx)
        chosen = await choose_color(ctx, player)
        ctx.log.event("color_chosen", player=player.name, color=chosen)
    played = ctx.state.play(idx, move, chosen)
    color = ctx.state.active_color
    suffix = f" → {color}" if played.is_wild else ""
    ctx.message = f"{player.name} jogou {face(played)}{suffix}"
    ctx.log.event(
        "play", player=player.name, card=face(played),
        active_color=color, wild=played.is_wild, hand=len(ctx.state.hands[idx]),
    )
    if ctx.state.winner() is not None:
        return
    if ctx.rules.zero_swap and played.value == "0":
        await do_zero_swap(ctx, player, idx)
    if (ctx.rules.multi_same_number
            and not played.is_wild
            and ctx.state.winner() is None):
        await do_multi_play(ctx, player, idx, played)
        return
    if ctx.rules.one_minigame and played.value == "1":
        await do_one_minigame(ctx, idx)
    apply_effect(ctx, played)
