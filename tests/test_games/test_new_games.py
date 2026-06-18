"""Smoke tests for Hangman / TicTacToe / Uno pure state logic."""

from __future__ import annotations

from termplay.games.hangman.state import HangmanState
from termplay.games.tictactoe.state import TicTacToeState
from termplay.games.uno.state import Card, UnoState, build_deck


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
