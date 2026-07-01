"""Match state and rules: setup, turn resolution, blocked-game scoring."""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace

from termplay.games.dominoes.domain.board import Board
from termplay.games.dominoes.domain.tile import Tile, double_six_set

HAND_SIZE = 7


@dataclass(frozen=True)
class MatchState:
    hands: tuple[tuple[Tile, ...], ...]
    boneyard: tuple[Tile, ...]
    board: Board = field(default_factory=Board)
    current: int = 0
    consecutive_passes: int = 0

    @classmethod
    def new(cls, num_players: int, rng: random.Random | None = None) -> MatchState:
        if not 2 <= num_players <= 4:
            raise ValueError("dominoes supports 2-4 players")
        tiles = double_six_set(rng)
        hands = tuple(
            tuple(tiles[i * HAND_SIZE : (i + 1) * HAND_SIZE])
            for i in range(num_players)
        )
        return cls(hands=hands, boneyard=tuple(tiles[num_players * HAND_SIZE :]))

    # ── queries ──────────────────────────────────────────────────────────────

    def playable_indices(self, player: int) -> list[int]:
        return [
            i for i, t in enumerate(self.hands[player]) if self.board.can_play(t)
        ]

    @property
    def num_players(self) -> int:
        return len(self.hands)

    def winner(self) -> int | None:
        """Index of the winner, or None while the match is running.

        A player wins by emptying their hand; a blocked game (everyone passed
        with an empty boneyard) goes to the lowest pip sum (first seat wins
        ties, keeping the rule deterministic).
        """
        for i, hand in enumerate(self.hands):
            if not hand:
                return i
        if self.is_blocked:
            sums = [sum(t.pips for t in hand) for hand in self.hands]
            return sums.index(min(sums))
        return None

    @property
    def is_blocked(self) -> bool:
        return not self.boneyard and self.consecutive_passes >= self.num_players

    def pip_sums(self) -> list[int]:
        return [sum(t.pips for t in hand) for hand in self.hands]

    # ── transitions (immutable — each returns a new state) ──────────────────

    def play_tile(self, player: int, tile_idx: int, side: str) -> MatchState:
        hand = self.hands[player]
        tile = hand[tile_idx]
        if side not in self.board.sides_for(tile):
            raise ValueError(f"tile {tile} cannot go on side {side}")
        new_hand = tuple(t for i, t in enumerate(hand) if i != tile_idx)
        hands = tuple(
            new_hand if i == player else h for i, h in enumerate(self.hands)
        )
        return replace(
            self,
            hands=hands,
            board=self.board.play(tile, side),
            current=(player + 1) % self.num_players,
            consecutive_passes=0,
        )

    def draw(self, player: int) -> MatchState:
        if not self.boneyard:
            raise ValueError("boneyard is empty")
        tile, *rest = self.boneyard
        hands = tuple(
            (*h, tile) if i == player else h for i, h in enumerate(self.hands)
        )
        return replace(self, hands=hands, boneyard=tuple(rest))

    def pass_turn(self, player: int) -> MatchState:
        return replace(
            self,
            current=(player + 1) % self.num_players,
            consecutive_passes=self.consecutive_passes + 1,
        )
