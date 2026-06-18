"""UnoState — pure Uno game state, zero I/O.

Cards are (color, value) pairs. Colors: R G B Y (and W for wilds). Values:
'0'..'9', 'skip', 'reverse', 'draw2', 'wild', 'wild4'.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

COLORS = ("R", "G", "B", "Y")
_ACTIONS = ("skip", "reverse", "draw2")


@dataclass(frozen=True)
class Card:
    color: str
    value: str

    @property
    def is_wild(self) -> bool:
        return self.color == "W"


def build_deck() -> list[Card]:
    deck: list[Card] = []
    for color in COLORS:
        deck.append(Card(color, "0"))
        for n in range(1, 10):
            deck.extend([Card(color, str(n))] * 2)
        for action in _ACTIONS:
            deck.extend([Card(color, action)] * 2)
    deck.extend([Card("W", "wild")] * 4)
    deck.extend([Card("W", "wild4")] * 4)
    return deck


@dataclass
class UnoState:
    """Mutable Uno table: draw pile, discard, hands, turn pointer, direction."""

    hands: list[list[Card]]
    deck: list[Card] = field(default_factory=list)
    discard: list[Card] = field(default_factory=list)
    current: int = 0
    direction: int = 1
    active_color: str = ""

    @classmethod
    def new(cls, num_players: int, hand_size: int = 7) -> UnoState:
        deck = build_deck()
        random.shuffle(deck)
        hands = [[deck.pop() for _ in range(hand_size)] for _ in range(num_players)]
        # First non-wild card starts the discard pile.
        while True:
            top = deck.pop()
            if not top.is_wild:
                break
            deck.insert(0, top)
        state = cls(hands=hands, deck=deck, discard=[top], active_color=top.color)
        return state

    @property
    def top(self) -> Card:
        return self.discard[-1]

    def playable(self, card: Card) -> bool:
        if card.is_wild:
            return True
        return card.color == self.active_color or card.value == self.top.value

    def has_playable(self, player: int) -> bool:
        return any(self.playable(c) for c in self.hands[player])

    def draw(self, player: int, count: int = 1) -> list[Card]:
        drawn: list[Card] = []
        for _ in range(count):
            if not self.deck:
                self._reshuffle()
            if not self.deck:
                break
            card = self.deck.pop()
            self.hands[player].append(card)
            drawn.append(card)
        return drawn

    def _reshuffle(self) -> None:
        if len(self.discard) <= 1:
            return
        top = self.discard[-1]
        rest = self.discard[:-1]
        random.shuffle(rest)
        self.deck = rest
        self.discard = [top]

    def play(self, player: int, idx: int, chosen_color: str = "") -> Card:
        """Remove card at idx from hand, push to discard, update active color."""
        card = self.hands[player].pop(idx)
        self.discard.append(card)
        if card.is_wild:
            self.active_color = chosen_color or COLORS[0]
        else:
            self.active_color = card.color
        return card

    def advance(self, skip: bool = False) -> None:
        step = self.direction * (2 if skip else 1)
        self.current = (self.current + step) % len(self.hands)

    def next_index(self) -> int:
        return (self.current + self.direction) % len(self.hands)

    def winner(self) -> int | None:
        for i, hand in enumerate(self.hands):
            if not hand:
                return i
        return None
