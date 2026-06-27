"""Bot behaviour in Brazilian rule prompts: tap minigame + card-0 target."""

from __future__ import annotations

import json

import pytest

from termplay.engine import bot_transport
from termplay.engine.bot_transport import BotTransportAdapter

_TAG = "uno.state"


@pytest.fixture(autouse=True)
def _instant_bot(monkeypatch: pytest.MonkeyPatch) -> None:
    # Remove reaction/think delays so tests run instantly and deterministically.
    monkeypatch.setattr(bot_transport, "_MINIGAME_REACTION", (0.0, 0.0))
    monkeypatch.setattr(bot_transport, "_THINK_DELAY", 0.0)


@pytest.mark.asyncio
async def test_bot_taps_in_minigame() -> None:
    bot = BotTransportAdapter("Bot 1")
    await bot.write(json.dumps({
        "v": _TAG, "phase": "minigame", "you": 1,
        "dot": {"x": 0.5, "y": 0.5}, "safe": [], "you_safe": False,
    }) + "\n")
    assert await bot.read_line() == "tap"


@pytest.mark.asyncio
async def test_bot_ignores_minigame_once_safe() -> None:
    bot = BotTransportAdapter("Bot 1")
    # Already safe → bot must not arm another tap (no move becomes ready).
    await bot.write(json.dumps({
        "v": _TAG, "phase": "minigame", "you": 1, "you_safe": True,
    }) + "\n")
    assert not bot._move_ready.is_set()


@pytest.mark.asyncio
async def test_bot_picks_smallest_hand_target_for_card_zero() -> None:
    bot = BotTransportAdapter("Bot 1")
    await bot.write(json.dumps({
        "v": _TAG, "phase": "play", "you": 1, "hand": ["R:5"],
        "playable": [], "need_color": False,
        "need_target": True, "targets": [0, 2],
        # player 0 has 6 cards, bot is 1, player 2 has 2 cards (smallest target).
        "players": [["A", 6], ["Bot 1", 1], ["C", 2]],
    }) + "\n")
    assert await bot.read_line() == "3"  # 1-based index of player 2
