"""Card — valor imutável representando uma carta de baralho."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final


class Suit(Enum):
    """Naipes do baralho francês."""

    HEARTS = "\u2665"
    DIAMONDS = "\u2666"
    CLUBS = "\u2663"
    SPADES = "\u2660"


class Rank(Enum):
    """Valores faciais das cartas."""

    A = "A"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    J = "J"
    Q = "Q"
    K = "K"


_FACE_VALUES: Final[dict[Rank, int]] = {
    Rank.A: 11,
    Rank.TWO: 2,
    Rank.THREE: 3,
    Rank.FOUR: 4,
    Rank.FIVE: 5,
    Rank.SIX: 6,
    Rank.SEVEN: 7,
    Rank.EIGHT: 8,
    Rank.NINE: 9,
    Rank.TEN: 10,
    Rank.J: 10,
    Rank.Q: 10,
    Rank.K: 10,
}

_RANKS: Final[list[Rank]] = list(Rank)


@dataclass(frozen=True)
class Card:
    """Carta de baralho francesa — imutável, comparável por igualdade."""

    suit: Suit
    rank: Rank

    @property
    def value(self) -> int:
        """Valor numérico no Blackjack (A=11, J/Q/K=10, demais = número)."""
        return _FACE_VALUES[self.rank]

    @property
    def is_ace(self) -> bool:
        """True se a carta é um Ás."""
        return self.rank is Rank.A

    @property
    def is_face(self) -> bool:
        """True se a carta é figura (J/Q/K)."""
        return self.rank in (Rank.J, Rank.Q, Rank.K)

    @property
    def display(self) -> str:
        """Exibição compacta: 'A♠', 'K♥', '10♦'."""
        return f"{self.rank.value}{self.suit.value}"

    def __str__(self) -> str:
        return self.display


def all_cards() -> list[Card]:
    """Retorna as 52 cartas de um baralho francês."""
    return [Card(suit, rank) for suit in Suit for rank in _RANKS]
