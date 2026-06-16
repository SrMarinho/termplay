"""Testes das regras do jogo (BlackjackRules)."""

from __future__ import annotations

from py21ssh.domain.card import Card, Rank, Suit
from py21ssh.domain.deck import Deck
from py21ssh.domain.hand import Hand
from py21ssh.domain.interfaces import RoundResult
from py21ssh.domain.rules import BlackjackRules


def _c(rank: Rank, suit: Suit = Suit.HEARTS) -> Card:
    return Card(suit, rank)


class TestBlackjackRules:
    def setup_method(self) -> None:
        self.rules = BlackjackRules()

    def test_initial_deal_gives_two_cards_each(self) -> None:
        deck = Deck()
        deck.shuffle()
        player, dealer = self.rules.initial_deal(deck)
        assert len(player) == 2
        assert len(dealer) == 2
        assert deck.remaining == 48

    def test_player_hit_adds_card(self) -> None:
        deck = Deck()
        deck.shuffle()
        hand = Hand()
        self.rules.player_hit(hand, deck)
        assert len(hand) == 1

    def test_dealer_plays_until_17(self) -> None:
        """Dealer compra até 17 ou mais."""
        deck = Deck()
        deck.shuffle()
        hand = Hand()
        hand.add(_c(Rank.TEN))
        hand.add(_c(Rank.FIVE))
        assert hand.value == 15

        self.rules.dealer_play(hand, deck)
        assert hand.value >= 17

    def test_dealer_stand_on_17(self) -> None:
        """Dealer para em 17 — não compra mais."""
        deck = Deck()
        hand = Hand()
        hand.add(_c(Rank.TEN))
        hand.add(_c(Rank.SEVEN))
        before = hand.value
        self.rules.dealer_play(hand, deck)
        assert hand.value == before  # não mudou

    def test_resolve_player_bust(self) -> None:
        player = Hand.from_cards([_c(Rank.K), _c(Rank.Q), _c(Rank.THREE)])
        dealer = Hand.from_cards([_c(Rank.TEN), _c(Rank.SEVEN)])
        assert player.is_bust
        assert self.rules.resolve(player, dealer) is RoundResult.LOSE

    def test_resolve_dealer_bust(self) -> None:
        player = Hand.from_cards([_c(Rank.TEN), _c(Rank.SEVEN)])  # 17
        dealer = Hand.from_cards([_c(Rank.K), _c(Rank.Q), _c(Rank.FIVE)])  # 25 bust
        assert dealer.is_bust
        assert self.rules.resolve(player, dealer) is RoundResult.WIN

    def test_resolve_player_wins(self) -> None:
        player = Hand.from_cards([_c(Rank.TEN), _c(Rank.NINE)])  # 19
        dealer = Hand.from_cards([_c(Rank.TEN), _c(Rank.SEVEN)])  # 17
        assert self.rules.resolve(player, dealer) is RoundResult.WIN

    def test_resolve_dealer_wins(self) -> None:
        player = Hand.from_cards([_c(Rank.TEN), _c(Rank.SIX)])  # 16
        dealer = Hand.from_cards([_c(Rank.TEN), _c(Rank.NINE)])  # 19
        assert self.rules.resolve(player, dealer) is RoundResult.LOSE

    def test_resolve_push(self) -> None:
        player = Hand.from_cards([_c(Rank.TEN), _c(Rank.SEVEN)])  # 17
        dealer = Hand.from_cards([_c(Rank.NINE), _c(Rank.EIGHT)])  # 17
        assert self.rules.resolve(player, dealer) is RoundResult.PUSH

    def test_player_blackjack_wins(self) -> None:
        player = Hand.from_cards([_c(Rank.A), _c(Rank.K)])  # BJ
        dealer = Hand.from_cards([_c(Rank.TEN), _c(Rank.SEVEN)])  # 17
        assert player.is_blackjack
        assert self.rules.resolve(player, dealer) is RoundResult.BLACKJACK

    def test_dealer_blackjack_loses(self) -> None:
        player = Hand.from_cards([_c(Rank.TEN), _c(Rank.SEVEN)])  # 17
        dealer = Hand.from_cards([_c(Rank.A), _c(Rank.K)])  # BJ
        assert dealer.is_blackjack
        assert self.rules.resolve(player, dealer) is RoundResult.LOSE

    def test_both_blackjack_push(self) -> None:
        player = Hand.from_cards([_c(Rank.A), _c(Rank.K)])  # BJ
        dealer = Hand.from_cards([_c(Rank.A), _c(Rank.Q)])  # BJ
        assert player.is_blackjack
        assert dealer.is_blackjack
        assert self.rules.resolve(player, dealer) is RoundResult.PUSH
