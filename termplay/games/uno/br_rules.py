"""UNO Brazilian extras — zero-swap, multi-card play, and the '1' minigame."""

from __future__ import annotations

import asyncio
import contextlib
import random
import time

from termplay.games.uno.broadcaster import broadcast, broadcast_minigame, notify_private
from termplay.games.uno.context import MINIGAME_TIMEOUT, TURN_TIMEOUT, UnoContext, Player, face
from termplay.games.uno.effects import apply_effect, apply_multi_effect
from termplay.games.uno.input_reader import choose_target, get_multi_move
from termplay.games.uno.state import Card


async def do_zero_swap(ctx: UnoContext, player: Player, idx: int) -> None:
    targets = [i for i, p in enumerate(ctx.players) if p.active and i != idx]
    if not targets:
        return
    if len(targets) == 1:
        target: int | None = targets[0]
    else:
        ctx.turn_deadline = time.time() + TURN_TIMEOUT
        await broadcast(ctx, active_idx=idx, need_target_for=idx, targets=targets)
        target = await choose_target(ctx, player, targets)
    if target is None:
        ctx.message = f"{player.name} optou por não trocar de mão"
        ctx.log.event("zero_swap_skip", player=player.name)
        return
    ctx.state.hands[idx], ctx.state.hands[target] = ctx.state.hands[target], ctx.state.hands[idx]
    ctx.message = f"{player.name} trocou de mão com {ctx.players[target].name}"
    ctx.log.event("zero_swap", player=player.name, target=ctx.players[target].name)


async def do_multi_play(ctx: UnoContext, player: Player, idx: int, first_card: Card) -> None:
    multi_played: list[str] = [face(first_card)]
    ones_count = 1 if (ctx.rules.one_minigame and first_card.value == "1") else 0

    while True:
        same_idxs = [i for i, c in enumerate(ctx.state.hands[idx]) if c.value == first_card.value]
        if not same_idxs:
            break
        ctx.message = f"{player.name} jogou {len(multi_played)}× — jogue mais ou passe"
        ctx.turn_deadline = time.time() + TURN_TIMEOUT
        await broadcast(ctx, active_idx=idx, multi_played=multi_played, multi_value=first_card.value)
        pos = await get_multi_move(ctx, player, same_idxs)
        if pos is None:
            break
        next_card = ctx.state.play(idx, pos, "")
        multi_played.append(face(next_card))
        if ctx.rules.one_minigame and next_card.value == "1":
            ones_count += 1
        if ctx.state.winner() is not None:
            for _ in range(ones_count):
                await do_one_minigame(ctx, idx)
            return

    if len(multi_played) > 1:
        ctx.message = f"{player.name} jogou {len(multi_played)}× {first_card.value}!"
        ctx.log.event("multi_play", player=player.name, cards=multi_played, count=len(multi_played))

    for _ in range(ones_count):
        await do_one_minigame(ctx, idx)

    apply_multi_effect(ctx, first_card, len(multi_played))


async def do_one_minigame(ctx: UnoContext, idx: int) -> None:
    participants = [i for i, p in enumerate(ctx.players) if p.active]
    if len(participants) < 2:
        return
    safe: set[int] = set()
    deadline = time.time() + MINIGAME_TIMEOUT
    dot = _random_dot()
    ctx.log.event("minigame_start", players=len(participants))
    await broadcast_minigame(ctx, participants, safe, dot, deadline)

    pending: dict[asyncio.Task[str], int] = {
        asyncio.create_task(ctx.players[i].transport.read_line()): i
        for i in participants
    }
    try:
        while len(safe) < len(participants) - 1:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            done, _ = await asyncio.wait(pending.keys(), timeout=remaining, return_when=asyncio.FIRST_COMPLETED)
            if not done:
                break
            changed = False
            for task in done:
                i = pending.pop(task)
                with contextlib.suppress(Exception):
                    task.result()
                if i not in safe:
                    safe.add(i)
                    changed = True
            if changed:
                dot = _random_dot()
                await broadcast_minigame(ctx, participants, safe, dot, deadline)
    finally:
        for task in pending:
            task.cancel()
        for task in pending:
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await task

    losers = [i for i in participants if i not in safe]
    for i in losers:
        ctx.state.draw(i, 1)
        ctx.log.event("minigame_loser", player=ctx.players[i].name)
    if losers:
        names = ", ".join(ctx.players[i].name for i in losers)
        ctx.message = f"⚡ {names} foi o mais lento — comprou!"


def _random_dot() -> dict[str, float]:
    return {
        "x": round(random.uniform(0.1, 0.9), 3),
        "y": round(random.uniform(0.15, 0.85), 3),
    }
