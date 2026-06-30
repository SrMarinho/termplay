from __future__ import annotations
import asyncio
import time
from termplay.games.truco.application.context import TrucoContext, Player
from termplay.games.truco.conf import ENVITE_LADDER, TURN_TIMEOUT


async def _read(player: Player, timeout: float) -> str | None:
    try:
        return (await asyncio.wait_for(player.transport.read_line(), timeout=timeout)).strip().lower()
    except TimeoutError:
        return None
    except ConnectionError:
        return ""  # sentinel for disconnect


async def get_play(ctx: TrucoContext, player: Player, player_idx: int) -> tuple[str, int | None]:
    """
    Returns:
      ("play", card_idx)  — play that card from hand
      ("truco", None)     — call envite
      ("quit", None)      — disconnected
      ("timeout", None)   — timed out
    """
    hand = ctx.state.hands[player_idx]
    can_call = ctx.state.envite is None  # can only call if no envite in progress
    while True:
        remaining = ctx.turn_deadline - time.time()
        if remaining <= 0:
            return ("timeout", None)
        raw = await _read(player, remaining)
        if raw is None:
            return ("timeout", None)
        if raw == "":
            return ("quit", None)
        if raw in ("q", "quit", "sair"):
            return ("quit", None)
        if can_call and raw in ("t", "truco"):
            return ("truco", None)
        if raw.isdigit():
            pos = int(raw) - 1
            if 0 <= pos < len(hand):
                return ("play", pos)


async def get_envite_response(
    ctx: TrucoContext, player: Player, offer: int
) -> str:
    """Return 'accept', 'raise', or 'run'."""
    can_raise = offer < ENVITE_LADDER[-1]
    while True:
        remaining = ctx.turn_deadline - time.time()
        if remaining <= 0:
            return "run"
        raw = await _read(player, remaining)
        if raw is None:
            return "run"
        if raw == "":
            return "run"
        if raw in ("a", "aceitar", "accept", "s", "sim"):
            return "accept"
        if raw in ("c", "correr", "run", "n", "nao", "não", "x"):
            return "run"
        if can_raise and raw in ("r", "raise", "aumentar", "mais", "m"):
            return "raise"


async def get_mao_de_onze(ctx: TrucoContext, player: Player) -> bool:
    """Return True to play, False to fold."""
    while True:
        remaining = ctx.turn_deadline - time.time()
        if remaining <= 0:
            return False
        raw = await _read(player, remaining)
        if raw is None:
            return False
        if raw == "":
            return False
        if raw in ("s", "sim", "jogar", "play", "j"):
            return True
        if raw in ("n", "nao", "não", "fugir", "fold", "f", "c", "correr"):
            return False
