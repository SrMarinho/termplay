"""Tests for player-vs-player Blackjack: round resolution, bot, full match."""

from __future__ import annotations

import asyncio
import json
import random

import pytest

from termplay.engine.transport.queued_adapter import QueuedAdapter
from termplay.games.blackjack.application import versus_controller as vc
from termplay.games.blackjack.application.bot_transport import (
    BlackjackBotTransportAdapter,
)
from termplay.games.blackjack.application.versus_controller import (
    TARGET_SCORE,
    BlackjackVersusController,
)
from termplay.games.blackjack.domain.card import Card, Rank, Suit
from termplay.games.blackjack.domain.hand import Hand

_S = Suit.SPADES


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def _hand(*ranks: Rank) -> Hand:
    return Hand([Card(_S, r) for r in ranks])


def _controller(n: int) -> BlackjackVersusController:
    return BlackjackVersusController(
        [QueuedAdapter() for _ in range(n)], [f"P{i}" for i in range(n)]
    )


def test_resolve_highest_non_bust_wins_point() -> None:
    ctrl = _controller(3)
    ctrl._players[0].hand = _hand(Rank.K, Rank.Q)            # 20
    ctrl._players[1].hand = _hand(Rank.K, Rank.EIGHT)        # 18
    ctrl._players[2].hand = _hand(Rank.K, Rank.Q, Rank.FIVE)  # 25 bust

    winner = ctrl._resolve()

    assert winner is ctrl._players[0]
    assert ctrl._players[0].score == 1
    assert ctrl._players[1].score == 0


def test_resolve_tie_pushes_no_point() -> None:
    ctrl = _controller(2)
    ctrl._players[0].hand = _hand(Rank.K, Rank.Q)  # 20
    ctrl._players[1].hand = _hand(Rank.J, Rank.Q)  # 20

    winner = ctrl._resolve()

    assert winner is None
    assert all(p.score == 0 for p in ctrl._players)


def test_resolve_all_bust_is_push() -> None:
    ctrl = _controller(2)
    ctrl._players[0].hand = _hand(Rank.K, Rank.Q, Rank.FIVE)  # 25
    ctrl._players[1].hand = _hand(Rank.K, Rank.J, Rank.THREE)  # 23

    assert ctrl._resolve() is None


def test_status_labels() -> None:
    ctrl = _controller(1)
    p = ctrl._players[0]
    p.hand = _hand(Rank.A, Rank.K)  # natural blackjack
    assert ctrl._status(p) == "blackjack"
    p.hand = _hand(Rank.K, Rank.Q, Rank.FIVE)
    assert ctrl._status(p) == "bust"


@pytest.mark.asyncio
async def test_bot_hits_below_17_stands_otherwise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "termplay.games.blackjack.application.bot_transport._REACTION", (0.0, 0.0)
    )
    bot = BlackjackBotTransportAdapter("Bot 1")

    await bot.write(json.dumps({
        "v": "blackjack.state", "phase": "play", "your_turn": True, "hand_value": 12,
    }) + "\n")
    assert await bot.read_line() == "h"

    await bot.write(json.dumps({
        "v": "blackjack.state", "phase": "play", "your_turn": True, "hand_value": 19,
    }) + "\n")
    assert await bot.read_line() == "s"


def test_full_match_completes_with_a_winner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vc, "RESULT_PAUSE", 0.0)
    monkeypatch.setattr(
        "termplay.games.blackjack.application.bot_transport._REACTION", (0.0, 0.0)
    )
    random.seed(1234)
    ctrl = BlackjackVersusController(
        [BlackjackBotTransportAdapter("A"), BlackjackBotTransportAdapter("B")],
        ["A", "B"],
    )
    _run(ctrl.run())

    assert ctrl._winner_name in ("A", "B")
    assert max(p.score for p in ctrl._players) >= TARGET_SCORE
