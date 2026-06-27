"""Hangman (Forca) plugin — registers solo IGame and multiplayer factory."""

from __future__ import annotations

from typing_extensions import override

from termplay.engine.game import IGame
from termplay.engine.interfaces import ITransportAdapter
from termplay.engine.multiplayer import MultiplayerRegistry
from termplay.engine.registry import GameRegistry
from termplay.games.hangman.controller import HangmanController


@GameRegistry.register
class Hangman(IGame):
    """Forca — guess the hidden word before the drawing completes."""

    @property
    @override
    def name(self) -> str:
        return "Forca"

    @property
    @override
    def description(self) -> str:
        return "Adivinhe a palavra antes de ser enforcado"

    @override
    async def run(self, transport: ITransportAdapter) -> None:
        controller = HangmanController([transport], names=["Você"])
        await controller.run()

    @override
    async def show_help(self, transport: ITransportAdapter) -> None:
        await transport.write(
            "\r\nFORCA\r\n"
            "Digite uma letra para adivinhar, ou a palavra inteira.\r\n"
            "6 erros e o boneco é enforcado. 'q' para sair.\r\n"
            "Pressione Enter para voltar..."
        )
        await transport.read_line()


MultiplayerRegistry.register(
    "forca", lambda t, n, s, rules="standard": HangmanController(t, n, s)
)
