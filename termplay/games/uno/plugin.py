"""Uno plugin — registers solo IGame placeholder and multiplayer factory."""

from __future__ import annotations

from typing_extensions import override

from termplay.engine.game import IGame
from termplay.engine.interfaces import ITransportAdapter
from termplay.engine.multiplayer import MultiplayerRegistry
from termplay.engine.registry import GameRegistry
from termplay.games.uno.controller import UnoController


@GameRegistry.register
class Uno(IGame):
    """Uno — match color or value, empty your hand to win."""

    @property
    @override
    def name(self) -> str:
        return "Uno"

    @property
    @override
    def description(self) -> str:
        return "Clássico jogo de cartas Uno (2+ jogadores)"

    @override
    async def run(self, transport: ITransportAdapter) -> None:
        await transport.write(
            "\r\nUno precisa de 2+ jogadores. Use o modo multiplayer.\r\n"
            "Pressione Enter para voltar..."
        )
        await transport.read_line()

    @override
    async def show_help(self, transport: ITransportAdapter) -> None:
        await transport.write(
            "\r\nUNO\r\n"
            "Jogue uma carta da mesma cor ou valor do topo, ou um coringa.\r\n"
            "skip pula, reverse inverte, draw2/wild4 forçam compras.\r\n"
            "Esvazie a mão para vencer. 'd' compra, 'q' sai.\r\n"
            "Pressione Enter para voltar..."
        )
        await transport.read_line()


MultiplayerRegistry.register("uno", lambda t, n, s: UnoController(t, n, s))
