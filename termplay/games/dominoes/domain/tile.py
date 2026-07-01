"""Domino tile value object — an unordered pair of pip counts (0-6)."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Tile:
    a: int
    b: int

    @property
    def pips(self) -> int:
        return self.a + self.b

    @property
    def is_double(self) -> bool:
        return self.a == self.b

    def matches(self, end: int) -> bool:
        return end in (self.a, self.b)

    def oriented(self, end: int) -> Tile:
        """Return this tile turned so that ``a`` touches ``end``."""
        if self.a == end:
            return self
        if self.b == end:
            return Tile(self.b, self.a)
        raise ValueError(f"tile {self} does not match end {end}")

    def __str__(self) -> str:
        return f"[{self.a}|{self.b}]"


def double_six_set(rng: random.Random | None = None) -> list[Tile]:
    """The shuffled 28-tile double-six set."""
    tiles = [Tile(a, b) for a in range(7) for b in range(a, 7)]
    (rng or random).shuffle(tiles)
    return tiles
