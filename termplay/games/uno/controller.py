"""UnoController — turn-based multiplayer Uno.

Players take turns playing a card matching the discard's color or value (or a
wild). Action cards (skip/reverse/draw2/wild4) alter turn order and force draws.
First player to empty their hand wins. Per-player rendering supports stealth
(log-line) disguise, matching the other game controllers.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass

from termplay.engine.interfaces import ITransportAdapter
from termplay.games.uno.state import COLORS, Card, UnoState


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _card(card: Card) -> str:
    return f"{card.color}:{card.value}"


@dataclass
class _Player:
    transport: ITransportAdapter
    name: str
    stealth: bool = False
    active: bool = True


class UnoController:
    """Coordinates a multiplayer Uno match over player transports."""

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
        self._state = UnoState.new(len(self._players))

    async def run(self) -> None:
        await self._broadcast_banner()
        while self._state.winner() is None:
            idx = self._state.current
            player = self._players[idx]
            if not player.active:
                self._state.advance()
                continue
            await self._broadcast_table()
            await self._show_hand(player)
            await self._prompt(player)
            move = await self._get_move(player, idx)
            if move is None:
                player.active = False
                if sum(p.active for p in self._players) < 2:
                    break
                self._state.advance()
                continue
            await self._apply_move(player, idx, move)
        await self._broadcast_end()

    async def _apply_move(self, player: _Player, idx: int, move: int | str) -> None:
        if move == "draw":
            drawn = self._state.draw(idx, 1)
            note = _card(drawn[0]) if drawn else "none"
            await self._broadcast_event(
                f"draw.card player={player.name} count=1",
                f"{player.name} comprou uma carta.",
            )
            await self._write(
                player,
                self._line(
                    player, "INFO", f"draw.private card={note}",
                    f"Você comprou: {note}.",
                ),
            )
            self._state.advance()
            return

        assert isinstance(move, int)
        card = self._state.hands[idx][move]
        chosen = ""
        if card.is_wild:
            chosen = await self._choose_color(player)
        played = self._state.play(idx, move, chosen)
        color = self._state.active_color
        await self._broadcast_event(
            f"play.card player={player.name} card={_card(played)} color={color}",
            f"{player.name} jogou {_card(played)}"
            + (f" → cor {color}" if played.is_wild else "")
            + ".",
        )
        if self._state.winner() is not None:
            return
        await self._apply_effect(played)

    async def _apply_effect(self, card: Card) -> None:
        two_players = sum(p.active for p in self._players) == 2
        if card.value == "reverse":
            self._state.direction *= -1
            self._state.advance(skip=two_players)
        elif card.value == "skip":
            self._state.advance(skip=True)
        elif card.value == "draw2":
            victim = self._state.next_index()
            self._state.draw(victim, 2)
            self._state.advance(skip=True)
        elif card.value == "wild4":
            victim = self._state.next_index()
            self._state.draw(victim, 4)
            self._state.advance(skip=True)
        else:
            self._state.advance()

    async def _get_move(self, player: _Player, idx: int) -> int | str | None:
        hand = self._state.hands[idx]
        while True:
            try:
                raw = (await player.transport.read_line()).strip().lower()
            except ConnectionError:
                return None
            if raw in ("q", "quit", "sair"):
                return None
            if raw in ("d", "draw", "comprar"):
                return "draw"
            if raw.isdigit():
                pos = int(raw) - 1
                if 0 <= pos < len(hand) and self._state.playable(hand[pos]):
                    return pos
            await self._write(
                player,
                self._line(
                    player, "WARN", "input.reject reason=invalid_play",
                    "Número de carta jogável, ou 'd' p/ comprar. 'q' sai.",
                ),
            )

    async def _choose_color(self, player: _Player) -> str:
        while True:
            await self._write(
                player,
                self._line(
                    player, "INFO", "input.await type=color",
                    "Escolha a cor (R/G/B/Y):",
                ),
            )
            try:
                raw = (await player.transport.read_line()).strip().upper()
            except ConnectionError:
                return COLORS[0]
            if raw in COLORS:
                return raw

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
                    f"[INFO ] {_ts()} service.start game=uno mode=multiplayer\r\n"
                )
            else:
                await p.transport.write(
                    "\r\n=== UNO MULTIPLAYER ===\r\n"
                    "Jogue carta da mesma cor ou valor. Coringa muda a cor.\r\n"
                    "Esvazie a mão para vencer.\r\n"
                )

        await asyncio.gather(*(send(p) for p in self._players))

    async def _broadcast_table(self) -> None:
        st = self._state
        turn = self._players[st.current].name
        counts = ", ".join(
            f"{p.name}={len(st.hands[i])}" for i, p in enumerate(self._players)
        )
        arrow = "→" if st.direction == 1 else "←"

        async def send(p: _Player) -> None:
            if p.stealth:
                await p.transport.write(
                    f"[INFO ] {_ts()} table.state top={_card(st.top)} "
                    f"color={st.active_color} dir={arrow} turn={turn} {counts}\r\n"
                )
            else:
                await p.transport.write(
                    "\r\n┌─ UNO ─────────────────────────┐\r\n"
                    f"  topo: {_card(st.top)}   cor: {st.active_color}   {arrow}\r\n"
                    f"  mãos: {counts}\r\n"
                    f"  vez: {turn}\r\n"
                    "└───────────────────────────────┘\r\n"
                )

        await asyncio.gather(*(send(p) for p in self._players))

    async def _show_hand(self, player: _Player) -> None:
        idx = self._players.index(player)
        hand = self._state.hands[idx]
        labels = [
            f"{i + 1}:{_card(c)}{'*' if self._state.playable(c) else ''}"
            for i, c in enumerate(hand)
        ]
        await self._write(
            player,
            self._line(
                player, "INFO", "hand.private " + " ".join(labels),
                "Sua mão: " + "  ".join(labels) + "\r\n  (* = jogável)",
            ),
        )

    async def _prompt(self, player: _Player) -> None:
        await self._write(
            player,
            self._line(
                player, "INFO", "input.await type=card",
                "▶ Sua vez! Número da carta ou 'd' p/ comprar:",
            ),
        )

    async def _broadcast_event(self, log_body: str, pretty: str) -> None:
        async def send(p: _Player) -> None:
            await p.transport.write(self._line(p, "INFO", log_body, pretty))

        await asyncio.gather(*(send(p) for p in self._players))

    async def _broadcast_end(self) -> None:
        win = self._state.winner()
        name = self._players[win].name if win is not None else ""

        async def send(p: _Player) -> None:
            if p.stealth:
                await p.transport.write(
                    f"[INFO ] {_ts()} round.result outcome=win winner={name or '-'}\r\n"
                )
            elif name:
                await p.transport.write(f"\r\n🏆 {name} venceu o Uno!\r\n")
            else:
                await p.transport.write("\r\nPartida encerrada.\r\n")

        await asyncio.gather(*(send(p) for p in self._players))
