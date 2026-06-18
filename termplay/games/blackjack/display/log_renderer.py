"""LogRenderer — disguise renderer that renders Blackjack as server log lines.

Same method surface as RichRenderer (display/renderer.py) but every method
returns a single plain log line — no Rich markup, no panels, no box-drawing
characters. Used when a player enables stealth mode so the game looks like an
application log feed at a glance.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from termplay.games.blackjack.conf import MIN_BET
from termplay.games.blackjack.domain.interfaces import RoundResult

if TYPE_CHECKING:
    from termplay.engine.interfaces import ITransportAdapter
    from termplay.games.blackjack.domain.card import Card
    from termplay.games.blackjack.domain.hand import Hand

_SUIT_LETTER = {"♥": "H", "♦": "D", "♣": "C", "♠": "S"}


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _card(card: Card) -> str:
    return f"{card.rank.value}{_SUIT_LETTER.get(card.suit.value, '?')}"


def _cards(cards: list[Card], hide_first: bool = False) -> str:
    parts = [
        "*" if i == 0 and hide_first else _card(c) for i, c in enumerate(cards)
    ]
    return ",".join(parts) if parts else "-"


def _line(level: str, event: str, *fields: str) -> str:
    body = " ".join((event, *fields))
    return f"[{level:<5}] {_ts()} {body}\r\n"


class LogRenderer:
    """Renders game events as plain log lines for disguise (stealth) mode."""

    def __init__(self, transport: ITransportAdapter) -> None:
        self._transport = transport

    def banner(self) -> str:
        return _line("INFO", "service.start", "game=blackjack", "mode=multiplayer")

    def farewell(self) -> str:
        return _line("INFO", "session.close", "reason=game_over")

    def multiplayer_table(
        self,
        my_name: str,
        my_hand: Hand,
        dealer_hand: Hand,
        balance: int,
        bet: int,
        others: list[tuple[str, Hand]],
        active_name: str = "",
        reveal_dealer: bool = False,
    ) -> str:
        dealer_val = str(dealer_hand.value) if reveal_dealer else "?"
        fields = [
            f"dealer={_cards(dealer_hand.cards, hide_first=not reveal_dealer)}"
            f"({dealer_val})",
            f"you={_cards(my_hand.cards)}({my_hand.value})",
            f"bal={balance}",
            f"bet={bet}",
        ]
        fields += [f"{n}={_cards(h.cards)}({h.value})" for n, h in others]
        if active_name:
            fields.append(f"turn={active_name}")
        return _line("INFO", "table.sync", *fields)

    def bet_prompt(self, balance: int) -> str:
        return _line(
            "INFO", "session.open", f"balance={balance}", f"min={MIN_BET}",
            "awaiting=bet",
        )

    def action_prompt(self, hand: Hand, bet: int) -> str:
        actions = "hit,stand" + (",double" if hand.can_double else "")
        return _line("INFO", "input.await", f"actions={actions}", f"bet={bet}")

    def result(self, result: RoundResult, bet: int, balance: int) -> str:
        token = {
            RoundResult.WIN: "win",
            RoundResult.LOSE: "lose",
            RoundResult.PUSH: "push",
            RoundResult.BLACKJACK: "blackjack",
        }[result]
        delta = {
            RoundResult.WIN: f"+{bet}",
            RoundResult.LOSE: f"-{bet}",
            RoundResult.PUSH: "0",
            RoundResult.BLACKJACK: f"+{int(bet * 1.5)}",
        }[result]
        return _line(
            "INFO", "round.result", f"outcome={token}", f"delta={delta}",
            f"balance={balance}",
        )

    def bust(self) -> str:
        return _line("WARN", "hand.bust", "total>21")

    def prompt(self, message: str) -> str:
        return _line("INFO", "input.await", f"prompt={message.strip()!r}")

    def error(self, message: str) -> str:
        return _line("WARN", "input.reject", f"reason={message.strip()!r}")

    def welcome(self) -> str:
        return self.banner()

    def goodbye(self, balance: int) -> str:
        return _line("INFO", "session.close", f"balance={balance}")
