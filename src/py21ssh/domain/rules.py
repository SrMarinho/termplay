"""BlackjackRules — implementação concreta das regras do Blackjack."""

from __future__ import annotations

from py21ssh.conf import DEALER_STAND_VALUE
from py21ssh.domain.deck import Deck
from py21ssh.domain.hand import Hand
from py21ssh.domain.interfaces import RoundResult


class BlackjackRules:
    """Regras do Blackjack americano padrão.

    - Dealer compra até 17 (stand em soft 17).
    - Blackjack natural paga 3:2.
    - Double down permitido nas 2 primeiras cartas.
    """

    def initial_deal(self, deck: Deck) -> tuple[Hand, Hand]:
        """Distribui 2 cartas para jogador e dealer alternadamente."""
        player = Hand()
        dealer = Hand()
        for _ in range(2):
            player.add(deck.draw())
            dealer.add(deck.draw())
        return player, dealer

    def player_hit(self, hand: Hand, deck: Deck) -> None:
        """Adiciona uma carta à mão do jogador."""
        hand.add(deck.draw())

    def dealer_play(self, hand: Hand, deck: Deck) -> None:
        """Jogada automática do dealer.

        Compra enquanto valor < 17 (incluindo soft 17).
        """
        while hand.value < DEALER_STAND_VALUE:
            hand.add(deck.draw())

    def resolve(self, player: Hand, dealer: Hand) -> RoundResult:
        """Determina o resultado da rodada."""
        if player.is_blackjack and dealer.is_blackjack:
            return RoundResult.PUSH
        if player.is_blackjack:
            return RoundResult.BLACKJACK
        if dealer.is_blackjack:
            return RoundResult.LOSE
        if player.is_bust:
            return RoundResult.LOSE
        if dealer.is_bust:
            return RoundResult.WIN
        if player.value > dealer.value:
            return RoundResult.WIN
        if player.value < dealer.value:
            return RoundResult.LOSE
        return RoundResult.PUSH
