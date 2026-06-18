"""Tic-tac-toe (Velha) plugin — registers solo IGame and multiplayer factory."""

from __future__ import annotations

from typing_extensions import override

from termplay.engine.game import IGame
from termplay.engine.interfaces import ITransportAdapter
from termplay.engine.multiplayer import MultiplayerRegistry
from termplay.engine.registry import GameRegistry
from termplay.games.tictactoe.controller import TicTacToeController


@GameRegistry.register
class TicTacToe(IGame):
    """Velha — classic 3x3 tic-tac-toe for two players."""

    @property
    @override
    def name(self) -> str:
        return "Velha"

    @property
    @override
    def description(self) -> str:
        return "Jogo da velha 3x3 para dois jogadores"

    @override
    async def run(self, transport: ITransportAdapter) -> None:
        await transport.write(
            "\r\nVelha precisa de 2 jogadores. Use o modo multiplayer.\r\n"
            "Pressione Enter para voltar..."
        )
        await transport.read_line()

    @override
    async def show_help(self, transport: ITransportAdapter) -> None:
        await transport.write(
            "\r\nVELHA\r\n"
            "Dois jogadores ('X' e 'O') alternam marcando casas de 1 a 9.\r\n"
            "Primeiro a alinhar três vence. 'q' para sair.\r\n"
            "Pressione Enter para voltar..."
        )
        await transport.read_line()


MultiplayerRegistry.register(
    "velha", lambda t, n, s: TicTacToeController(t, n, s)
)
