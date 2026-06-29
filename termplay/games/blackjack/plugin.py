"""Plugin Blackjack - implementa IGame.

Padrão: Strategy Pattern - implementa estratégia concreta de jogo.
"""

from __future__ import annotations

from typing_extensions import override

from termplay.engine.game import IGame
from termplay.engine.interfaces import ITransportAdapter
from termplay.engine.multiplayer import MultiplayerRegistry
from termplay.engine.registry import GameRegistry
from termplay.games.blackjack.application.game_controller import GameController
from termplay.games.blackjack.application.versus_controller import (
    BlackjackVersusController,
)
from termplay.games.blackjack.display.renderer import RichRenderer
from termplay.games.blackjack.domain.rules import BlackjackRules


@GameRegistry.register
class Blackjack(IGame):
    """Jogo de Blackjack (21) como plugin da engine termplay.

    Princípio: Open/Closed (OCP) - estende IGame sem modificar a engine.
    """

    @property
    @override
    def name(self) -> str:
        return "Blackjack"

    @property
    @override
    def description(self) -> str:
        return "Jogo clássico de 21 contra o dealer"

    @override
    async def run(self, transport: ITransportAdapter) -> None:
        """Executa o jogo de Blackjack."""
        renderer = RichRenderer(transport)
        rules = BlackjackRules()
        controller = GameController(transport, rules, renderer)

        await controller.run()

    @override
    async def show_help(self, transport: ITransportAdapter) -> None:
        """Mostra instruções do Blackjack."""
        help_text = (
            "\r\n"
            "🃏 BLACKJACK (21) - Regras\r\n"
            "═══════════════════════════\r\n"
            "\r\n"
            "Objetivo: Chegar o mais perto de 21 sem estourar\r\n"
            "Cartas: A=1 ou 11, J/Q/K=10, demais=valor numérico\r\n"
            "\r\n"
            "Comandos:\r\n"
            "  1/h/Hit    - Comprar mais uma carta\r\n"
            "  2/s/Stand  - Parar e revelar cartas\r\n"
            "  3/q/Quit   - Desistir e sair\r\n"
            "\r\n"
            "Blackjack natural (A + 10/J/Q/K) paga 3:2\r\n"
            "Dealer compra até 17\r\n"
            "\r\n"
            "Pressione Enter para voltar..."
        )
        await transport.write(help_text)
        await transport.read_line()


# Multiplayer rooms use the player-vs-player versus controller (no house dealer).
MultiplayerRegistry.register(
    "blackjack",
    lambda t, n, s, rules="": BlackjackVersusController(t, n, s, rules),
)
