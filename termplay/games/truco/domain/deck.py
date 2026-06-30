from __future__ import annotations
import random
from termplay.games.truco.conf import DECK_RANKS, DECK_SUITS
from termplay.games.truco.domain.card import Card


def build_deck() -> list[Card]:
    return [Card(suit, rank) for suit in DECK_SUITS for rank in DECK_RANKS]


class Deck:
    def __init__(self) -> None:
        self._cards: list[Card] = build_deck()
        random.shuffle(self._cards)

    def draw(self, n: int = 1) -> list[Card]:
        result, self._cards = self._cards[:n], self._cards[n:]
        return result

    def draw_one(self) -> Card:
        return self.draw(1)[0]
