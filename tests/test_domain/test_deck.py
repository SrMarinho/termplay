"""Testes da camada Deck."""

from __future__ import annotations

import pytest

from termplay.games.blackjack.domain.card import Card, Rank, Suit
from termplay.games.blackjack.domain.deck import Deck, EmptyDeckError


class TestDeck:
    def test_deck_has_52_cards(self) -> None:
        deck = Deck()
        assert deck.remaining == 52
        assert not deck.is_empty

    def test_draw_reduces_count(self) -> None:
        deck = Deck()
        deck.draw()
        assert deck.remaining == 51

    def test_draw_returns_card(self) -> None:
        deck = Deck()
        card = deck.draw()
        assert isinstance(card, Card)

    def test_draw_all_52(self) -> None:
        deck = Deck()
        drawn = [deck.draw() for _ in range(52)]
        assert deck.is_empty
        assert deck.remaining == 0
        assert len(set(drawn)) == 52  # todas únicas

    def test_draw_from_empty_raises(self) -> None:
        deck = Deck()
        for _ in range(52):
            deck.draw()
        with pytest.raises(EmptyDeckError):
            deck.draw()

    def test_shuffle_changes_order(self) -> None:
        deck = Deck()
        original_order = list(deck.cards)
        deck.shuffle()
        assert deck.cards != original_order

    def test_new_deck_has_all_same_cards(self) -> None:
        deck = Deck()
        all_cards = set(deck.cards)
        assert len(all_cards) == 52

    def test_custom_deck(self) -> None:
        cards = [Card(Suit.HEARTS, Rank.A), Card(Suit.SPADES, Rank.K)]
        deck = Deck(cards=cards)
        assert deck.remaining == 2
        assert deck.draw() == Card(Suit.SPADES, Rank.K)  # LIFO (pop)
