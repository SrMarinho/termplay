from __future__ import annotations
from dataclasses import dataclass
from termplay.games.truco.conf import DECK_RANKS, SUIT_STRENGTH


@dataclass(frozen=True)
class Card:
    suit: str  # C, H, S, D
    rank: str  # 4,5,6,7,Q,J,K,A,2,3

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


def manilha_rank(vira: Card) -> str:
    idx = DECK_RANKS.index(vira.rank)
    return DECK_RANKS[(idx + 1) % len(DECK_RANKS)]


def card_strength(card: Card, vira: Card) -> int:
    mrank = manilha_rank(vira)
    if card.rank == mrank:
        return 10 + SUIT_STRENGTH[card.suit]  # 10-13
    return DECK_RANKS.index(card.rank)  # 0-9
