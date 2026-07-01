"""DominoesController — turn loop for a 2-4 player match.

A player with no playable tile auto-draws from the boneyard until one fits
(Brazilian style); with the boneyard empty the turn auto-passes, so input is
only ever requested when there is a real choice to make.
"""

from __future__ import annotations

from collections.abc import Sequence

from termplay.engine.game_log import GameLogger
from termplay.engine.interfaces import ITransportAdapter
from termplay.games.dominoes.application.broadcaster import (
    Seat,
    broadcast,
    broadcast_text,
)
from termplay.games.dominoes.domain.match_state import MatchState


class DominoesController:
    """Coordinates a multiplayer dominoes match over player transports."""

    def __init__(
        self,
        transports: Sequence[ITransportAdapter],
        names: list[str] | None = None,
        stealth_flags: list[bool] | None = None,
    ) -> None:
        _names = names or [f"Player {i + 1}" for i in range(len(transports))]
        _stealth = stealth_flags or [False] * len(transports)
        self._seats = [
            Seat(t, n, s)
            for t, n, s in zip(transports, _names, _stealth, strict=False)
        ]
        self._state = MatchState.new(len(self._seats))
        self._log = GameLogger("domino")
        self._log.event(
            "match_start",
            players=[s.name for s in self._seats],
            boneyard=len(self._state.boneyard),
        )

    async def run(self) -> None:
        message = ""
        while self._state.winner() is None:
            idx = self._state.current
            seat = self._seats[idx]
            if not seat.active:
                self._state = self._state.pass_turn(idx)
                continue

            drew = await self._auto_draw(idx)
            if drew:
                message = f"{seat.name} comprou {drew} pedra(s)"
            playable = self._state.playable_indices(idx)
            if not playable:
                self._log.event("pass", player=seat.name)
                await broadcast_text(self._seats, f"{seat.name} passou a vez.")
                self._state = self._state.pass_turn(idx)
                message = ""
                continue

            await broadcast(self._state, self._seats, message)
            message = ""
            move = await self._get_move(seat, playable)
            if move is None:
                seat.active = False
                self._log.event("leave", player=seat.name)
                await broadcast_text(self._seats, f"👋 {seat.name} saiu da partida.")
                if sum(s.active for s in self._seats) < 2:
                    break
                self._state = self._state.pass_turn(idx)
                continue
            tile_idx, side = move
            tile = self._state.hands[idx][tile_idx]
            self._state = self._state.play_tile(idx, tile_idx, side)
            self._log.event(
                "play", player=seat.name, tile=str(tile), side=side,
                remaining=len(self._state.hands[idx]),
            )
        await self._broadcast_end()

    async def _auto_draw(self, idx: int) -> int:
        """Draw until a tile fits (or the boneyard runs dry). Returns count."""
        drawn = 0
        while not self._state.playable_indices(idx) and self._state.boneyard:
            self._state = self._state.draw(idx)
            drawn += 1
        if drawn:
            self._log.event("draw", player=self._seats[idx].name, count=drawn)
        return drawn

    async def _get_move(
        self, seat: Seat, playable: list[int]
    ) -> tuple[int, str] | None:
        """Read '<n>[ e|d]' → (tile index, side). None means the player left."""
        while True:
            try:
                raw = (await seat.transport.read_line()).strip().lower()
            except (ConnectionError, OSError):
                return None
            if raw in ("q", "quit", "sair"):
                return None
            parts = raw.split()
            if not parts or not parts[0].isdigit():
                await self._reject(seat, "Digite o número da pedra (ex.: 3).")
                continue
            tile_idx = int(parts[0]) - 1
            if tile_idx not in playable:
                await self._reject(seat, "Essa pedra não encaixa. Escolha uma com ▶.")
                continue
            tile = self._state.hands[self._state.current][tile_idx]
            sides = self._state.board.sides_for(tile)
            wanted = {"e": "left", "d": "right"}.get(parts[1][0]) if len(parts) > 1 else None
            if wanted and wanted in sides:
                return tile_idx, wanted
            return tile_idx, sides[-1]  # default: right end

    async def _reject(self, seat: Seat, text: str) -> None:
        try:
            await seat.transport.write(f"\r\n{text}\r\n")
        except (ConnectionError, OSError):
            seat.active = False

    async def _broadcast_end(self) -> None:
        win = self._state.winner()
        name = self._seats[win].name if win is not None else ""
        blocked = self._state.is_blocked
        self._log.event(
            "match_end",
            winner=name or None,
            blocked=blocked,
            pip_sums=self._state.pip_sums(),
        )
        if blocked:
            sums = ", ".join(
                f"{s.name}: {p}" for s, p in zip(self._seats, self._state.pip_sums(), strict=False)
            )
            text = f"🔒 Jogo fechado! Menor soma vence — {sums}. Vencedor: {name}."
        else:
            text = f"🏆 {name} bateu! Fim de jogo."
        await broadcast_text(self._seats, text)
