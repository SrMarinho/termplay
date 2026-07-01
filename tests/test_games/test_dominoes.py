"""Dominoes: tile/board domain rules, blocked scoring and a full bot match."""

from __future__ import annotations

import asyncio

import pytest

from termplay.games.dominoes.domain.board import Board
from termplay.games.dominoes.domain.match_state import MatchState
from termplay.games.dominoes.domain.tile import Tile, double_six_set


class TestTile:
    def test_set_has_28_unique_tiles(self) -> None:
        tiles = double_six_set()
        assert len(tiles) == 28
        assert len({(min(t.a, t.b), max(t.a, t.b)) for t in tiles}) == 28

    def test_matches_and_orientation(self) -> None:
        tile = Tile(3, 5)
        assert tile.matches(3) and tile.matches(5)
        assert not tile.matches(4)
        assert tile.oriented(5) == Tile(5, 3)
        assert tile.oriented(3) == Tile(3, 5)
        with pytest.raises(ValueError):
            tile.oriented(1)


class TestBoard:
    def test_first_tile_opens_both_ends(self) -> None:
        board = Board().play(Tile(3, 5), "right")
        assert board.left_end == 3
        assert board.right_end == 5

    def test_play_right_orients_tile(self) -> None:
        board = Board().play(Tile(3, 5), "right").play(Tile(2, 5), "right")
        assert board.right_end == 2
        assert board.line[-1] == Tile(5, 2)

    def test_play_left_orients_tile(self) -> None:
        board = Board().play(Tile(3, 5), "right").play(Tile(3, 6), "left")
        assert board.left_end == 6
        assert board.line[0] == Tile(6, 3)

    def test_can_play_checks_both_ends(self) -> None:
        board = Board().play(Tile(3, 5), "right")
        assert board.can_play(Tile(5, 5))
        assert board.can_play(Tile(0, 3))
        assert not board.can_play(Tile(1, 2))

    def test_sides_for_double_match(self) -> None:
        board = Board().play(Tile(4, 4), "right")
        assert board.sides_for(Tile(4, 1)) == ["left", "right"]


class TestMatchState:
    def test_new_deals_seven_each(self) -> None:
        state = MatchState.new(4)
        assert all(len(h) == 7 for h in state.hands)
        assert len(state.boneyard) == 0  # 4×7 = 28, nothing left
        state2 = MatchState.new(2)
        assert len(state2.boneyard) == 14

    def test_play_tile_is_immutable(self) -> None:
        state = MatchState.new(2)
        idx = state.playable_indices(0)[0]
        after = state.play_tile(0, idx, "right")
        assert len(state.hands[0]) == 7  # original untouched
        assert len(after.hands[0]) == 6
        assert after.current == 1

    def test_winner_by_empty_hand(self) -> None:
        state = MatchState(
            hands=((Tile(1, 2),), (Tile(3, 3), Tile(4, 5))),
            boneyard=(),
            board=Board().play(Tile(2, 6), "right"),
            current=0,
        )
        assert state.winner() is None
        won = state.play_tile(0, 0, "left")
        assert won.winner() == 0

    def test_blocked_game_lowest_pips_wins(self) -> None:
        state = MatchState(
            hands=((Tile(6, 6),), (Tile(1, 0),)),
            boneyard=(),
            board=Board().play(Tile(2, 3), "right"),
            current=0,
            consecutive_passes=2,
        )
        assert state.is_blocked
        assert state.winner() == 1  # 1 pip beats 12

    def test_draw_moves_tile_from_boneyard(self) -> None:
        state = MatchState(
            hands=((), ()),
            boneyard=(Tile(1, 1), Tile(2, 2)),
        )
        after = state.draw(0)
        assert after.hands[0] == (Tile(1, 1),)
        assert after.boneyard == (Tile(2, 2),)


class TestFullMatch:
    def test_two_bots_play_to_completion(self, monkeypatch) -> None:
        import termplay.games.dominoes.application.bot_transport as bt
        from termplay.games.dominoes.application.controller import (
            DominoesController,
        )

        monkeypatch.setattr(bt, "_THINK_DELAY", 0)
        bots = [
            bt.DominoesBotTransportAdapter("Bot 1"),
            bt.DominoesBotTransportAdapter("Bot 2"),
        ]
        ctrl = DominoesController(bots, ["Bot 1", "Bot 2"])

        async def scenario() -> None:
            async with asyncio.timeout(10):
                await ctrl.run()

        asyncio.run(scenario())
        assert ctrl._state.winner() is not None
