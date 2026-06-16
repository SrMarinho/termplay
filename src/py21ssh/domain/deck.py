"""Deck — baralho com embaralhamento e compra."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from py21ssh.domain.card import Card, all_cards


class EmptyDeckError(Exception):
    """Erro ao tentar comprar de um baralho vazio."""


@dataclass
class Deck:
    """Baralho de N cartas.

    Pode conter múltiplos baralhos franceses (shoe).
    Por padrão, um baralho de 52 cartas.

    Raises:
        EmptyDeckError: se draw() for chamado com o baralho vazio.
    """

    cards: list[Card] = field(default_factory=all_cards)

    def shuffle(self) -> None:
        """Embaralha as cartas in-place."""
        random.shuffle(self.cards)

    def draw(self) -> Card:
        """Remove e retorna a carta do topo.

        Raises:
            EmptyDeckError: se não houver cartas restantes.
        """
        if not self.cards:
            raise EmptyDeckError("Não há cartas no baralho.")
        return self.cards.pop()

    @property
    def remaining(self) -> int:
        """Quantidade de cartas restantes."""
        return len(self.cards)

    @property
    def is_empty(self) -> bool:
        """True se o baralho acabou."""
        return not self.cards
