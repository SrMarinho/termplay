"""UnoSoloGame — Uno single-player: human (idx 0) vs CPU bots."""

from __future__ import annotations

import asyncio
from collections import Counter

from typing_extensions import override

from termplay.engine.game import IGame
from termplay.engine.interfaces import ITransportAdapter
from termplay.games.uno.display import render_log_view
from termplay.games.uno.state import COLORS, Card, UnoState

_BOT_NAMES = ["Bot 1", "Bot 2", "Bot 3"]
_THINK_DELAY = 0.6  # seconds bots "think"


def _bot_color(hand: list[Card]) -> str:
    non_wild = [c.color for c in hand if not c.is_wild]
    if not non_wild:
        return COLORS[0]
    return Counter(non_wild).most_common(1)[0][0]


def _bot_move(state: UnoState, idx: int) -> int | str:
    """Return card index to play, or 'draw'."""
    hand = state.hands[idx]
    for i, card in enumerate(hand):
        if state.playable(card):
            return i
    return "draw"


class UnoSoloGame(IGame):
    """Uno against 3 CPU bots, rendered as server-log lines."""

    @property
    @override
    def name(self) -> str:
        return "Uno"

    @property
    @override
    def description(self) -> str:
        return "Uno contra bots (solo)"

    @override
    async def show_help(self, transport: ITransportAdapter) -> None:
        await transport.write(
            "\r\nUNO — Solo\r\n"
            "Digite o número da carta para jogar, 'd' para comprar, 'q' para sair.\r\n"
            "Cartas marcadas com * são jogáveis.\r\n"
            "Pressione Enter para voltar..."
        )
        await transport.read_line()

    @override
    async def run(self, transport: ITransportAdapter) -> None:
        names = ["Você"] + _BOT_NAMES
        state = UnoState.new(len(names))
        message = ""

        while state.winner() is None:
            idx = state.current
            is_human = idx == 0

            await transport.write(
                render_log_view(state, names, 0, is_active=is_human, message=message)
            )
            message = ""

            if is_human:
                move = await self._human_move(transport, state)
                if move is None:
                    return
            else:
                await asyncio.sleep(_THINK_DELAY)
                move = _bot_move(state, idx)

            message = self._apply_move(state, names, idx, move)

        winner = state.winner()
        name = names[winner] if winner is not None else "?"
        await transport.write(
            render_log_view(state, names, 0, is_active=False, message=f"winner={name}")
        )
        await transport.write(
            f"\r\n{'Você venceu!' if winner == 0 else f'{name} venceu.'}\r\n"
            "Pressione Enter para voltar..."
        )
        await transport.read_line()

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _human_move(
        self, transport: ITransportAdapter, state: UnoState
    ) -> int | str | None:
        hand = state.hands[0]
        while True:
            try:
                raw = (await transport.read_line()).strip().lower()
            except ConnectionError:
                return None
            if raw in ("q", "quit", "sair"):
                return None
            if raw in ("d", "draw", "comprar"):
                return "draw"
            if raw.isdigit():
                pos = int(raw) - 1
                if 0 <= pos < len(hand) and state.playable(hand[pos]):
                    return pos
            await transport.write(
                "[WARN ] Entrada inválida. Número da carta (*), 'd' comprar, 'q' sair.\r\n"
            )

    def _apply_move(
        self, state: UnoState, names: list[str], idx: int, move: int | str
    ) -> str:
        name = names[idx]
        if move == "draw":
            drawn = state.draw(idx, 1)
            if drawn and state.playable(drawn[0]):
                card = drawn[0]
                color = _bot_color(state.hands[idx]) if card.is_wild else ""
                state.play(idx, len(state.hands[idx]) - 1, color)
                state.advance()
                return f"{name} comprou e jogou {card.color}:{card.value}"
            state.advance()
            return f"{name} comprou uma carta"

        assert isinstance(move, int)
        card = state.hands[idx][move]
        chosen = _bot_color(state.hands[idx]) if card.is_wild else ""
        played = state.play(idx, move, chosen)
        suffix = f" → {chosen}" if played.is_wild else ""
        msg = f"{name} jogou {played.color}:{played.value}{suffix}"
        if state.winner() is not None:
            return msg
        self._apply_effect(state, played)
        return msg

    def _apply_effect(self, state: UnoState, card: Card) -> None:
        two_active = sum(1 for h in state.hands if h) == 2
        if card.value == "reverse":
            state.direction *= -1
            state.advance(skip=two_active)
        elif card.value == "skip":
            state.advance(skip=True)
        elif card.value in ("draw2", "wild4"):
            victim = state.next_index()
            count = 2 if card.value == "draw2" else 4
            state.draw(victim, count)
            state.advance(skip=True)
        else:
            state.advance()
