"""UNO card effects — pure game logic applied after a card is played."""

from __future__ import annotations

from termplay.games.uno.context import UnoContext, face
from termplay.games.uno.state import Card


def stacking_allowed(ctx: UnoContext, card: Card) -> bool:
    """Whether `card` can be stacked on the current pending draw pile."""
    pending = ctx.state.pending_draw_value
    if pending == "draw2":
        return card.value in ("draw2", "wild4")
    return card.value == pending


def can_stack(ctx: UnoContext, idx: int) -> bool:
    """Whether player `idx` holds any card that defends the pending draw."""
    pending = ctx.state.pending_draw_value
    hand = ctx.state.hands[idx]
    if pending == "draw2":
        return any(c.value in ("draw2", "wild4") for c in hand)
    return any(c.value == pending for c in hand)


def apply_effect(ctx: UnoContext, card: Card) -> None:
    two_players = sum(p.active for p in ctx.players) == 2
    if card.value == "reverse":
        ctx.state.direction *= -1
        ctx.state.advance(skip=two_players)
        ctx.log.event("effect", type="reverse", direction=ctx.state.direction)
    elif card.value == "skip":
        ctx.state.advance(skip=True)
        ctx.log.event("effect", type="skip")
    elif card.value in ("draw2", "wild4"):
        count = 2 if card.value == "draw2" else 4
        if ctx.rules.stack_draws:
            ctx.state.pending_draws += count
            ctx.state.pending_draw_value = card.value
            ctx.state.advance()
            ctx.log.event("effect", type=card.value, stacked=ctx.state.pending_draws)
        else:
            victim = ctx.state.next_index()
            ctx.state.draw(victim, count)
            ctx.state.advance(skip=True)
            ctx.log.event("effect", type=card.value, victim=ctx.players[victim].name, drawn=count)
    else:
        ctx.state.advance()
