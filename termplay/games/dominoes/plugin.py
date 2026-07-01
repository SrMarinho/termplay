"""Dominoes plugin — registers solo IGame (vs bot) and multiplayer factory."""

from __future__ import annotations

from typing_extensions import override

from termplay.engine.game import IGame
from termplay.engine.interfaces import ITransportAdapter
from termplay.engine.multiplayer import MultiplayerRegistry
from termplay.engine.registry import GameRegistry
from termplay.games.dominoes.application.bot_transport import (
    DominoesBotTransportAdapter,
)
from termplay.games.dominoes.application.controller import DominoesController


@GameRegistry.register
class Dominoes(IGame):
    """Dominó — empty your hand first on the double-six set."""

    @property
    @override
    def name(self) -> str:
        return "Domino"

    @property
    @override
    def description(self) -> str:
        return "Encaixe as pedras e bata primeiro"

    @override
    async def run(self, transport: ITransportAdapter) -> None:
        controller = DominoesController(
            [transport, DominoesBotTransportAdapter("Bot")],
            names=["Você", "Bot"],
        )
        await controller.run()

    @override
    async def show_help(self, transport: ITransportAdapter) -> None:
        await transport.write(
            "\r\nDOMINÓ\r\n"
            "Encaixe uma pedra em uma das pontas da mesa.\r\n"
            "Digite o número da pedra (▶ marca as jogáveis); adicione 'e'\r\n"
            "para a ponta esquerda (ex.: '3 e'). Sem jogada, você compra do\r\n"
            "dorme automaticamente. Bater = ficar sem pedras. 'q' sai.\r\n"
            "Pressione Enter para voltar..."
        )
        await transport.read_line()


MultiplayerRegistry.register(
    "domino", lambda t, n, s, rules="standard": DominoesController(t, n, s)
)
