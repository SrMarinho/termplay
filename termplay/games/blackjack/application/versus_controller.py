"""BlackjackVersusController — player-vs-player Blackjack (no house dealer).

Players face each other: every round each player is dealt two cards, then takes
their turn (hit/stand) sequentially. The highest non-bust hand wins the round and
scores a point; first to ``TARGET_SCORE`` points wins the match. Ties push (no
point). The controller mirrors ``UnoController``: it stays authoritative and
pushes a per-player ``blackjack.state`` JSON snapshot the web client renders.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

from termplay.engine.game_log import GameLogger
from termplay.engine.interfaces import ITransportAdapter
from termplay.games.blackjack.domain.card import all_cards
from termplay.games.blackjack.domain.deck import Deck
from termplay.games.blackjack.domain.hand import Hand
from termplay.games.blackjack.domain.ruleset import BlackjackRuleset

BJ_STATE_TAG = "blackjack.state"
TURN_TIMEOUT = 30  # seconds per turn
TARGET_SCORE = 3   # points needed to win the match
RESULT_PAUSE = 2.5  # seconds to show the round result before the next deal


@dataclass
class _BJPlayer:
    transport: ITransportAdapter
    name: str
    stealth: bool = False
    active: bool = True
    score: int = 0
    hand: Hand = field(default_factory=Hand)
    done: bool = False  # stood or busted this round


class BlackjackVersusController:
    """Coordinates a player-vs-player Blackjack match over player transports."""

    def __init__(
        self,
        transports: Sequence[ITransportAdapter],
        names: list[str] | None = None,
        stealth_flags: list[bool] | None = None,
        rules: object = None,
    ) -> None:
        _names = names or [f"Player {i + 1}" for i in range(len(transports))]
        _stealth = stealth_flags or [False] * len(transports)
        players = [
            _BJPlayer(t, n, s)
            for t, n, s in zip(transports, _names, _stealth, strict=False)
        ]
        random.shuffle(players)
        self._players = players
        self._rules = BlackjackRuleset.from_spec(rules)
        self._message = ""
        self._turn_deadline: float = 0.0
        self._start = 0  # index of the player who acts first this round
        self._winner_name = ""
        self._log = GameLogger("blackjack")
        self._log.event("match_start", players=self._names, target=TARGET_SCORE)

    @property
    def _names(self) -> list[str]:
        return [p.name for p in self._players]

    def _active(self) -> list[_BJPlayer]:
        return [p for p in self._players if p.active]

    async def run(self) -> None:
        while True:
            active = self._active()
            if len(active) < 2:
                if active:
                    self._winner_name = active[0].name
                break
            winner = await self._play_round()
            if winner is not None and winner.score >= TARGET_SCORE:
                self._winner_name = winner.name
                break
            self._start = (self._start + 1) % len(self._players)
            await asyncio.sleep(RESULT_PAUSE)
        await self._broadcast_over()

    # ── round ────────────────────────────────────────────────────────────────

    async def _play_round(self) -> _BJPlayer | None:
        deck = Deck(cards=[*all_cards(), *all_cards()])  # 2-deck shoe
        deck.shuffle()
        active = self._active()
        for p in active:
            p.hand = Hand([deck.draw(), deck.draw()])
            p.done = p.hand.is_blackjack  # natural 21 stands automatically
        self._message = "Nova rodada — boa sorte!"

        for player in self._turn_order():
            if not player.active:
                continue
            await self._take_turn(player, deck)
            if len(self._active()) < 2:
                return None  # someone left — abort and let run() end the match

        winner = self._resolve()
        await self._broadcast()  # reveal final hands + result message
        return winner

    def _turn_order(self) -> list[_BJPlayer]:
        n = len(self._players)
        return [self._players[(self._start + k) % n] for k in range(n)]

    async def _take_turn(self, player: _BJPlayer, deck: Deck) -> None:
        while not player.done and player.active:
            self._turn_deadline = time.time() + TURN_TIMEOUT
            await self._broadcast(active=player)
            self._log.event(
                "turn", player=player.name, value=player.hand.value,
                cards=str(player.hand),
            )
            action = await self._get_action(player)
            if action is None:
                player.active = False
                self._message = f"{player.name} saiu da partida"
                self._log.event("leave", player=player.name)
                return
            if action == "stand":
                player.done = True
                self._message = f"{player.name} parou em {player.hand.value}"
                self._log.event("stand", player=player.name, value=player.hand.value)
            elif action == "hit":
                card = deck.draw()
                player.hand.add(card)
                self._message = f"{player.name} comprou {card.display}"
                self._log.event(
                    "hit", player=player.name, card=card.display,
                    value=player.hand.value,
                )
                if player.hand.is_bust:
                    player.done = True
                    self._message = f"{player.name} estourou em {player.hand.value}!"

    def _resolve(self) -> _BJPlayer | None:
        active = self._active()
        busted = [p for p in active if p.hand.is_bust]
        contenders = [p for p in active if not p.hand.is_bust]

        if self._rules.bust_penalty:
            for p in busted:
                p.score -= 1
                self._log.event("bust_penalty", player=p.name, score=p.score)

        if not contenders:
            bust_note = " (−1 pt cada)" if self._rules.bust_penalty and busted else ""
            self._message = f"Todos estouraram — empate, sem ponto{bust_note}."
            self._log.event("round_push", reason="all_bust")
            return None

        best = max(p.hand.value for p in contenders)
        winners = [p for p in contenders if p.hand.value == best]
        if len(winners) == 1:
            w = winners[0]
            w.score += 1
            self._message = f"🏆 {w.name} venceu a rodada com {best}! ({w.score} pts)"
            self._log.event("round_win", player=w.name, value=best, score=w.score)
            return w
        names = ", ".join(p.name for p in winners)
        self._message = f"Empate em {best} entre {names} — sem ponto."
        self._log.event("round_push", value=best, tied=[p.name for p in winners])
        return None

    async def _get_action(self, player: _BJPlayer) -> str | None:
        """Return "hit", "stand", or None to leave."""
        while True:
            remaining = self._turn_deadline - time.time()
            if remaining <= 0:
                self._message = f"{player.name} demorou — parou"
                return "stand"
            try:
                raw = (
                    await asyncio.wait_for(player.transport.read_line(), timeout=remaining)
                ).strip().lower()
            except TimeoutError:
                self._message = f"{player.name} demorou — parou"
                return "stand"
            except ConnectionError:
                return None
            if raw in ("q", "quit", "sair"):
                return None
            if raw in ("h", "hit", "comprar", "1"):
                return "hit"
            if raw in ("s", "stand", "parar", "2"):
                return "stand"

    # ── output ─────────────────────────────────────────────────────────────────

    async def _safe_write(self, player: _BJPlayer, text: str) -> None:
        try:
            await player.transport.write(text)
        except (ConnectionError, OSError):
            player.active = False

    def _status(self, p: _BJPlayer) -> str:
        if not p.active:
            return "out"
        if p.hand.is_bust:
            return "bust"
        if p.hand.is_blackjack:
            return "blackjack"
        return "stand" if p.done else ""

    def _payload(self, idx: int, current: int, *, your_turn: bool, phase: str) -> str:
        players = [
            [
                p.name,
                [c.display for c in p.hand.cards],
                p.hand.value,
                p.score,
                self._status(p),
            ]
            for p in self._players
        ]
        me = self._players[idx]
        data = {
            "v": BJ_STATE_TAG,
            "phase": phase,
            "you": idx,
            "current": current,
            "your_turn": your_turn,
            "players": players,
            "hand": [c.display for c in me.hand.cards],
            "hand_value": me.hand.value,
            "deadline": self._turn_deadline,
            "message": self._message,
            "target_score": TARGET_SCORE,
            "winner": self._winner_name,
        }
        return json.dumps(data) + "\n"

    def _log_view(self, idx: int) -> str:
        lines = [f"== Blackjack (até {TARGET_SCORE} pts) =="]
        for p in self._players:
            tag = " (você)" if p is self._players[idx] else ""
            cards = str(p.hand) or "—"
            lines.append(
                f"{p.name}{tag}: {cards} = {p.hand.value} "
                f"[{self._status(p) or 'jogando'}] · {p.score} pts"
            )
        if self._message:
            lines.append(self._message)
        return "\r\n".join(lines) + "\r\n"

    async def _broadcast(self, *, active: _BJPlayer | None = None) -> None:
        current = self._players.index(active) if active is not None else -1

        async def send(i: int, p: _BJPlayer) -> None:
            if not p.active:
                return
            if p.stealth:
                await self._safe_write(p, self._log_view(i))
            else:
                await self._safe_write(
                    p, self._payload(i, current, your_turn=(p is active), phase="play")
                )

        await asyncio.gather(*(send(i, p) for i, p in enumerate(self._players)))
        self._message = ""

    async def _broadcast_over(self) -> None:
        self._log.event("match_end", winner=self._winner_name or None)
        self._message = (
            f"🏆 {self._winner_name} venceu a partida!"
            if self._winner_name
            else "Partida encerrada."
        )

        async def send(i: int, p: _BJPlayer) -> None:
            if not p.active:
                return
            if p.stealth:
                await self._safe_write(p, self._log_view(i))
            else:
                await self._safe_write(
                    p, self._payload(i, -1, your_turn=False, phase="over")
                )

        await asyncio.gather(*(send(i, p) for i, p in enumerate(self._players)))
