"""Tic-tac-toe (Velha) plugin — registers solo IGame and multiplayer factory."""

from __future__ import annotations

from typing_extensions import override

from termplay.engine.game import IGame
from termplay.engine.interfaces import ITransportAdapter
from termplay.engine.multiplayer import MultiplayerRegistry
from termplay.engine.registry import GameRegistry
from termplay.games.tictactoe.bot import VelhaBotTransportAdapter
from termplay.games.tictactoe.controller import TicTacToeController


@GameRegistry.register
class TicTacToe(IGame):
    """Velha — classic 3x3 tic-tac-toe."""

    @property
    @override
    def name(self) -> str:
        return "Velha"

    @property
    @override
    def description(self) -> str:
        return "Jogo da velha 3x3 — solo ou multiplayer"

    @override
    async def run(self, transport: ITransportAdapter) -> None:
        # Solo play is handled by VelhaScreen (bypasses this transport).
        # This path is hit only if game is launched via raw GameScreen (legacy).
        await transport.write(
            '{"v":"velha.state","cells":[" "," "," "," "," "," "," "," "," "],'
            '"turn":"","phase":"over","your_mark":"","winner":null}\r\n'
        )

    @override
    async def show_help(self, transport: ITransportAdapter) -> None:
        await transport.write(
            '{"v":"velha.state","cells":[" "," "," "," "," "," "," "," "," "],'
            '"turn":"","phase":"over","your_mark":"","winner":null}\r\n'
        )


def _make_controller(
    transports: list[ITransportAdapter],
    names: list[str] | None,
    stealth_flags: list[bool] | None,
) -> TicTacToeController:
    all_transports = list(transports)
    all_names = list(names) if names else [f"Player {i+1}" for i in range(len(transports))]
    while len(all_transports) < 2:
        all_transports.append(VelhaBotTransportAdapter("hard"))
        all_names.append(f"Bot {len(all_transports)}")
    return TicTacToeController(all_transports, all_names, stealth_flags)


MultiplayerRegistry.register("velha", _make_controller)
