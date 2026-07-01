"""Line of play — immutable: every move returns a new Board."""

from __future__ import annotations

from dataclasses import dataclass, field

from termplay.games.dominoes.domain.tile import Tile


@dataclass(frozen=True)
class Board:
    """Tiles laid left-to-right. ``line[0].a`` is the left end,
    ``line[-1].b`` the right end."""

    line: tuple[Tile, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        return not self.line

    @property
    def left_end(self) -> int | None:
        return self.line[0].a if self.line else None

    @property
    def right_end(self) -> int | None:
        return self.line[-1].b if self.line else None

    def can_play(self, tile: Tile) -> bool:
        if self.is_empty:
            return True
        assert self.left_end is not None and self.right_end is not None
        return tile.matches(self.left_end) or tile.matches(self.right_end)

    def sides_for(self, tile: Tile) -> list[str]:
        """Which sides ('left'/'right') accept this tile."""
        if self.is_empty:
            return ["right"]
        sides = []
        if self.left_end is not None and tile.matches(self.left_end):
            sides.append("left")
        if self.right_end is not None and tile.matches(self.right_end):
            sides.append("right")
        return sides

    def play(self, tile: Tile, side: str) -> Board:
        """Return a new board with ``tile`` attached to ``side``."""
        if self.is_empty:
            return Board(line=(tile,))
        if side == "left":
            assert self.left_end is not None
            oriented = tile.oriented(self.left_end)
            # a must face outward on the left: [b|a] with a touching the line
            return Board(line=(Tile(oriented.b, oriented.a), *self.line))
        assert self.right_end is not None
        return Board(line=(*self.line, tile.oriented(self.right_end)))
