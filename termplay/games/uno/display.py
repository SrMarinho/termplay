"""Uno stealth rendering — server-log lines for disguise mode.

The visual TUI is driven by structured state (see ``controller.state_payload`` and
``frontends/screens/uno_screen.py``); only the disguise path renders text here.
"""

from __future__ import annotations

import time

from termplay.games.uno.state import Card, UnoState


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _log_face(card: Card) -> str:
    return f"{card.color}:{card.value}"


def render_log_view(
    state: UnoState,
    names: list[str],
    idx: int,
    *,
    is_active: bool,
    message: str = "",
) -> str:
    """Stealth view: table + private hand as server-log lines."""
    top = state.top
    arrow = "→" if state.direction == 1 else "←"
    counts = " ".join(f"{n}={len(state.hands[i])}" for i, n in enumerate(names))
    hand = " ".join(
        f"{i + 1}:{_log_face(c)}{'*' if state.playable(c) else ''}"
        for i, c in enumerate(state.hands[idx])
    )
    lines: list[str] = []
    if message:
        lines.append(f"[INFO ] {_ts()} event {message}")
    lines.append(
        f"[INFO ] {_ts()} table.state top={_log_face(top)} "
        f"color={state.active_color} dir={arrow} turn={names[state.current]} {counts}"
    )
    lines.append(f"[INFO ] {_ts()} hand.private {hand}")
    if is_active:
        lines.append(f"[INFO ] {_ts()} input.await type=card player={names[idx]}")
    return "\r\n".join(lines) + "\r\n"
