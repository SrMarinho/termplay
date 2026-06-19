"""UnoController — turn-based multiplayer Uno with structured state output.

The server stays authoritative for game state. Each turn it pushes a per-player
JSON snapshot (hand, pile, opponents, whose turn, whether a color is needed) which
the visual ``UnoGameScreen`` renders with Textual widgets. Disguise-mode players
instead receive server-log lines. Client input (card number / ``d`` / color letter)
arrives through the normal game-input channel.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass

from termplay.engine.game_log import GameLogger
from termplay.engine.interfaces import ITransportAdapter
from termplay.games.uno.display import render_log_view
from termplay.games.uno.state import COLORS, Card, UnoState

UNO_STATE_TAG = "uno.state"


def _face(card: Card) -> str:
    return f"{card.color}:{card.value}"


@dataclass
class _Player:
    transport: ITransportAdapter
    name: str
    stealth: bool = False
    active: bool = True


class UnoController:
    """Coordinates a multiplayer Uno match over player transports."""

    def __init__(
        self,
        transports: Sequence[ITransportAdapter],
        names: list[str] | None = None,
        stealth_flags: list[bool] | None = None,
    ) -> None:
        _names = names or [f"Player {i + 1}" for i in range(len(transports))]
        _stealth = stealth_flags or [False] * len(transports)
        self._players = [
            _Player(t, n, s)
            for t, n, s in zip(transports, _names, _stealth, strict=False)
        ]
        self._state = UnoState.new(len(self._players))
        self._message = ""
        self._log = GameLogger("uno")
        self._log.event(
            "match_start",
            players=self._names,
            top=_face(self._state.top),
            active_color=self._state.active_color,
            hand_size=len(self._state.hands[0]),
        )

    @property
    def _names(self) -> list[str]:
        return [p.name for p in self._players]

    async def run(self) -> None:
        while self._state.winner() is None:
            idx = self._state.current
            player = self._players[idx]
            if not player.active:
                self._state.advance()
                continue
            await self._broadcast(active_idx=idx)
            self._log.event(
                "turn",
                player=player.name,
                idx=idx,
                top=_face(self._state.top),
                active_color=self._state.active_color,
                direction=self._state.direction,
                hand=len(self._state.hands[idx]),
                playable=sum(
                    self._state.playable(c) for c in self._state.hands[idx]
                ),
            )
            move = await self._get_move(player, idx)
            if move is None:
                player.active = False
                self._message = f"{player.name} saiu da partida"
                self._log.event("leave", player=player.name)
                remaining = sum(p.active for p in self._players)
                await self._notify_left(player)
                if remaining < 2:
                    break
                self._state.advance()
                continue
            await self._apply_move(player, idx, move)
        await self._broadcast_over()

    async def _notify_left(self, gone: _Player) -> None:
        """Tell remaining players that someone left."""
        async def send(p: _Player) -> None:
            if p is gone or not p.active:
                return
            if p.stealth:
                return  # reflected in next table broadcast
            data = {
                "v": UNO_STATE_TAG,
                "phase": "toast",
                "you": self._players.index(p),
                "message": f"👋 {gone.name} saiu da partida",
            }
            await self._safe_write(p, json.dumps(data) + "\n")

        await asyncio.gather(*(send(p) for p in self._players))

    # ── moves ─────────────────────────────────────────────────────────────────

    async def _apply_move(self, player: _Player, idx: int, move: int | str) -> None:
        if move == "draw":
            drawn = self._state.draw(idx, 1)
            face = _face(drawn[0]) if drawn else "—"
            self._message = f"{player.name} comprou uma carta"
            self._log.event(
                "draw", player=player.name, card=face, hand=len(self._state.hands[idx])
            )
            await self._notify_private(player, idx, f"Você comprou: {face}")
            self._state.advance()
            return

        assert isinstance(move, int)
        card = self._state.hands[idx][move]
        chosen = ""
        if card.is_wild:
            await self._broadcast(active_idx=idx, need_color_for=idx)
            chosen = await self._choose_color(player)
            self._log.event("color_chosen", player=player.name, color=chosen)
        played = self._state.play(idx, move, chosen)
        color = self._state.active_color
        suffix = f" → {color}" if played.is_wild else ""
        self._message = f"{player.name} jogou {_face(played)}{suffix}"
        self._log.event(
            "play",
            player=player.name,
            card=_face(played),
            active_color=color,
            wild=played.is_wild,
            hand=len(self._state.hands[idx]),
        )
        if self._state.winner() is not None:
            return
        self._apply_effect(played)

    def _apply_effect(self, card: Card) -> None:
        two_players = sum(p.active for p in self._players) == 2
        if card.value == "reverse":
            self._state.direction *= -1
            self._state.advance(skip=two_players)
            self._log.event(
                "effect", type="reverse", direction=self._state.direction
            )
        elif card.value == "skip":
            self._state.advance(skip=True)
            self._log.event("effect", type="skip")
        elif card.value in ("draw2", "wild4"):
            victim = self._state.next_index()
            count = 2 if card.value == "draw2" else 4
            self._state.draw(victim, count)
            self._state.advance(skip=True)
            self._log.event(
                "effect",
                type=card.value,
                victim=self._players[victim].name,
                drawn=count,
            )
        else:
            self._state.advance()

    async def _get_move(self, player: _Player, idx: int) -> int | str | None:
        hand = self._state.hands[idx]
        while True:
            try:
                raw = (await player.transport.read_line()).strip().lower()
            except ConnectionError:
                return None
            if raw in ("q", "quit", "sair"):
                return None
            if raw in ("d", "draw", "comprar"):
                return "draw"
            if raw.isdigit():
                pos = int(raw) - 1
                if 0 <= pos < len(hand) and self._state.playable(hand[pos]):
                    return pos

    async def _choose_color(self, player: _Player) -> str:
        while True:
            try:
                raw = (await player.transport.read_line()).strip().upper()
            except ConnectionError:
                return COLORS[0]
            if raw in COLORS:
                return raw

    # ── output ──────────────────────────────────────────────────────────────

    async def _safe_write(self, player: _Player, text: str) -> None:
        """Write to a player, dropping them if the transport is dead."""
        try:
            await player.transport.write(text)
        except (ConnectionError, OSError):
            player.active = False

    def _payload(self, idx: int, *, your_turn: bool, need_color: bool) -> str:
        st = self._state
        data = {
            "v": UNO_STATE_TAG,
            "phase": "play",
            "top": _face(st.top),
            "color": st.active_color,
            "direction": st.direction,
            "current": st.current,
            "you": idx,
            "players": [
                [p.name, len(st.hands[i])] for i, p in enumerate(self._players)
            ],
            "hand": [_face(c) for c in st.hands[idx]],
            "playable": [i for i, c in enumerate(st.hands[idx]) if st.playable(c)],
            "your_turn": your_turn,
            "need_color": need_color,
            "message": self._message,
            "winner": "",
        }
        return json.dumps(data) + "\n"

    async def _broadcast(
        self, *, active_idx: int, need_color_for: int | None = None
    ) -> None:
        async def send(i: int, p: _Player) -> None:
            if not p.active:
                return
            if p.stealth:
                await self._safe_write(
                    p,
                    render_log_view(
                        self._state, self._names, i,
                        is_active=(i == active_idx and need_color_for is None),
                        message=self._message,
                    ),
                )
            else:
                need = need_color_for == i
                turn = i == active_idx and need_color_for is None
                await self._safe_write(
                    p, self._payload(i, your_turn=turn, need_color=need)
                )

        await asyncio.gather(*(send(i, p) for i, p in enumerate(self._players)))
        self._message = ""

    async def _notify_private(self, player: _Player, idx: int, text: str) -> None:
        if player.stealth or not player.active:
            return  # private draw already implied by next table broadcast
        data = {"v": UNO_STATE_TAG, "phase": "toast", "you": idx, "message": text}
        await self._safe_write(player, json.dumps(data) + "\n")

    async def _broadcast_over(self) -> None:
        win = self._state.winner()
        name = self._players[win].name if win is not None else ""
        self._log.event("match_end", winner=name or None)

        async def send(i: int, p: _Player) -> None:
            if not p.active:
                return
            if p.stealth:
                await self._safe_write(
                    p,
                    render_log_view(
                        self._state, self._names, i, is_active=False,
                        message=f"round.result winner={name or '-'}",
                    ),
                )
            else:
                data = {"v": UNO_STATE_TAG, "phase": "over", "you": i, "winner": name}
                await self._safe_write(p, json.dumps(data) + "\n")

        await asyncio.gather(*(send(i, p) for i, p in enumerate(self._players)))
