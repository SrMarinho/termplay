"""Smoke tests for Hangman / TicTacToe / Uno pure state logic."""

from __future__ import annotations

from termplay.games.hangman.state import HangmanState
from termplay.games.tictactoe.state import TicTacToeState
from termplay.games.uno.state import Card, UnoState, build_deck
from termplay.games.tictactoe.bot import VelhaBot


def test_hangman_win_and_loss() -> None:
    state = HangmanState(word="AB", max_wrong=2)
    assert state.guess_letter("A") is True
    assert state.is_won is False
    assert state.guess_letter("B") is True
    assert state.is_won is True

    lost = HangmanState(word="AB", max_wrong=2)
    assert lost.guess_letter("Z") is False
    assert lost.guess_letter("Y") is False
    assert lost.is_lost is True


def test_hangman_guess_whole_word() -> None:
    state = HangmanState(word="CAT")
    assert state.guess_word("dog") is False
    assert state.wrong == 1
    assert state.guess_word("cat") is True
    assert state.is_won is True


def test_tictactoe_row_win_and_draw() -> None:
    state = TicTacToeState()
    for idx in (0, 1, 2):
        assert state.place(idx, "X") is True
    assert state.winner() == "X"

    assert state.place(0, "O") is False  # occupied

    draw = TicTacToeState(cells=list("XXOOOXXXO"))
    assert draw.winner() is None
    assert draw.is_full is True


def test_uno_deck_and_play() -> None:
    assert len(build_deck()) == 108

    state = UnoState(
        hands=[[Card("R", "5"), Card("W", "wild")], [Card("B", "2")]],
        discard=[Card("R", "0")],
        active_color="R",
    )
    assert state.playable(Card("R", "9")) is True   # color match
    assert state.playable(Card("G", "0")) is True    # value match
    assert state.playable(Card("G", "7")) is False
    assert state.playable(Card("W", "wild4")) is True

    played = state.play(0, 1, chosen_color="B")  # wild → choose blue
    assert played.is_wild is True
    assert state.active_color == "B"
    assert state.winner() is None
    state.hands[1].clear()
    assert state.winner() == 1


def test_easy_move_picks_empty_cell() -> None:
    cells = ["X", "O", "X", "O", "X", "O", " ", " ", " "]
    idx = VelhaBot.easy_move(cells)
    assert idx in (6, 7, 8)
    assert cells[idx] == " "


def test_hard_move_blocks_opponent_win() -> None:
    # O about to win at index 2 (row 0: O, O, _)
    cells = ["O", "O", " ", "X", "X", " ", " ", " ", " "]
    idx = VelhaBot.hard_move(cells[:], "X")
    assert idx == 2  # must block


def test_hard_move_takes_win() -> None:
    # X at 0,3 can win at 6 (col 0)
    cells = ["X", "O", " ", "X", "O", " ", " ", " ", " "]
    idx = VelhaBot.hard_move(cells[:], "X")
    assert idx == 6  # X wins col 0


def test_hard_move_never_loses_from_start() -> None:
    # Bot plays as O from empty board; human plays first at center
    cells = [" "] * 9
    cells[4] = "X"  # human takes center
    idx = VelhaBot.hard_move(cells[:], "O")
    assert 0 <= idx <= 8
    assert cells[idx] == " "
