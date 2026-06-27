"""Tests for Uno rule variants: ruleset presets, stacking, Wild+4 legality."""

from __future__ import annotations

import asyncio
import time

from termplay.engine.transport.queued_adapter import QueuedAdapter
from termplay.games.uno.controller import UnoController
from termplay.games.uno.ruleset import UnoRuleset
from termplay.games.uno.state import Card, UnoState


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def test_ruleset_presets() -> None:
    std = UnoRuleset.standard()
    assert std.draw_then_play and std.initial_card_effect and std.wild4_strict
    assert not std.stack_draws and not std.draw_until_play

    br = UnoRuleset.brazilian()
    assert br.stack_draws and br.draw_until_play
    assert br.zero_swap and br.one_minigame
    assert not br.wild4_strict and not br.initial_card_effect
    assert not UnoRuleset.standard().zero_swap
    assert not UnoRuleset.standard().one_minigame

    assert UnoRuleset.from_name("br").stack_draws is True
    assert UnoRuleset.from_name("standard").wild4_strict is True
    assert UnoRuleset.from_name("nonsense").wild4_strict is True  # falls back


def test_from_spec_accepts_name_dict_and_json() -> None:
    assert UnoRuleset.from_spec("br").stack_draws is True
    assert UnoRuleset.from_spec({"stack_draws": True}).stack_draws is True
    assert UnoRuleset.from_spec('{"wild4_strict": true}').wild4_strict is True
    assert UnoRuleset.from_spec({"unknown": True}).stack_draws is False  # ignored
    assert UnoRuleset.from_spec(None).wild4_strict is True  # default standard
    assert UnoRuleset.from_spec("{bad json").wild4_strict is True  # falls back


def _brazilian_controller() -> UnoController:
    adapters = [QueuedAdapter() for _ in range(3)]
    ctrl = UnoController(adapters, ["A", "B", "C"], ruleset=UnoRuleset.brazilian())
    ctrl._state = UnoState(
        hands=[
            [Card("R", "draw2"), Card("Y", "9")],
            [Card("G", "draw2"), Card("Y", "8")],
            [Card("B", "5"), Card("Y", "7")],
        ],
        deck=[Card("Y", "1") for _ in range(10)],
        discard=[Card("R", "0")],
        active_color="R",
        current=0,
    )
    return ctrl


def test_stacking_accumulates_and_forces_draw() -> None:
    ctrl = _brazilian_controller()

    async def scenario() -> None:
        # Player 0 plays +2 → pending 2, turn passes to 1.
        await ctrl._apply_move(ctrl._players[0], 0, 0)
        assert ctrl._state.pending_draws == 2
        assert ctrl._state.pending_draw_value == "draw2"
        assert ctrl._state.current == 1

        # Player 1 stacks +2 → pending 4, turn passes to 2.
        assert ctrl._can_stack(1) is True
        await ctrl._apply_move(ctrl._players[1], 1, 0)
        assert ctrl._state.pending_draws == 4
        assert ctrl._state.current == 2

        # Player 2 cannot stack → absorbs all 4, pile resets, turn passes.
        assert ctrl._can_stack(2) is False
        await ctrl._take_pending(ctrl._players[2], 2)
        assert ctrl._state.pending_draws == 0
        assert ctrl._state.pending_draw_value == ""
        assert len(ctrl._state.hands[2]) == 2 + 4
        assert ctrl._state.current == 0

    _run(scenario())


def test_wild4_strict_rejected_when_other_card_playable() -> None:
    adapters = [QueuedAdapter(), QueuedAdapter()]
    ctrl = UnoController(adapters, ["A", "B"], ruleset=UnoRuleset.standard())
    ctrl._state = UnoState(
        hands=[[Card("W", "wild4"), Card("R", "5")], [Card("B", "1")]],
        discard=[Card("R", "0")],
        active_color="R",
        current=0,
    )
    ctrl._turn_deadline = time.time() + 30

    player = ctrl._players[0]
    player.transport.feed("1")  # wild4 → must be rejected (R:5 is playable)
    player.transport.feed("2")  # R:5 → accepted

    move = _run(ctrl._get_move(player, 0))
    assert move == ("play", 1)


def test_wild4_allowed_in_brazilian() -> None:
    adapters = [QueuedAdapter(), QueuedAdapter()]
    ctrl = UnoController(adapters, ["A", "B"], ruleset=UnoRuleset.brazilian())
    ctrl._state = UnoState(
        hands=[[Card("W", "wild4"), Card("R", "5")], [Card("B", "1")]],
        discard=[Card("R", "0")],
        active_color="R",
        current=0,
    )
    ctrl._turn_deadline = time.time() + 30

    player = ctrl._players[0]
    player.transport.feed("1")  # wild4 accepted even with R:5 in hand

    move = _run(ctrl._get_move(player, 0))
    assert move == ("play", 0)


def test_zero_swap_exchanges_full_hands() -> None:
    adapters = [QueuedAdapter() for _ in range(2)]
    ctrl = UnoController(adapters, ["A", "B"], ruleset=UnoRuleset.brazilian())
    ctrl._state = UnoState(
        hands=[[Card("R", "0"), Card("Y", "9")], [Card("B", "5"), Card("G", "3")]],
        deck=[Card("Y", "1") for _ in range(5)],
        discard=[Card("R", "7")],
        active_color="R",
        current=0,
    )
    # Player 0 plays the 0 (idx 0). Only one other player → auto target, hands swap.
    _run(ctrl._apply_move(ctrl._players[0], 0, 0))
    # Player 0 now holds what player 1 had; player 1 got player 0's leftover.
    assert [(c.color, c.value) for c in ctrl._state.hands[0]] == [("B", "5"), ("G", "3")]
    assert ("Y", "9") in [(c.color, c.value) for c in ctrl._state.hands[1]]


def test_one_minigame_last_to_tap_draws() -> None:
    adapters = [QueuedAdapter() for _ in range(3)]
    ctrl = UnoController(adapters, ["A", "B", "C"], ruleset=UnoRuleset.brazilian())
    ctrl._state = UnoState(
        hands=[[Card("R", "5")], [Card("B", "5")], [Card("G", "5")]],
        deck=[Card("Y", "1") for _ in range(10)],
        discard=[Card("R", "7")],
        active_color="R",
        current=0,
    )
    # Players 0 and 1 tap; player 2 never does → player 2 draws a card.
    ctrl._players[0].transport.feed("tap")
    ctrl._players[1].transport.feed("tap")

    async def scenario() -> None:
        await ctrl._do_one_minigame(0)

    _run(scenario())
    assert len(ctrl._state.hands[2]) == 2  # the slow one drew
    assert len(ctrl._state.hands[0]) == 1
    assert len(ctrl._state.hands[1]) == 1


def test_initial_reverse_card_effect() -> None:
    adapters = [QueuedAdapter() for _ in range(3)]
    ctrl = UnoController(adapters, ["A", "B", "C"], ruleset=UnoRuleset.standard())
    # Force a known first card and re-apply the initial effect.
    ctrl._state = UnoState(
        hands=[[Card("R", "1")] for _ in range(3)],
        discard=[Card("R", "reverse")],
        active_color="R",
        current=0,
    )
    ctrl._apply_initial_card()
    assert ctrl._state.direction == -1
    assert ctrl._state.current == 2  # play starts from the last player
