from typing_extensions import override

from termplay.engine.game import IGame
from termplay.engine.interfaces import ITransportAdapter
from termplay.engine.multiplayer import MultiplayerRegistry
from termplay.engine.registry import GameRegistry
from termplay.games.truco.application.controller import TrucoController
from termplay.games.truco.ruleset import TrucoRuleset


@GameRegistry.register
class Truco(IGame):
    @property
    @override
    def name(self) -> str:
        return "Truco"

    @property
    @override
    def description(self) -> str:
        return "Truco Paulista (1v1 ou 2v2) com envite completo"

    @override
    async def run(self, transport: ITransportAdapter) -> None:
        await transport.write("Truco requer partida multijogador. Volte ao lobby.")
        await transport.read_line()

    @override
    async def show_help(self, transport: ITransportAdapter) -> None:
        help_text = (
            "=== TRUCO PAULISTA ===\n"
            "Baralho de 40 cartas (sem 8 e 9).\n"
            "Vira: carta virada determina a manilha (rank seguinte).\n"
            "Manilhas: Zap(C) > Copas(H) > Espadilha(S) > Escopeta(D).\n"
            "Força: 3 > 2 > A > K > J > Q > 7 > 6 > 5 > 4.\n"
            "Rodada: 3 levadas, melhor de 3 vence.\n"
            "Pontos: 1pt normal | 3/6/9/12 com envite.\n"
            "Primeiro a 12 pts vence.\n"
            "Comandos: 1-3 jogar carta | t truco | a aceitar | c correr | r aumentar\n"
        )
        await transport.write(help_text)
        await transport.read_line()


MultiplayerRegistry.register(
    "truco",
    lambda t, n, s, rules: TrucoController(t, n, s, TrucoRuleset.from_spec(rules)),
)
