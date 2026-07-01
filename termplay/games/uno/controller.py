"""UnoController — orchestrates a multiplayer Uno match."""

from __future__ import annotations

import random
import time
from collections.abc import Sequence

from termplay.engine.game_log import GameLogger
from termplay.engine.interfaces import ITransportAdapter
from termplay.games.uno.broadcaster import broadcast, broadcast_over, notify_left
from termplay.games.uno.context import TURN_TIMEOUT, UnoContext, Player, face
from termplay.games.uno.effects import can_stack
from termplay.games.uno.input_reader import get_move
from termplay.games.uno.ruleset import UnoRuleset
from termplay.games.uno.state import UnoState
from termplay.games.uno.turn_handler import apply_move, handle_draw, take_pending


class UnoController:
    """Coordinates a multiplayer Uno match over player transports."""

    def __init__(
        self,
        transports: Sequence[ITransportAdapter],
        names: list[str] | None = None,
        stealth_flags: list[bool] | None = None,
        ruleset: UnoRuleset | None = None,
    ) -> None:
        _names = names or [f"Player {i + 1}" for i in range(len(transports))]
        _stealth = stealth_flags or [False] * len(transports)
        players = [
            Player(t, n, s)
            for t, n, s in zip(transports, _names, _stealth, strict=False)
        ]
        random.shuffle(players)
        rules = ruleset or UnoRuleset.standard()
        state = UnoState.new(len(players))
        log = GameLogger("uno")
        self._ctx = UnoContext(players=players, state=state, rules=rules, log=log)
        log.event(
            "match_start",
            players=self._ctx.names,
            top=face(state.top),
            active_color=state.active_color,
            hand_size=len(state.hands[0]),
        )
        if rules.initial_card_effect:
            self._apply_initial_card()

    def add_spectators(self, transports: list[ITransportAdapter]) -> None:
        """Attach the room's live spectator feed (see Room.spectator_feed)."""
        self._ctx.spectators = transports

    def _apply_initial_card(self) -> None:
        card = self._ctx.state.top
        if card.value == "skip":
            self._ctx.state.advance()
        elif card.value == "reverse":
            self._ctx.state.direction = -1
            self._ctx.state.advance()
        elif card.value == "draw2":
            self._ctx.state.draw(self._ctx.state.current, 2)
            self._ctx.state.advance()

    async def run(self) -> None:
        ctx = self._ctx
        while ctx.state.winner() is None:
            idx = ctx.state.current
            player = ctx.players[idx]
            if not player.active:
                ctx.state.advance()
                continue
            if ctx.state.pending_draws > 0 and not can_stack(ctx, idx):
                await take_pending(ctx, player, idx)
                continue
            ctx.turn_deadline = time.time() + TURN_TIMEOUT
            await broadcast(ctx, active_idx=idx)
            ctx.log.event(
                "turn", player=player.name, idx=idx,
                top=face(ctx.state.top), active_color=ctx.state.active_color,
                direction=ctx.state.direction, hand=len(ctx.state.hands[idx]),
                playable=sum(ctx.state.playable(c) for c in ctx.state.hands[idx]),
            )
            move = await get_move(ctx, player, idx)
            if move is None:
                player.active = False
                ctx.message = f"{player.name} saiu da partida"
                ctx.log.event("leave", player=player.name)
                remaining = sum(p.active for p in ctx.players)
                await notify_left(ctx, player)
                if remaining < 2:
                    break
                ctx.state.advance()
                continue
            mtype, value = move
            if mtype == "play":
                assert value is not None
                await apply_move(ctx, player, idx, value)
            elif ctx.state.pending_draws > 0:
                await take_pending(ctx, player, idx)
            else:
                await handle_draw(ctx, player, idx)
        await broadcast_over(ctx)
