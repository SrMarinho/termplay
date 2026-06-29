"""UnoController — turn-based multiplayer Uno with structured state output.

The server stays authoritative for game state. Each turn it pushes a per-player
JSON snapshot (hand, pile, opponents, whose turn, whether a color is needed) which
the visual ``UnoGameScreen`` renders with Textual widgets. Disguise-mode players
instead receive server-log lines. Client input (card number / ``d`` / color letter)
arrives through the normal game-input channel.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import random
import time
from collections.abc import Sequence
from dataclasses import dataclass

from termplay.engine.game_log import GameLogger
from termplay.engine.interfaces import ITransportAdapter
from termplay.games.uno.display import render_log_view
from termplay.games.uno.ruleset import UnoRuleset
from termplay.games.uno.state import COLORS, Card, UnoState

UNO_STATE_TAG = "uno.state"
TURN_TIMEOUT = 30  # seconds per turn
MINIGAME_TIMEOUT = 15  # seconds for the tap-the-dot round


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
        ruleset: UnoRuleset | None = None,
    ) -> None:
        _names = names or [f"Player {i + 1}" for i in range(len(transports))]
        _stealth = stealth_flags or [False] * len(transports)
        players = [
            _Player(t, n, s)
            for t, n, s in zip(transports, _names, _stealth, strict=False)
        ]
        random.shuffle(players)
        self._players = players
        self.rules = ruleset or UnoRuleset.standard()
        self._state = UnoState.new(len(self._players))
        self._message = ""
        self._turn_deadline: float = 0.0
        self._log = GameLogger("uno")
        self._log.event(
            "match_start",
            players=self._names,
            top=_face(self._state.top),
            active_color=self._state.active_color,
            hand_size=len(self._state.hands[0]),
        )
        if self.rules.initial_card_effect:
            self._apply_initial_card()

    def _apply_initial_card(self) -> None:
        """Apply the action of the very first discard card (standard rules)."""
        card = self._state.top
        if card.value == "skip":
            self._state.advance()
        elif card.value == "reverse":
            self._state.direction = -1
            self._state.advance()  # play starts from the last player
        elif card.value == "draw2":
            self._state.draw(self._state.current, 2)
            self._state.advance()

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
            # Stacking: if draws are pending and this player cannot stack a
            # matching card, force them to take the whole pile and move on.
            if self._state.pending_draws > 0 and not self._can_stack(idx):
                await self._take_pending(player, idx)
                continue
            self._turn_deadline = time.time() + TURN_TIMEOUT
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
            mtype, value = move
            if mtype == "play":
                assert value is not None
                await self._apply_move(player, idx, value)
            elif self._state.pending_draws > 0:
                await self._take_pending(player, idx)
            else:
                await self._handle_draw(player, idx)
        await self._broadcast_over()

    def _can_stack(self, idx: int) -> bool:
        """Whether the player holds a card that can stack on the pending draw."""
        target = self._state.pending_draw_value
        return any(c.value == target for c in self._state.hands[idx])

    async def _take_pending(self, player: _Player, idx: int) -> None:
        """Player absorbs the accumulated stacked draw count, then turn passes."""
        count = self._state.pending_draws
        self._state.draw(idx, count)
        self._state.pending_draws = 0
        self._state.pending_draw_value = ""
        self._message = f"{player.name} comprou {count} cartas"
        self._log.event("take_pending", player=player.name, count=count)
        await self._notify_private(player, idx, f"Você comprou {count} cartas")
        self._state.advance()

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

    async def _handle_draw(self, player: _Player, idx: int) -> None:
        """Resolve a draw action according to the active ruleset."""
        if self.rules.draw_until_play:
            while True:
                drawn = self._state.draw(idx, 1)
                if not drawn:
                    break  # deck exhausted
                if self._state.playable(drawn[0]):
                    self._log.event(
                        "draw_until", player=player.name, card=_face(drawn[0])
                    )
                    await self._apply_move(
                        player, idx, len(self._state.hands[idx]) - 1
                    )
                    return
            self._message = f"{player.name} não conseguiu jogar"
            self._state.advance()
            return

        drawn = self._state.draw(idx, 1)
        face = _face(drawn[0]) if drawn else "—"
        self._log.event(
            "draw", player=player.name, card=face, hand=len(self._state.hands[idx])
        )

        if self.rules.draw_then_play and drawn and self._state.playable(drawn[0]):
            drawn_idx = len(self._state.hands[idx]) - 1
            self._message = f"{player.name} comprou — pode jogar"
            self._turn_deadline = time.time() + TURN_TIMEOUT
            await self._broadcast(active_idx=idx, may_play_drawn=drawn_idx)
            await self._notify_private(player, idx, f"Você comprou: {face}")
            decision = await self._get_drawn_decision(player, idx, drawn_idx)
            if decision == "play":
                await self._apply_move(player, idx, drawn_idx)
            else:
                self._message = f"{player.name} passou"
                self._log.event("pass_drawn", player=player.name)
                self._state.advance()
            return

        self._message = f"{player.name} comprou uma carta"
        await self._notify_private(player, idx, f"Você comprou: {face}")
        self._state.advance()

    async def _apply_move(self, player: _Player, idx: int, move: int) -> None:
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
        # Brazilian extras: 0 swaps hands, 1 fires the tap-the-dot minigame.
        if self.rules.zero_swap and played.value == "0":
            await self._do_zero_swap(player, idx)
        # Multi-card play: collect all same-number cards before resolving effects.
        if (self.rules.multi_same_number
                and played.value.isdigit()
                and not played.is_wild
                and self._state.winner() is None):
            await self._do_multi_play(player, idx, played)
            return
        if self.rules.one_minigame and played.value == "1":
            await self._do_one_minigame(idx)
        self._apply_effect(played)

    async def _do_zero_swap(self, player: _Player, idx: int) -> None:
        """Playing a 0: the player picks another active player and swaps full hands."""
        targets = [
            i for i, p in enumerate(self._players) if p.active and i != idx
        ]
        if not targets:
            return
        if len(targets) == 1:
            target: int | None = targets[0]
        else:
            self._turn_deadline = time.time() + TURN_TIMEOUT
            await self._broadcast(active_idx=idx, need_target_for=idx, targets=targets)
            target = await self._choose_target(player, targets)
        if target is None:
            self._message = f"{player.name} optou por não trocar de mão"
            self._log.event("zero_swap_skip", player=player.name)
            return
        self._state.hands[idx], self._state.hands[target] = (
            self._state.hands[target],
            self._state.hands[idx],
        )
        self._message = (
            f"{player.name} trocou de mão com {self._players[target].name}"
        )
        self._log.event(
            "zero_swap", player=player.name, target=self._players[target].name
        )

    async def _do_multi_play(
        self, player: _Player, idx: int, first_card: Card
    ) -> None:
        """Let the player chain multiple cards of the same number value."""

        multi_played: list[str] = [_face(first_card)]
        last_card = first_card
        ones_count = 1 if (self.rules.one_minigame and first_card.value == "1") else 0

        while True:
            same_idxs = [
                i for i, c in enumerate(self._state.hands[idx])
                if c.value == first_card.value
            ]
            if not same_idxs:
                break
            n = len(multi_played)
            self._message = f"{player.name} jogou {n}× — jogue mais ou passe"
            self._turn_deadline = time.time() + TURN_TIMEOUT
            await self._broadcast(
                active_idx=idx,
                multi_played=multi_played,
                multi_value=first_card.value,
            )
            pos = await self._get_multi_move(player, idx, same_idxs)
            if pos is None:
                break
            next_card = self._state.play(idx, pos, "")
            last_card = next_card
            multi_played.append(_face(next_card))
            if self.rules.one_minigame and next_card.value == "1":
                ones_count += 1
            if self._state.winner() is not None:
                for _ in range(ones_count):
                    await self._do_one_minigame(idx)
                return

        if len(multi_played) > 1:
            self._message = (
                f"{player.name} jogou {len(multi_played)} cartas de uma vez!"
            )
            self._log.event(
                "multi_play",
                player=player.name,
                cards=multi_played,
                count=len(multi_played),
            )

        for _ in range(ones_count):
            await self._do_one_minigame(idx)

        self._apply_effect(last_card)

    async def _get_multi_move(
        self, player: _Player, idx: int, valid_idxs: list[int]
    ) -> int | None:
        """During multi-play: return a valid card index, or None to stop the chain."""
        hand = self._state.hands[idx]
        while True:
            remaining = self._turn_deadline - time.time()
            if remaining <= 0:
                return None
            try:
                raw = (
                    await asyncio.wait_for(
                        player.transport.read_line(), timeout=remaining
                    )
                ).strip().lower()
            except (TimeoutError, ConnectionError):
                return None
            if raw in ("p", "pass", "passar", "q", "quit", "sair"):
                return None
            if raw.isdigit():
                pos = int(raw) - 1
                if pos in valid_idxs:
                    return pos

    async def _choose_target(self, player: _Player, targets: list[int]) -> int | None:
        """Read a target player number (1-based global) from the player. Returns None to skip."""
        while True:
            remaining = self._turn_deadline - time.time()
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
            digits = raw.lstrip("t@p")  # tolerate "t2" / "@2" / "p2" / "2"
            if digits.isdigit():
                pick = int(digits) - 1
                if pick in targets:
                    return pick

    # ── minigame (Brazilian "1" card) ──────────────────────────────────────────

    @staticmethod
    def _random_dot() -> dict[str, float]:
        return {
            "x": round(random.uniform(0.1, 0.9), 3),
            "y": round(random.uniform(0.15, 0.85), 3),
        }

    async def _do_one_minigame(self, idx: int) -> None:
        """Tap-the-dot: every active player must click the moving dot once. The
        single player who never manages to tap draws a card. The card's player
        (idx) is subject to it too."""
        participants = [i for i, p in enumerate(self._players) if p.active]
        if len(participants) < 2:
            return
        safe: set[int] = set()
        deadline = time.time() + MINIGAME_TIMEOUT
        dot = self._random_dot()
        self._log.event("minigame_start", players=len(participants))
        await self._broadcast_minigame(participants, safe, dot, deadline)

        pending: dict[asyncio.Task[str], int] = {
            asyncio.create_task(self._players[i].transport.read_line()): i
            for i in participants
        }
        try:
            while len(safe) < len(participants) - 1:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                done, _ = await asyncio.wait(
                    pending.keys(),
                    timeout=remaining,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if not done:
                    break  # timed out
                changed = False
                for task in done:
                    i = pending.pop(task)
                    with contextlib.suppress(Exception):
                        task.result()  # any input counts as a tap
                    if i not in safe:
                        safe.add(i)
                        changed = True
                if changed:
                    dot = self._random_dot()
                    await self._broadcast_minigame(participants, safe, dot, deadline)
        finally:
            for task in pending:
                task.cancel()
            for task in pending:
                with contextlib.suppress(Exception, asyncio.CancelledError):
                    await task

        losers = [i for i in participants if i not in safe]
        for i in losers:
            self._state.draw(i, 1)
            self._log.event("minigame_loser", player=self._players[i].name)
        if losers:
            names = ", ".join(self._players[i].name for i in losers)
            self._message = f"⚡ {names} foi o mais lento — comprou!"

    async def _broadcast_minigame(
        self,
        participants: list[int],
        safe: set[int],
        dot: dict[str, float],
        deadline: float,
    ) -> None:
        async def send(i: int, p: _Player) -> None:
            if not p.active:
                return
            if p.stealth:
                await self._safe_write(
                    p,
                    render_log_view(
                        self._state, self._names, i,
                        is_active=(i not in safe),
                        message="minigame: clique no ponto!",
                    ),
                )
                return
            data = {
                "v": UNO_STATE_TAG,
                "phase": "minigame",
                "you": i,
                "players": [
                    [pp.name, len(self._state.hands[j])]
                    for j, pp in enumerate(self._players)
                ],
                "dot": dot,
                "safe": sorted(safe),
                "participants": participants,
                "you_safe": i in safe,
                "deadline": deadline,
                "message": "Clique no ponto antes de sobrar!",
            }
            await self._safe_write(p, json.dumps(data) + "\n")

        await asyncio.gather(*(send(i, p) for i, p in enumerate(self._players)))

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
            count = 2 if card.value == "draw2" else 4
            if self.rules.stack_draws:
                self._state.pending_draws += count
                self._state.pending_draw_value = card.value
                self._state.advance()  # next player may stack or take the pile
                self._log.event(
                    "effect",
                    type=card.value,
                    stacked=self._state.pending_draws,
                )
            else:
                victim = self._state.next_index()
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

    async def _get_move(
        self, player: _Player, idx: int
    ) -> tuple[str, int | None] | None:
        """Return ("play", pos), ("draw", None), or None to leave."""
        hand = self._state.hands[idx]
        stacking = self._state.pending_draws > 0
        while True:
            remaining = self._turn_deadline - time.time()
            if remaining <= 0:
                self._message = f"{player.name} demorou — comprou"
                return ("draw", None)
            try:
                raw = (
                    await asyncio.wait_for(player.transport.read_line(), timeout=remaining)
                ).strip().lower()
            except TimeoutError:
                self._message = f"{player.name} demorou — comprou"
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
                if not self._state.playable(card):
                    continue
                if stacking and card.value != self._state.pending_draw_value:
                    await self._notify_private(
                        player, idx,
                        f"Empilhe um {self._state.pending_draw_value} ou compre",
                    )
                    continue
                if (
                    self.rules.wild4_strict
                    and card.value == "wild4"
                    and any(
                        (not c.is_wild) and self._state.playable(c) for c in hand
                    )
                ):
                    await self._notify_private(
                        player, idx,
                        "Wild+4 só quando não há outra carta jogável",
                    )
                    continue
                return ("play", pos)

    async def _get_drawn_decision(
        self, player: _Player, idx: int, drawn_idx: int
    ) -> str:
        """After draw_then_play: return "play" to play the drawn card, else "pass"."""
        while True:
            remaining = self._turn_deadline - time.time()
            if remaining <= 0:
                return "pass"
            try:
                raw = (
                    await asyncio.wait_for(player.transport.read_line(), timeout=remaining)
                ).strip().lower()
            except TimeoutError:
                return "pass"
            except ConnectionError:
                return "pass"
            if raw in ("p", "pass", "passar", "d", "draw"):
                return "pass"
            if raw.isdigit() and int(raw) - 1 == drawn_idx:
                return "play"

    async def _choose_color(self, player: _Player) -> str:
        while True:
            remaining = self._turn_deadline - time.time()
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

    # ── output ──────────────────────────────────────────────────────────────

    async def _safe_write(self, player: _Player, text: str) -> None:
        """Write to a player, dropping them if the transport is dead."""
        try:
            await player.transport.write(text)
        except (ConnectionError, OSError):
            player.active = False

    def _payload(
        self,
        idx: int,
        *,
        your_turn: bool,
        need_color: bool,
        may_play_drawn: int | None = None,
        need_target: bool = False,
        targets: list[int] | None = None,
        multi_played: list[str] | None = None,
        multi_value: str = "",
    ) -> str:
        st = self._state
        in_multi = multi_played is not None and your_turn
        if in_multi:
            playable = [
                i for i, c in enumerate(st.hands[idx]) if c.value == multi_value
            ]
        elif may_play_drawn is not None:
            playable = [may_play_drawn]
        else:
            playable = [i for i, c in enumerate(st.hands[idx]) if st.playable(c)]
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
            "playable": playable,
            "your_turn": your_turn,
            "need_color": need_color,
            "need_target": need_target,
            "targets": targets or [],
            "deadline": self._turn_deadline,
            "message": self._message,
            "pending_draws": st.pending_draws,
            "may_play_drawn": may_play_drawn is not None,
            "drawn_card_idx": may_play_drawn if may_play_drawn is not None else -1,
            "multi_played": multi_played or [],
            "multi_value": multi_value,
            "winner": "",
        }
        return json.dumps(data) + "\n"

    async def _broadcast(
        self,
        *,
        active_idx: int,
        need_color_for: int | None = None,
        may_play_drawn: int | None = None,
        need_target_for: int | None = None,
        targets: list[int] | None = None,
        multi_played: list[str] | None = None,
        multi_value: str = "",
    ) -> None:
        prompt = need_color_for is not None or need_target_for is not None

        async def send(i: int, p: _Player) -> None:
            if not p.active:
                return
            if p.stealth:
                await self._safe_write(
                    p,
                    render_log_view(
                        self._state, self._names, i,
                        is_active=(i == active_idx and not prompt),
                        message=self._message,
                    ),
                )
            else:
                need = need_color_for == i
                want_target = need_target_for == i
                turn = i == active_idx and not prompt
                drawn = may_play_drawn if i == active_idx else None
                await self._safe_write(
                    p,
                    self._payload(
                        i,
                        your_turn=turn,
                        need_color=need,
                        may_play_drawn=drawn,
                        need_target=want_target,
                        targets=targets if want_target else None,
                        multi_played=multi_played,
                        multi_value=multi_value,
                    ),
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
