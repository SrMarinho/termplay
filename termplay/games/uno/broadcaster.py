"""UNO broadcaster — builds JSON payloads and fans them out to all players."""

from __future__ import annotations

import json

from termplay.games.uno.context import UNO_STATE_TAG, UnoContext, Player, face
from termplay.games.uno.display import render_log_view


async def safe_write(ctx: UnoContext, player: Player, text: str) -> None:
    try:
        await player.transport.write(text)
    except (ConnectionError, OSError):
        player.active = False


def _spectator_payload(ctx: UnoContext) -> str:
    """Public table view: piles, counts and turn info — never a hand."""
    st = ctx.state
    data = {
        "v": UNO_STATE_TAG,
        "phase": "play",
        "top": face(st.top),
        "color": st.active_color,
        "direction": st.direction,
        "current": st.current,
        "you": -1,
        "players": [[p.name, len(st.hands[i])] for i, p in enumerate(ctx.players)],
        "hand": [],
        "playable": [],
        "your_turn": False,
        "need_color": False,
        "need_target": False,
        "targets": [],
        "deadline": ctx.turn_deadline,
        "message": ctx.message,
        "pending_draws": st.pending_draws,
        "may_play_drawn": False,
        "drawn_card_idx": -1,
        "multi_played": [],
        "multi_value": "",
        "draws_remaining": 0,
        "drew_unplayable": False,
        "winner": "",
        "spectator": True,
    }
    return json.dumps(data) + "\n"


async def _feed_spectators(ctx: UnoContext, text: str) -> None:
    import asyncio

    async def send(transport: object) -> None:
        try:
            await transport.write(text)  # type: ignore[attr-defined]
        except (ConnectionError, OSError):
            pass  # room removes dead spectators from the feed

    await asyncio.gather(*(send(t) for t in list(ctx.spectators)))


def _payload(
    ctx: UnoContext,
    idx: int,
    *,
    your_turn: bool,
    need_color: bool,
    may_play_drawn: int | None = None,
    need_target: bool = False,
    targets: list[int] | None = None,
    multi_played: list[str] | None = None,
    multi_value: str = "",
    draws_remaining: int = 0,
    drew_unplayable: bool = False,
) -> str:
    st = ctx.state
    in_multi = multi_played is not None and your_turn
    if drew_unplayable:
        playable = []
    elif in_multi:
        playable = [i for i, c in enumerate(st.hands[idx]) if c.value == multi_value]
    elif may_play_drawn is not None:
        playable = [may_play_drawn]
    elif st.pending_draws > 0:
        pend = st.pending_draw_value
        if pend == "draw2":
            playable = [i for i, c in enumerate(st.hands[idx]) if c.value in ("draw2", "wild4")]
        else:
            playable = [i for i, c in enumerate(st.hands[idx]) if c.value == pend]
    else:
        hand = st.hands[idx]
        playable = [i for i, c in enumerate(hand) if st.playable(c)]
        if ctx.rules.wild4_strict:
            # Mirrors input_reader.get_move's wild4_strict check: a Wild+4 is
            # illegal while any non-wild card is playable. Keeping this list in
            # sync with that check matters for bots (BotTransportAdapter only
            # ever submits indices from this list — anything else silently
            # never gets a retry prompt, so a mismatch here hangs the bot's
            # turn until the timeout instead of it actually playing).
            has_non_wild_alt = any(
                not hand[i].is_wild for i in playable
            )
            if has_non_wild_alt:
                playable = [i for i in playable if not hand[i].is_wild or hand[i].value != "wild4"]
    data = {
        "v": UNO_STATE_TAG,
        "phase": "play",
        "top": face(st.top),
        "color": st.active_color,
        "direction": st.direction,
        "current": st.current,
        "you": idx,
        "players": [[p.name, len(st.hands[i])] for i, p in enumerate(ctx.players)],
        "hand": [face(c) for c in st.hands[idx]],
        "playable": playable,
        "your_turn": your_turn,
        "need_color": need_color,
        "need_target": need_target,
        "targets": targets or [],
        "deadline": ctx.turn_deadline,
        "message": ctx.message,
        "pending_draws": st.pending_draws,
        "may_play_drawn": may_play_drawn is not None,
        "drawn_card_idx": may_play_drawn if may_play_drawn is not None else -1,
        "multi_played": multi_played or [],
        "multi_value": multi_value,
        "draws_remaining": draws_remaining,
        "drew_unplayable": drew_unplayable,
        "winner": "",
    }
    return json.dumps(data) + "\n"


async def broadcast(
    ctx: UnoContext,
    *,
    active_idx: int,
    need_color_for: int | None = None,
    may_play_drawn: int | None = None,
    need_target_for: int | None = None,
    targets: list[int] | None = None,
    multi_played: list[str] | None = None,
    multi_value: str = "",
    draws_remaining: int = 0,
    drew_unplayable: bool = False,
) -> None:
    import asyncio
    prompt = need_color_for is not None or need_target_for is not None

    async def send(i: int, p: Player) -> None:
        if not p.active:
            return
        if p.stealth:
            await safe_write(ctx, p, render_log_view(
                ctx.state, ctx.names, i,
                is_active=(i == active_idx and not prompt),
                message=ctx.message,
            ))
        else:
            turn = i == active_idx and not prompt
            await safe_write(ctx, p, _payload(
                ctx, i,
                your_turn=turn,
                need_color=need_color_for == i,
                may_play_drawn=may_play_drawn if i == active_idx else None,
                need_target=need_target_for == i,
                targets=targets if need_target_for == i else None,
                multi_played=multi_played,
                multi_value=multi_value,
                draws_remaining=draws_remaining if i == active_idx else 0,
                drew_unplayable=drew_unplayable if i == active_idx else False,
            ))

    await asyncio.gather(*(send(i, p) for i, p in enumerate(ctx.players)))
    if ctx.spectators:
        await _feed_spectators(ctx, _spectator_payload(ctx))
    ctx.message = ""


async def broadcast_minigame(
    ctx: UnoContext,
    participants: list[int],
    safe: set[int],
    dot: dict[str, float],
    deadline: float,
) -> None:
    import asyncio

    async def send(i: int, p: Player) -> None:
        if not p.active:
            return
        if p.stealth:
            await safe_write(ctx, p, render_log_view(
                ctx.state, ctx.names, i,
                is_active=(i not in safe),
                message="minigame: clique no ponto!",
            ))
            return
        data = {
            "v": UNO_STATE_TAG,
            "phase": "minigame",
            "you": i,
            "players": [[pp.name, len(ctx.state.hands[j])] for j, pp in enumerate(ctx.players)],
            "dot": dot,
            "safe": sorted(safe),
            "participants": participants,
            "you_safe": i in safe,
            "deadline": deadline,
            "message": "Clique no ponto antes de sobrar!",
        }
        await safe_write(ctx, p, json.dumps(data) + "\n")

    await asyncio.gather(*(send(i, p) for i, p in enumerate(ctx.players)))


async def broadcast_over(ctx: UnoContext) -> None:
    import asyncio
    win = ctx.state.winner()
    name = ctx.players[win].name if win is not None else ""
    ctx.log.event("match_end", winner=name or None)

    async def send(i: int, p: Player) -> None:
        if not p.active:
            return
        if p.stealth:
            await safe_write(ctx, p, render_log_view(
                ctx.state, ctx.names, i, is_active=False,
                message=f"round.result winner={name or '-'}",
            ))
        else:
            data = {"v": UNO_STATE_TAG, "phase": "over", "you": i, "winner": name}
            await safe_write(ctx, p, json.dumps(data) + "\n")

    await asyncio.gather(*(send(i, p) for i, p in enumerate(ctx.players)))
    if ctx.spectators:
        over = {"v": UNO_STATE_TAG, "phase": "over", "you": -1, "winner": name}
        await _feed_spectators(ctx, json.dumps(over) + "\n")


async def notify_private(ctx: UnoContext, player: Player, idx: int, text: str) -> None:
    if player.stealth or not player.active:
        return
    data = {"v": UNO_STATE_TAG, "phase": "toast", "you": idx, "message": text}
    await safe_write(ctx, player, json.dumps(data) + "\n")


async def notify_left(ctx: UnoContext, gone: Player) -> None:
    import asyncio

    async def send(p: Player) -> None:
        if p is gone or not p.active or p.stealth:
            return
        data = {
            "v": UNO_STATE_TAG, "phase": "toast",
            "you": ctx.players.index(p),
            "message": f"👋 {gone.name} saiu da partida",
        }
        await safe_write(ctx, p, json.dumps(data) + "\n")

    await asyncio.gather(*(send(p) for p in ctx.players))
