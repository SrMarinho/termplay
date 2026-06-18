"""TicTacToeState — pure 3x3 board logic, zero I/O."""

from __future__ import annotations

from dataclasses import dataclass, field

_LINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
    (0, 4, 8), (2, 4, 6),             # diagonals
)


@dataclass
class TicTacToeState:
    """3x3 grid. Empty cells are spaces; marks are 'X' / 'O'."""

    cells: list[str] = field(default_factory=lambda: [" "] * 9)

    def place(self, idx: int, mark: str) -> bool:
        """Place mark at idx (0-8). Returns False if out of range or occupied."""
        if not 0 <= idx < 9 or self.cells[idx] != " ":
            return False
        self.cells[idx] = mark
        return True

    def winner(self) -> str | None:
        for a, b, c in _LINES:
            if self.cells[a] != " " and self.cells[a] == self.cells[b] == self.cells[c]:
                return self.cells[a]
        return None

    @property
    def is_full(self) -> bool:
        return all(c != " " for c in self.cells)
