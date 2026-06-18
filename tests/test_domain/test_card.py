"""Testes da camada Card."""

from __future__ import annotations

import pytest

from termplay.games.blackjack.domain.card import Card, Rank, Suit, all_cards


class TestCard:
    def test_cria_carta(self) -> None:
        card = Card(Suit.HEARTS, Rank.A)
        assert card.suit == Suit.HEARTS
        assert card.rank == Rank.A

    def test_ace_value(self) -> None:
        card = Card(Suit.SPADES, Rank.A)
        assert card.value == 11
        assert card.is_ace
        assert not card.is_face

    def test_face_value(self) -> None:
        for rank in (Rank.J, Rank.Q, Rank.K):
            card = Card(Suit.CLUBS, rank)
            assert card.value == 10
            assert card.is_face
            assert not card.is_ace

    def test_numeric_value(self) -> None:
        pairs = [(Rank.TWO, 2), (Rank.FIVE, 5), (Rank.NINE, 9), (Rank.TEN, 10)]
        for rank, expected in pairs:
            card = Card(Suit.DIAMONDS, rank)
            assert card.value == expected
            assert not card.is_ace
            assert not card.is_face

    def test_display_format(self) -> None:
        assert Card(Suit.HEARTS, Rank.A).display == "A♥"
        assert Card(Suit.SPADES, Rank.K).display == "K♠"
        assert Card(Suit.DIAMONDS, Rank.TEN).display == "10♦"

    def test_card_immutability(self) -> None:
        card = Card(Suit.HEARTS, Rank.A)
        with pytest.raises(AttributeError):
            # sourcery skip: no-conditionals-in-tests
            card.suit = Suit.SPADES  # type: ignore[misc]

    def test_card_equality(self) -> None:
        a = Card(Suit.HEARTS, Rank.A)
        b = Card(Suit.HEARTS, Rank.A)
        c = Card(Suit.HEARTS, Rank.K)
        assert a == b
        assert a != c

    def test_all_cards_has_52(self) -> None:
        cards = all_cards()
        assert len(cards) == 52

    def test_all_cards_unique(self) -> None:
        cards = all_cards()
        assert len(set(cards)) == 52

    def test_all_suits_present(self) -> None:
        cards = all_cards()
        suits = {c.suit for c in cards}
        assert suits == set(Suit)

    def test_all_ranks_present(self) -> None:
        cards = all_cards()
        ranks = {c.rank for c in cards}
        assert ranks == set(Rank)
