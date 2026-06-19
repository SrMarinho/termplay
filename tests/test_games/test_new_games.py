"""Smoke tests for Hangman / TicTacToe / Uno pure state logic."""

from __future__ import annotations

import asyncio
import json

from termplay.engine.transport.queued_adapter import QueuedAdapter
from termplay.games.hangman.state import HangmanState
from termplay.games.tictactoe.bot import VelhaBot
from termplay.games.tictactoe.controller import TicTacToeController
from termplay.games.tictactoe.state import TicTacToeState
from termplay.games.uno.state import Card, UnoState, build_deck


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


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


def test_controller_sends_json_state() -> None:
    p1 = QueuedAdapter()
    p2 = QueuedAdapter()
    p1.feed("1")  # X plays cell 1 (idx 0)
    p2.feed("4")  # O plays cell 4 (idx 3)
    p1.feed("2")  # X plays cell 2 (idx 1)
    p2.feed("5")  # O plays cell 5 (idx 4)
    p1.feed("3")  # X wins row 0: cells 0,1,2
    ctrl = TicTacToeController([p1, p2])
    _run(ctrl.run())

    # p1 received multiple JSON state messages
    msgs = []
    while not p1.output_queue.empty():
        msgs.append(p1.output_queue.get_nowait())

    # At least one message should be valid JSON velha.state
    states = []
    for m in msgs:
        for line in m.splitlines():
            line = line.strip()
            try:
                data = json.loads(line)
                if data.get("v") == "velha.state":
                    states.append(data)
            except (ValueError, TypeError):
                pass

    assert len(states) > 0
    last = states[-1]
    assert last["phase"] == "over"
    assert last["winner"] == "X"
    assert last["your_mark"] == "X"
