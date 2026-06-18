"""MultiplayerGameController — Blackjack para múltiplos jogadores."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from termplay.games.blackjack.conf import BLACKJACK_PAYOUT, MIN_BET, STARTING_BALANCE
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
    renderer: RichRenderer
    name: str
    balance: int = STARTING_BALANCE
    hand: Hand = field(default_factory=lambda: Hand([]))
    bet: int = 0
    active: bool = True


class MultiplayerGameController:
    """Orquestra rodadas de Blackjack com múltiplos jogadores.

    Cada jogador tem transport/renderer próprios.
    Broadcasts vão para todos; prompts vão apenas ao jogador ativo.
    """

    def __init__(
        self,
        transports: Sequence[ITransportAdapter],
        rules: IGameRules,
        names: list[str] | None = None,
    ) -> None:
        self._rules = rules
        _names = names or [f"Player {i + 1}" for i in range(len(transports))]
        self._players = [
            _PlayerState(t, RichRenderer(t), n)
            for t, n in zip(transports, _names, strict=False)
        ]

    async def run(self) -> None:
        await self._broadcast(
            "\r\n╔══════════════════════════════╗\r\n"
            "║   BLACKJACK MULTIPLAYER 🃏   ║\r\n"
            "╚══════════════════════════════╝\r\n\r\n"
        )
        while self._active_players():
            await self._play_round()
            if not await self._ask_continue():
                break
        await self._broadcast("\r\nFim de jogo! Obrigado por jogar.\r\n")

    async def _play_round(self) -> None:
        deck = Deck()
        deck.shuffle()

        active = self._active_players()

        # Bets
        for player in active:
            await player.transport.write(player.renderer.bet_prompt(player.balance))
            bet = await self._get_bet(player)
            if bet is None:
                player.active = False
                continue
            player.bet = bet

        active = self._active_players()
        if not active:
            return

        # Deal: each player + dealer get 2 cards
        dealer_hand = Hand([deck.draw(), deck.draw()])
        for player in active:
            player.hand = Hand([deck.draw(), deck.draw()])

        # Show initial table to all players
        await self._broadcast_all_tables(active[0], active, dealer_hand)

        # Player turns
        for player in active:
            await self._broadcast_all_tables(player, active, dealer_hand)
            await self._play_player_turn(player, dealer_hand, deck, active)

        # Dealer plays (if any player still standing)
        if any(not p.hand.is_bust for p in active):
            self._rules.dealer_play(dealer_hand, deck)

        # Resolve results, apply balance changes, then broadcast final table
        player_results: list[tuple[_PlayerState, RoundResult]] = []
        for player in active:
            if player.hand.is_bust:
                res = RoundResult.LOSE
            elif player.hand.is_blackjack and not dealer_hand.is_blackjack:
                res = RoundResult.BLACKJACK
            else:
                res = self._rules.resolve(player.hand, dealer_hand)
            self._apply_result(player, res)
            player_results.append((player, res))

        await self._broadcast_all_tables(
            active[0], active, dealer_hand, reveal_dealer=True
        )
        for player, res in player_results:
            await player.transport.write(
                player.renderer.result(res, player.bet, player.balance)
            )

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
                    player.renderer.error("Valor inválido. Digite um número.")
                )
                continue
            if amount < MIN_BET:
                await player.transport.write(
                    player.renderer.error(f"Aposta mínima: {MIN_BET}")
                )
                continue
            if amount > player.balance:
                await player.transport.write(
                    player.renderer.error(f"Saldo insuficiente: {player.balance}")
                )
                continue
            return amount

    async def _play_player_turn(
        self,
        player: _PlayerState,
        dealer_hand: Hand,
        deck: Deck,
        all_active: list[_PlayerState],
    ) -> None:
        while not player.hand.is_bust and not player.hand.is_blackjack:
            await self._broadcast_all_tables(player, all_active, dealer_hand)
            action = await self._get_action(player)
            if action is PlayerAction.QUIT:
                player.active = False
                return
            if action is PlayerAction.STAND:
                await self._broadcast_all_tables(player, all_active, dealer_hand)
                break
            if action is PlayerAction.HIT:
                self._rules.player_hit(player.hand, deck)
                if player.hand.is_bust:
                    await self._broadcast_all_tables(player, all_active, dealer_hand)
                    await player.transport.write(player.renderer.bust())
                    break
            elif action is PlayerAction.DOUBLE:
                if player.hand.can_double and player.balance >= player.bet:
                    player.bet *= 2
                    self._rules.player_hit(player.hand, deck)
                    await self._broadcast_all_tables(player, all_active, dealer_hand)
                    if player.hand.is_bust:
                        await player.transport.write(player.renderer.bust())
                    break

    async def _get_action(self, player: _PlayerState) -> PlayerAction:
        await player.transport.write(
            player.renderer.action_prompt(player.hand, player.bet)
        )
        mapping = {
            "h": PlayerAction.HIT,
            "hit": PlayerAction.HIT,
            "1": PlayerAction.HIT,
            "s": PlayerAction.STAND,
            "stand": PlayerAction.STAND,
            "2": PlayerAction.STAND,
            "d": PlayerAction.DOUBLE,
            "double": PlayerAction.DOUBLE,
            "3": PlayerAction.DOUBLE,
            "q": PlayerAction.QUIT,
            "quit": PlayerAction.QUIT,
        }
        while True:
            try:
                raw = (await player.transport.read_line()).strip().lower()
            except ConnectionError:
                return PlayerAction.QUIT
            if raw in mapping:
                return mapping[raw]
            await player.transport.write(
                player.renderer.error("Use: h=hit  s=stand  d=double  q=sair")
            )

    def _apply_result(self, player: _PlayerState, result: RoundResult) -> None:
        if result is RoundResult.WIN:
            player.balance += player.bet
        elif result is RoundResult.LOSE:
            player.balance -= player.bet
        elif result is RoundResult.BLACKJACK:
            player.balance += int(player.bet * BLACKJACK_PAYOUT)

    async def _ask_continue(self) -> bool:
        active = self._active_players()
        if not active:
            return False

        results: list[bool] = []

        async def ask_one(player: _PlayerState) -> None:
            await player.transport.write(player.renderer.prompt("Continuar? (s/n): "))
            try:
                raw = (await player.transport.read_line()).strip().lower()
                results.append(raw in ("s", "sim", "y", "yes", ""))
            except ConnectionError:
                results.append(False)

        await asyncio.gather(*(ask_one(p) for p in active))
        return any(results)

    async def _broadcast_all_tables(
        self,
        active_player: _PlayerState,
        all_active: list[_PlayerState],
        dealer_hand: Hand,
        reveal_dealer: bool = False,
    ) -> None:
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
                    active_name=active_player.name,
                    reveal_dealer=reveal_dealer,
                )
            )

        await asyncio.gather(*(send_to(p) for p in all_active))

    async def _broadcast(self, text: str) -> None:
        await asyncio.gather(*(p.transport.write(text) for p in self._players))

    def _active_players(self) -> list[_PlayerState]:
        return [p for p in self._players if p.active]
