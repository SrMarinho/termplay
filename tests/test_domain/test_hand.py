"""Testes da camada Hand."""

from __future__ import annotations

from termplay.games.blackjack.domain.card import Card, Rank, Suit
from termplay.games.blackjack.domain.hand import Hand


def _make(rank: Rank, suit: Suit = Suit.HEARTS) -> Card:
    return Card(suit, rank)


class TestHand:
    def test_empty_hand_value_zero(self) -> None:
        assert Hand().value == 0

    def test_simple_value(self) -> None:
        hand = Hand.from_cards([_make(Rank.SEVEN), _make(Rank.FIVE)])
        assert hand.value == 12

    def test_face_card_value(self) -> None:
        hand = Hand.from_cards([_make(Rank.K), _make(Rank.Q)])
        assert hand.value == 20

    def test_ace_counts_as_11(self) -> None:
        hand = Hand.from_cards([_make(Rank.A), _make(Rank.SEVEN)])
        assert hand.value == 18

    def test_ace_adjusts_to_1_when_bust(self) -> None:
        hand = Hand.from_cards([_make(Rank.A), _make(Rank.K), _make(Rank.FIVE)])
        # A=11 → 11+10+5=26 (bust) → A=1 → 1+10+5=16
        assert hand.value == 16

    def test_multiple_aces(self) -> None:
        hand = Hand.from_cards([_make(Rank.A), _make(Rank.A), _make(Rank.NINE)])
        # 11+11+9=31 → 1+11+9=21 → 1+1+9=11
        assert hand.value == 21

    def test_three_aces(self) -> None:
        hand = Hand.from_cards([_make(Rank.A), _make(Rank.A), _make(Rank.A)])
        # 11+11+11=33 → 1+11+11=23 → 1+1+11=13
        assert hand.value == 13

    def test_is_bust(self) -> None:
        hand = Hand.from_cards([_make(Rank.K), _make(Rank.Q), _make(Rank.FIVE)])
        assert hand.is_bust

    def test_not_bust(self) -> None:
        hand = Hand.from_cards([_make(Rank.TEN), _make(Rank.SEVEN)])
        assert not hand.is_bust

    def test_blackjack(self) -> None:
        hand = Hand.from_cards([_make(Rank.A), _make(Rank.K)])
        assert hand.is_blackjack
        assert hand.value == 21

    def test_three_card_21_is_not_blackjack(self) -> None:
        cards = [_make(Rank.SEVEN), _make(Rank.SEVEN), _make(Rank.SEVEN)]
        hand = Hand.from_cards(cards)
        assert hand.value == 21
        assert not hand.is_blackjack

    def test_is_pair(self) -> None:
        hand = Hand.from_cards([_make(Rank.EIGHT), _make(Rank.EIGHT)])
        assert hand.is_pair

    def test_ace_and_king_not_pair(self) -> None:
        hand = Hand.from_cards([_make(Rank.A), _make(Rank.K)])
        assert not hand.is_pair  # same value (11 and 10) but different rank value

    def test_can_double(self) -> None:
        hand = Hand.from_cards([_make(Rank.SEVEN), _make(Rank.FOUR)])
        assert hand.can_double

    def test_cannot_double_after_hit(self) -> None:
        hand = Hand.from_cards([_make(Rank.SEVEN), _make(Rank.FOUR), _make(Rank.THREE)])
        assert not hand.can_double

    def test_cannot_double_blackjack(self) -> None:
        hand = Hand.from_cards([_make(Rank.A), _make(Rank.K)])
        assert not hand.can_double

    def test_add_card(self) -> None:
        hand = Hand()
        hand.add(_make(Rank.A))
        assert len(hand) == 1
        assert hand.value == 11

    def test_from_cards_creates_copy(self) -> None:
        cards = [_make(Rank.A), _make(Rank.K)]
        hand = Hand.from_cards(cards)
        assert len(hand) == 2
        assert hand.is_blackjack
