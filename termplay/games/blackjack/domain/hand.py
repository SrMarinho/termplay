"""Hand — mão de cartas com cálculo de valor (com Ás ajustável)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Self

from termplay.games.blackjack.domain.card import Card


@dataclass
class Hand:
    """Mão de um jogador ou dealer.

    Atributos:
        cards: cartas na mão (ordem de compra).
    """

    cards: list[Card] = field(default_factory=list)

    def add(self, card: Card) -> None:
        """Adiciona uma carta à mão."""
        self.cards.append(card)

    @property
    def value(self) -> int:
        """Valor total da mão, com ajuste de Ás (11 → 1 se estourar 21)."""
        total = sum(c.value for c in self.cards)
        aces = sum(1 for c in self.cards if c.is_ace)
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    @property
    def is_bust(self) -> bool:
        """True se a mão estourou (>21)."""
        return self.value > 21

    @property
    def is_blackjack(self) -> bool:
        """True se a mão é um Blackjack natural (2 cartas, valor 21)."""
        return len(self.cards) == 2 and self.value == 21

    @property
    def is_pair(self) -> bool:
        """True se a mão tem exatamente 2 cartas do mesmo valor."""
        return len(self.cards) == 2 and self.cards[0].value == self.cards[1].value

    @property
    def can_double(self) -> bool:
        """True se pode dobrar a aposta (2 cartas, sem blackjack)."""
        return len(self.cards) == 2 and not self.is_blackjack

    def __len__(self) -> int:
        return len(self.cards)

    def __str__(self) -> str:
        return " ".join(c.display for c in self.cards)

    @classmethod
    def from_cards(cls, cards: Sequence[Card]) -> Self:
        """Cria uma mão a partir de uma sequência de cartas."""
        return cls(list(cards))
