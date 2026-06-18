"""MultiplayerGameController — concurrent Blackjack for multiple players."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from termplay.games.blackjack.conf import BLACKJACK_PAYOUT, MIN_BET, STARTING_BALANCE
from termplay.games.blackjack.display.log_renderer import LogRenderer
from termplay.games.blackjack.display.renderer import RichRenderer
from termplay.games.blackjack.domain.deck import Deck
from termplay.games.blackjack.domain.hand import Hand
from termplay.games.blackjack.domain.interfaces import (
    IGameRules,
    PlayerAction,
    RoundResult,
)

if TYPE_CHECKING:
    from termplay.engine.interfaces import ITransportAdapter


@dataclass
class _PlayerState:
    transport: ITransportAdapter
    renderer: RichRenderer | LogRenderer
    name: str
    balance: int = STARTING_BALANCE
    hand: Hand = field(default_factory=lambda: Hand([]))
    bet: int = 0
    active: bool = True


class MultiplayerGameController:
    """Concurrent Blackjack — all players bet and play simultaneously.

    Each player gets their own transport/renderer. Table broadcasts go to all
    players after every action so everyone always sees the current state.
    """

    def __init__(
        self,
        transports: Sequence[ITransportAdapter],
        rules: IGameRules,
        names: list[str] | None = None,
        stealth_flags: list[bool] | None = None,
    ) -> None:
        self._rules = rules
        _names = names or [f"Player {i + 1}" for i in range(len(transports))]
        _stealth = stealth_flags or [False] * len(transports)
        self._players = [
            _PlayerState(t, LogRenderer(t) if s else RichRenderer(t), n)
            for t, n, s in zip(transports, _names, _stealth, strict=False)
        ]

    async def run(self) -> None:
        await asyncio.gather(*(
            p.transport.write(p.renderer.banner()) for p in self._players
        ))
        while self._active_players():
            await self._play_round()
            if not await self._ask_continue():
                break
        await asyncio.gather(*(
            p.transport.write(p.renderer.farewell()) for p in self._players
        ))

    async def _play_round(self) -> None:
        deck = Deck()
        deck.shuffle()
        active = self._active_players()

        # Send personalised bet prompts and collect bets simultaneously
        await asyncio.gather(*(
            p.transport.write(p.renderer.bet_prompt(p.balance)) for p in active
        ))
        bets = await asyncio.gather(*(self._get_bet(p) for p in active))
        for player, bet in zip(active, bets, strict=False):
            if bet is None:
                player.active = False
            else:
                player.bet = bet

        active = self._active_players()
        if not active:
            return

        # Deal
        dealer_hand = Hand([deck.draw(), deck.draw()])
        for player in active:
            player.hand = Hand([deck.draw(), deck.draw()])

        # Show initial table to all
        await self._broadcast_tables(active, dealer_hand)

        # All players take turns concurrently
        await asyncio.gather(*(
            self._play_turn(player, dealer_hand, deck, active)
            for player in active
        ))

        # Dealer draws
        if any(not p.hand.is_bust for p in active):
            self._rules.dealer_play(dealer_hand, deck)

        # Resolve and show results
        results: list[tuple[_PlayerState, RoundResult]] = []
        for player in active:
            if player.hand.is_bust:
                res = RoundResult.LOSE
            elif player.hand.is_blackjack and not dealer_hand.is_blackjack:
                res = RoundResult.BLACKJACK
            else:
                res = self._rules.resolve(player.hand, dealer_hand)
            self._apply_result(player, res)
            results.append((player, res))

        await self._broadcast_tables(active, dealer_hand, reveal_dealer=True)
        await asyncio.gather(*(
            p.transport.write(p.renderer.result(res, p.bet, p.balance))
            for p, res in results
        ))

    # ── Player turn (runs concurrently per player) ───────────────────────────

    async def _play_turn(
        self,
        player: _PlayerState,
        dealer_hand: Hand,
        deck: Deck,
        all_active: list[_PlayerState],
    ) -> None:
        while not player.hand.is_bust and not player.hand.is_blackjack:
            # Always show fresh table then action prompt (no panel → no clear)
            await self._broadcast_tables(all_active, dealer_hand, acting=player.name)
            await player.transport.write(
                player.renderer.action_prompt(player.hand, player.bet)
            )

            action = await self._get_action(player)

            if action is PlayerAction.QUIT:
                player.active = False
                return
            if action is PlayerAction.STAND:
                await self._broadcast_tables(
                    all_active, dealer_hand, acting=player.name
                )
                break
            if action is PlayerAction.HIT:
                self._rules.player_hit(player.hand, deck)
                await self._broadcast_tables(
                    all_active, dealer_hand, acting=player.name
                )
                if player.hand.is_bust:
                    await player.transport.write(player.renderer.bust())
                    break
            elif action is PlayerAction.DOUBLE:
                if player.hand.can_double and player.balance >= player.bet:
                    player.bet *= 2
                    self._rules.player_hit(player.hand, deck)
                    await self._broadcast_tables(
                        all_active, dealer_hand, acting=player.name
                    )
                    if player.hand.is_bust:
                        await player.transport.write(player.renderer.bust())
                    break

    # ── Input helpers ────────────────────────────────────────────────────────

    async def _get_bet(self, player: _PlayerState) -> int | None:
        while True:
            try:
                raw = (await player.transport.read_line()).strip().lower()
            except ConnectionError:
                return None
            if raw in ("q", "quit", "exit"):
                return None
            try:
                amount = int(raw)
            except ValueError:
                await player.transport.write(
                    player.renderer.error("Invalid value. Enter a number.")
                )
                continue
            if amount < MIN_BET:
                await player.transport.write(
                    player.renderer.error(f"Minimum bet: {MIN_BET}")
                )
                continue
            if amount > player.balance:
                await player.transport.write(
                    player.renderer.error(f"Insufficient balance: {player.balance}")
                )
                continue
            return amount

    async def _get_action(self, player: _PlayerState) -> PlayerAction:
        mapping = {
            "h": PlayerAction.HIT, "hit": PlayerAction.HIT, "1": PlayerAction.HIT,
            "s": PlayerAction.STAND, "stand": PlayerAction.STAND,
            "2": PlayerAction.STAND,
            "d": PlayerAction.DOUBLE, "double": PlayerAction.DOUBLE,
            "3": PlayerAction.DOUBLE,
            "q": PlayerAction.QUIT, "quit": PlayerAction.QUIT,
        }
        while True:
            try:
                raw = (await player.transport.read_line()).strip().lower()
            except ConnectionError:
                return PlayerAction.QUIT
            if raw in mapping:
                return mapping[raw]
            await player.transport.write(
                player.renderer.error("Use: h=hit  s=stand  d=double  q=quit")
            )

    # ── Broadcast helpers ────────────────────────────────────────────────────

    async def _broadcast_tables(
        self,
        all_active: list[_PlayerState],
        dealer_hand: Hand,
        *,
        acting: str = "",
        reveal_dealer: bool = False,
    ) -> None:
        """Send each player a table view with their own perspective."""
        async def send_to(viewer: _PlayerState) -> None:
            others = [(p.name, p.hand) for p in all_active if p is not viewer]
            await viewer.transport.write(
                viewer.renderer.multiplayer_table(
                    my_name=viewer.name,
                    my_hand=viewer.hand,
                    dealer_hand=dealer_hand,
                    balance=viewer.balance,
                    bet=viewer.bet,
                    others=others,
                    active_name=acting,
                    reveal_dealer=reveal_dealer,
                )
            )

        await asyncio.gather(*(send_to(p) for p in all_active))

    async def _broadcast(self, text: str) -> None:
        await asyncio.gather(*(p.transport.write(text) for p in self._players))

    # ── Continue / utils ─────────────────────────────────────────────────────

    async def _ask_continue(self) -> bool:
        active = self._active_players()
        if not active:
            return False

        results: list[bool] = []

        async def ask_one(player: _PlayerState) -> None:
            await player.transport.write(player.renderer.prompt("Continue? (s/n): "))
            try:
                raw = (await player.transport.read_line()).strip().lower()
                results.append(raw in ("s", "sim", "y", "yes", ""))
            except ConnectionError:
                results.append(False)

        await asyncio.gather(*(ask_one(p) for p in active))
        return any(results)

    def _apply_result(self, player: _PlayerState, result: RoundResult) -> None:
        if result is RoundResult.WIN:
            player.balance += player.bet
        elif result is RoundResult.LOSE:
            player.balance -= player.bet
        elif result is RoundResult.BLACKJACK:
            player.balance += int(player.bet * BLACKJACK_PAYOUT)

    def _active_players(self) -> list[_PlayerState]:
        return [p for p in self._players if p.active]
