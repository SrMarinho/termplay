"""GameController — orquestra o fluxo do jogo (caso de uso principal).

Depende apenas de interfaces (DIP): ITransportAdapter e IGameRules.
Nada de socket, nada de terminal real.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from termplay.games.blackjack.conf import MIN_BET, STARTING_BALANCE
from termplay.games.blackjack.domain.deck import Deck
from termplay.games.blackjack.domain.interfaces import PlayerAction, RoundResult

if TYPE_CHECKING:
    from termplay.engine.interfaces import ITransportAdapter
    from termplay.games.blackjack.display.interfaces import IDisplayRenderer
    from termplay.games.blackjack.domain.hand import Hand
    from termplay.games.blackjack.domain.interfaces import IGameRules

logger = logging.getLogger(__name__)


class GameController:
    """Caso de uso principal: orquestra uma sessão completa de Blackjack.

    Fluxo:
        welcome → loop de rodadas
        (bet → deal → player_turn → dealer → resolve) → goodbye
    """

    def __init__(
        self,
        transport: ITransportAdapter,
        rules: IGameRules,
        renderer: IDisplayRenderer,
    ) -> None:
        self._transport = transport
        self._rules = rules
        self._renderer = renderer
        self._balance = STARTING_BALANCE

    async def run(self) -> int:
        """Executa a sessão completa. Retorna o saldo final."""
        await self._transport.write(self._renderer.welcome())
        while self._balance > 0:
            await self._play_round()
            if not await self._ask_continue():
                break
        await self._transport.write(self._renderer.goodbye(self._balance))
        return self._balance

    async def _play_round(self) -> None:
        """Executa uma rodada completa."""
        # 1. Aposta
        bet = await self._get_bet()
        if bet is None:
            return  # quit during bet

        # 2. Deal
        deck = Deck()
        deck.shuffle()
        player_hand, dealer_hand = self._rules.initial_deal(deck)

        await self._render(player_hand, dealer_hand, bet)

        # 3. Verifica Blackjack natural
        if dealer_hand.cards[0].is_ace or dealer_hand.cards[0].is_face:
            self._rules.dealer_play(dealer_hand, deck)
            if dealer_hand.is_blackjack and not player_hand.is_blackjack:
                await self._render(player_hand, dealer_hand, bet, reveal_dealer=True)
                await self._transport.write(
                    self._renderer.result(RoundResult.LOSE, bet, self._balance)
                )
                self._balance -= bet
                return

        result: RoundResult | None = None

        # 4. Turno do jogador
        if not player_hand.is_blackjack:
            result = await self._player_turn(player_hand, dealer_hand, deck, bet)
        elif dealer_hand.is_blackjack:
            result = RoundResult.PUSH
        else:
            result = RoundResult.BLACKJACK

        # 5. Turno do dealer
        if result is None:
            self._rules.dealer_play(dealer_hand, deck)
            await self._render(player_hand, dealer_hand, bet, reveal_dealer=True)
            result = self._rules.resolve(player_hand, dealer_hand)

        # 6. Resolução
        self._apply_result(result, bet)
        await self._transport.write(self._renderer.result(result, bet, self._balance))
        await self._transport.write(self._renderer.history(self._balance))

    async def _player_turn(
        self,
        player_hand: Hand,
        dealer_hand: Hand,
        deck: Deck,
        bet: int,
    ) -> RoundResult | None:
        """Loop de ações do jogador. Retorna None se dealer deve jogar."""
        while True:
            action = await self._get_action(player_hand, bet)
            if action is PlayerAction.QUIT:
                return RoundResult.LOSE
            if action is PlayerAction.STAND:
                return None
            if action is PlayerAction.HIT:
                self._rules.player_hit(player_hand, deck)
                await self._render(player_hand, dealer_hand, bet)
                if player_hand.is_bust:
                    await self._transport.write(self._renderer.bust())
                    return RoundResult.LOSE
            elif action is PlayerAction.DOUBLE:
                self._rules.player_hit(player_hand, deck)
                await self._render(player_hand, dealer_hand, bet, doubled=True)
                if player_hand.is_bust:
                    return RoundResult.LOSE
                return None
        return None  # unreachable

    async def _get_bet(self) -> int | None:
        """Solicita e valida a aposta do jogador."""
        await self._transport.write(self._renderer.bet_prompt(self._balance))
        while True:
            raw = await self._transport.read_line()
            if raw.strip().lower() in ("q", "quit", "exit"):
                return None
            try:
                amount = int(raw.strip())
            except ValueError:
                await self._transport.write(
                    self._renderer.error("Valor inválido. Digite um número.")
                )
                continue
            if amount < MIN_BET:
                await self._transport.write(
                    self._renderer.error(f"Aposta mínima: {MIN_BET}")
                )
                continue
            if amount > self._balance:
                await self._transport.write(
                    self._renderer.error(
                        f"Saldo insuficiente. Você tem {self._balance}"
                    )
                )
                continue
            return amount

    async def _get_action(self, hand: Hand, bet: int) -> PlayerAction:
        """Solicita e valida a ação do jogador."""
        await self._transport.write(self._renderer.action_prompt(hand, bet))
        while True:
            raw = await self._transport.read_line()
            raw = raw.strip().lower()
            if raw in ("h", "hit", "1"):
                return PlayerAction.HIT
            if raw in ("s", "stand", "2"):
                return PlayerAction.STAND
            if raw in ("d", "double", "3") and hand.can_double:
                return PlayerAction.DOUBLE
            if raw in ("q", "quit", "exit"):
                return PlayerAction.QUIT
            await self._transport.write(
                self._renderer.error(
                    "Comando inválido. Use h (hit), s (stand), d (double), q (quit)."
                )
            )

    async def _ask_continue(self) -> bool:
        """Pergunta se quer jogar outra rodada."""
        if self._balance <= 0:
            return False
        await self._transport.write(self._renderer.prompt("Jogar novamente? (s/n): "))
        raw = await self._transport.read_line()
        return raw.strip().lower() in ("s", "sim", "y", "yes", "")

    def _apply_result(self, result: RoundResult, bet: int) -> None:
        """Atualiza o saldo conforme o resultado."""
        if result is RoundResult.WIN:
            self._balance += bet
        elif result is RoundResult.LOSE:
            self._balance -= bet
        elif result is RoundResult.BLACKJACK:
            self._balance += int(bet * 1.5)

    async def _render(
        self,
        player_hand: Hand,
        dealer_hand: Hand,
        bet: int,
        reveal_dealer: bool = False,
        doubled: bool = False,
    ) -> None:
        """Renderiza a mesa e envia para o transporte."""
        output = self._renderer.table(
            player_hand=player_hand,
            dealer_hand=dealer_hand,
            balance=self._balance,
            bet=bet,
            reveal_dealer=reveal_dealer,
            doubled=doubled,
        )
        await self._transport.write(output)
