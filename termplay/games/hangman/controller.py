"""HangmanController — turn-based multiplayer Forca.

Players take turns guessing letters (or the whole word) of a shared hidden word.
Wrong guesses advance the hangman; the player who completes the word wins; if the
hangman completes first, everyone loses. Per-player rendering supports stealth
(log-line) disguise, matching the Blackjack controller.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Sequence
from dataclasses import dataclass

from termplay.engine.game_log import GameLogger
from termplay.engine.interfaces import ITransportAdapter
from termplay.games.hangman.conf import STAGES, WORDS
from termplay.games.hangman.state import HangmanState


def _ts() -> str:
    return time.strftime("%H:%M:%S")


@dataclass
class _Player:
    transport: ITransportAdapter
    name: str
    stealth: bool = False
    active: bool = True


def _board_pretty(state: HangmanState, turn: str) -> str:
    art = STAGES[min(state.wrong, len(STAGES) - 1)].strip("\n")
    art_lines = art.replace("\r\n", "\n").split("\n")
    body = [
        "┌─ FORCA ──────────────────────────┐",
        *(f"  {line}" for line in art_lines),
        "",
        f"  palavra:  {state.masked}",
        f"  errados:  {', '.join(state.wrong_letters) or '-'}"
        f"   ({state.wrong}/{state.max_wrong})",
        f"  vez: {turn}" if turn else "",
        "└──────────────────────────────────┘",
    ]
    return "\r\n" + "\r\n".join(body) + "\r\n"


def _board_log(state: HangmanState, turn: str) -> str:
    errors = ",".join(state.wrong_letters) or "-"
    parts = [
        f'masked="{state.masked}"',
        f"wrong={state.wrong}/{state.max_wrong}",
        f"errors={errors}",
    ]
    if turn:
        parts.append(f"turn={turn}")
    return f"[INFO ] {_ts()} puzzle.state " + " ".join(parts) + "\r\n"


class HangmanController:
    """Coordinates a multiplayer Forca match over player transports."""

    def __init__(
        self,
        transports: Sequence[ITransportAdapter],
        names: list[str] | None = None,
        stealth_flags: list[bool] | None = None,
    ) -> None:
        _names = names or [f"Player {i + 1}" for i in range(len(transports))]
        _stealth = stealth_flags or [False] * len(transports)
        self._players = [
            _Player(t, n, s)
            for t, n, s in zip(transports, _names, _stealth, strict=False)
        ]
        self._state = HangmanState(word=random.choice(WORDS).upper())
        self._log = GameLogger("forca")
        self._log.event(
            "match_start",
            players=[p.name for p in self._players],
            word_len=len(self._state.word),
            max_wrong=self._state.max_wrong,
        )

    async def run(self) -> None:
        await self._broadcast_banner()
        await self._broadcast_board("")
        turn = 0
        while not self._state.is_won and not self._state.is_lost:
            active = [p for p in self._players if p.active]
            if not active:
                break
            player = active[turn % len(active)]
            await self._broadcast_board(player.name)
            await self._prompt(player)
            guess = await self._get_guess(player)
            if guess is None:
                player.active = False
                continue
            await self._apply_guess(player, guess)
            turn += 1
        await self._broadcast_end()

    async def _apply_guess(self, player: _Player, guess: str) -> None:
        kind = "letter" if len(guess) == 1 else "word"
        if len(guess) == 1:
            correct = self._state.guess_letter(guess)
        else:
            correct = self._state.guess_word(guess)
        self._log.event(
            "guess",
            player=player.name,
            kind=kind,
            value=guess,
            hit=correct,
            wrong=self._state.wrong,
        )
        await self._broadcast_guess(player.name, guess, correct)
        await self._broadcast_board("")

    async def _get_guess(self, player: _Player) -> str | None:
        while True:
            try:
                raw = (await player.transport.read_line()).strip().upper()
            except ConnectionError:
                return None
            if raw in ("Q", "QUIT", "SAIR"):
                return None
            if raw.isalpha():
                return raw
            await self._write(
                player,
                self._line(
                    player, "WARN", "input.reject reason=letters_only",
                    "Digite uma letra (ou a palavra inteira). 'q' sai.",
                ),
            )

    # ── rendering / broadcast ────────────────────────────────────────────────

    def _line(
        self, player: _Player, level: str, log_body: str, pretty: str
    ) -> str:
        if player.stealth:
            return f"[{level:<5}] {_ts()} {log_body}\r\n"
        return f"\r\n{pretty}\r\n"

    async def _write(self, player: _Player, text: str) -> None:
        await player.transport.write(text)

    async def _broadcast_banner(self) -> None:
        async def send(p: _Player) -> None:
            if p.stealth:
                await p.transport.write(
                    f"[INFO ] {_ts()} service.start game=forca mode=multiplayer\r\n"
                )
            else:
                await p.transport.write(
                    "\r\n=== FORCA MULTIPLAYER ===\r\n"
                    "Adivinhe a palavra. Digite uma letra ou a palavra inteira.\r\n"
                )

        await asyncio.gather(*(send(p) for p in self._players))

    async def _broadcast_board(self, turn: str) -> None:
        async def send(p: _Player) -> None:
            view = _board_log(self._state, turn) if p.stealth else _board_pretty(
                self._state, turn
            )
            await p.transport.write(view)

        await asyncio.gather(*(send(p) for p in self._players))

    async def _prompt(self, player: _Player) -> None:
        await self._write(
            player,
            self._line(
                player, "INFO", "input.await type=letter",
                "▶ Sua vez! Digite uma letra:",
            ),
        )

    async def _broadcast_guess(self, name: str, guess: str, correct: bool) -> None:
        hit = "true" if correct else "false"
        verdict = "acertou" if correct else "errou"

        async def send(p: _Player) -> None:
            await p.transport.write(
                self._line(
                    p, "INFO",
                    f"guess.result player={name} value={guess} hit={hit}",
                    f"{name} tentou '{guess}' — {verdict}.",
                )
            )

        await asyncio.gather(*(send(p) for p in self._players))

    async def _broadcast_end(self) -> None:
        won = self._state.is_won
        word = self._state.word
        self._log.event(
            "match_end", outcome="win" if won else "lose", word=word
        )

        async def send(p: _Player) -> None:
            if p.stealth:
                outcome = "win" if won else "lose"
                await p.transport.write(
                    f"[INFO ] {_ts()} round.result outcome={outcome} word={word}\r\n"
                )
            elif won:
                await p.transport.write(
                    f"\r\n🎉 A palavra era {word}. Vocês venceram!\r\n"
                )
            else:
                await p.transport.write(
                    f"\r\n💀 Enforcado! A palavra era {word}.\r\n"
                )

        await asyncio.gather(*(send(p) for p in self._players))
