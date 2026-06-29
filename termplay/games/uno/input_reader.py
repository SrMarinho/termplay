"""UNO input reader — reads player actions from their transports."""

from __future__ import annotations

import asyncio
import random
import time

from termplay.games.uno.context import TURN_TIMEOUT, UnoContext, Player
from termplay.games.uno.state import COLORS


async def get_move(
    ctx: UnoContext, player: Player, idx: int
) -> tuple[str, int | None] | None:
    """Return ("play", pos), ("draw", None), or None to leave."""
    hand = ctx.state.hands[idx]
    stacking = ctx.state.pending_draws > 0
    while True:
        remaining = ctx.turn_deadline - time.time()
        if remaining <= 0:
            ctx.message = f"{player.name} demorou — comprou"
            return ("draw", None)
        try:
            raw = (
                await asyncio.wait_for(player.transport.read_line(), timeout=remaining)
            ).strip().lower()
        except TimeoutError:
            ctx.message = f"{player.name} demorou — comprou"
            return ("draw", None)
        except ConnectionError:
            return None
        if raw in ("q", "quit", "sair"):
            return None
        if raw in ("d", "draw", "comprar"):
            return ("draw", None)
        if raw.isdigit():
            pos = int(raw) - 1
            if not (0 <= pos < len(hand)):
                continue
            card = hand[pos]
            if not ctx.state.playable(card):
                continue
            if stacking:
                from termplay.games.uno.effects import stacking_allowed
                if not stacking_allowed(ctx, card):
                    pending = ctx.state.pending_draw_value
                    hint = "Empilhe +2 ou +4" if pending == "draw2" else "Só +4 pode defender +4"
                    from termplay.games.uno.broadcaster import notify_private
                    await notify_private(ctx, player, idx, hint)
                    continue
            if (
                ctx.rules.wild4_strict
                and card.value == "wild4"
                and any((not c.is_wild) and ctx.state.playable(c) for c in hand)
            ):
                from termplay.games.uno.broadcaster import notify_private
                await notify_private(ctx, player, idx, "Wild+4 só quando não há outra carta jogável")
                continue
            return ("play", pos)


async def get_drawn_decision(
    ctx: UnoContext, player: Player, idx: int, drawn_idx: int
) -> str:
    while True:
        remaining = ctx.turn_deadline - time.time()
        if remaining <= 0:
            return "pass"
        try:
            raw = (
                await asyncio.wait_for(player.transport.read_line(), timeout=remaining)
            ).strip().lower()
        except (TimeoutError, ConnectionError):
            return "pass"
        if raw in ("p", "pass", "passar", "d", "draw"):
            return "pass"
        if raw.isdigit() and int(raw) - 1 == drawn_idx:
            return "play"


async def get_multi_move(
    ctx: UnoContext, player: Player, valid_idxs: list[int]
) -> int | None:
    """During multi-play: return a valid card index, or None to stop the chain."""
    while True:
        remaining = ctx.turn_deadline - time.time()
        if remaining <= 0:
            return None
        try:
            raw = (
                await asyncio.wait_for(player.transport.read_line(), timeout=remaining)
            ).strip().lower()
        except (TimeoutError, ConnectionError):
            return None
        if raw in ("p", "pass", "passar", "q", "quit", "sair"):
            return None
        if raw.isdigit():
            pos = int(raw) - 1
            if pos in valid_idxs:
                return pos


async def choose_color(ctx: UnoContext, player: Player) -> str:
    while True:
        remaining = ctx.turn_deadline - time.time()
        if remaining <= 0:
            return random.choice(COLORS)
        try:
            raw = (
                await asyncio.wait_for(player.transport.read_line(), timeout=remaining)
            ).strip().upper()
        except TimeoutError:
            return random.choice(COLORS)
        except ConnectionError:
            return COLORS[0]
        if raw in COLORS:
            return raw


async def choose_target(
    ctx: UnoContext, player: Player, targets: list[int]
) -> int | None:
    while True:
        remaining = ctx.turn_deadline - time.time()
        if remaining <= 0:
            return random.choice(targets)
        try:
            raw = (
                await asyncio.wait_for(player.transport.read_line(), timeout=remaining)
            ).strip().lower()
        except TimeoutError:
            return random.choice(targets)
        except ConnectionError:
            return targets[0]
        if raw == "skip":
            return None
        digits = raw.lstrip("t@p")
        if digits.isdigit():
            pick = int(digits) - 1
            if pick in targets:
                return pick


async def wait_for_draw_confirm(ctx: UnoContext, player: Player) -> None:
    try:
        await asyncio.wait_for(player.transport.read_line(), timeout=TURN_TIMEOUT)
    except (TimeoutError, ConnectionError):
        pass
