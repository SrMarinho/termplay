"""TicTacToeController — 2-player multiplayer Velha.

First two players are assigned marks X and O and alternate turns; any further
players spectate (receive board broadcasts, never prompted). Per-player rendering
supports stealth (log-line) disguise, matching the Blackjack/Hangman controllers.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass

from termplay.engine.interfaces import ITransportAdapter
from termplay.games.tictactoe.state import TicTacToeState


def _ts() -> str:
    return time.strftime("%H:%M:%S")


@dataclass
class _Player:
    transport: ITransportAdapter
    name: str
    stealth: bool = False
    mark: str = ""
    active: bool = True


def _cell(state: TicTacToeState, idx: int) -> str:
    c = state.cells[idx]
    return c if c != " " else str(idx + 1)


def _board_pretty(state: TicTacToeState, turn: str) -> str:
    def row(a: int, b: int, c: int) -> str:
        return f"   {_cell(state, a)} │ {_cell(state, b)} │ {_cell(state, c)}"

    body = [
        "┌─ VELHA ───────┐",
        row(0, 1, 2),
        "  ───┼───┼───",
        row(3, 4, 5),
        "  ───┼───┼───",
        row(6, 7, 8),
        f"  vez: {turn}" if turn else "",
        "└───────────────┘",
    ]
    return "\r\n" + "\r\n".join(body) + "\r\n"


def _board_log(state: TicTacToeState, turn: str) -> str:
    cells = ",".join(c if c != " " else "_" for c in state.cells)
    parts = [f"cells={cells}"]
    if turn:
        parts.append(f"turn={turn}")
    return f"[INFO ] {_ts()} board.state " + " ".join(parts) + "\r\n"


class TicTacToeController:
    """Coordinates a multiplayer Velha match over player transports."""

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
        marks = ["X", "O"]
        for i, p in enumerate(self._players[:2]):
            p.mark = marks[i]
        self._state = TicTacToeState()

    async def run(self) -> None:
        await self._broadcast_banner()
        contenders = [p for p in self._players if p.mark]
        if len(contenders) < 2:
            await self._broadcast_board("")
            return
        await self._broadcast_board("")
        turn = 0
        while self._state.winner() is None and not self._state.is_full:
            player = contenders[turn % len(contenders)]
            if not player.active:
                break
            await self._broadcast_board(f"{player.name} ({player.mark})")
            await self._prompt(player)
            idx = await self._get_move(player)
            if idx is None:
                player.active = False
                break
            self._state.place(idx, player.mark)
            await self._broadcast_move(player, idx)
            await self._broadcast_board("")
            turn += 1
        await self._broadcast_end(contenders)

    async def _get_move(self, player: _Player) -> int | None:
        while True:
            try:
                raw = (await player.transport.read_line()).strip().lower()
            except ConnectionError:
                return None
            if raw in ("q", "quit", "sair"):
                return None
            if raw.isdigit() and 1 <= int(raw) <= 9:
                idx = int(raw) - 1
                if self._state.cells[idx] == " ":
                    return idx
            await self._write(
                player,
                self._line(
                    player, "WARN", "input.reject reason=invalid_cell",
                    "Escolha um número de 1 a 9 de uma casa livre. 'q' sai.",
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
                    f"[INFO ] {_ts()} service.start game=velha mode=multiplayer\r\n"
                )
            else:
                role = f" Você é '{p.mark}'." if p.mark else " Você assiste."
                await p.transport.write(
                    "\r\n=== VELHA MULTIPLAYER ===\r\n"
                    f"Jogo da velha 3x3.{role}\r\n"
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
                player, "INFO", "input.await type=cell",
                "▶ Sua vez! Número da casa (1-9):",
            ),
        )

    async def _broadcast_move(self, player: _Player, idx: int) -> None:
        async def send(p: _Player) -> None:
            await p.transport.write(
                self._line(
                    p, "INFO",
                    f"move.play player={player.name} mark={player.mark} cell={idx + 1}",
                    f"{player.name} marcou '{player.mark}' na casa {idx + 1}.",
                )
            )

        await asyncio.gather(*(send(p) for p in self._players))

    async def _broadcast_end(self, contenders: list[_Player]) -> None:
        win_mark = self._state.winner()
        winner = next((p for p in contenders if p.mark == win_mark), None)
        name = winner.name if winner else ""

        async def send(p: _Player) -> None:
            if p.stealth:
                outcome = "win" if win_mark else "draw"
                who = name or "-"
                await p.transport.write(
                    f"[INFO ] {_ts()} round.result outcome={outcome} winner={who}\r\n"
                )
            elif win_mark:
                await p.transport.write(f"\r\n🏆 {name} venceu! ('{win_mark}')\r\n")
            else:
                await p.transport.write("\r\n🤝 Deu velha! Empate.\r\n")

        await asyncio.gather(*(send(p) for p in self._players))
