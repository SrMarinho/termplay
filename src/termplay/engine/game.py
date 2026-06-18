"""Interface IGame - contrato que todo jogo plugin implementa."""

from __future__ import annotations

from abc import ABC, abstractmethod

from termplay.engine.interfaces import ITransportAdapter


class IGame(ABC):
    """Contrato abstrato para jogos.

    Princípio: Open/Closed (OCP) - novos jogos estendem sem modificar a engine.
    Padrão: Strategy/Game Pattern.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome do jogo (ex: "Blackjack")."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Descrição curta do jogo."""

    @abstractmethod
    async def run(self, transport: ITransportAdapter) -> None:
        """Executa o jogo até o cliente desconectar ou desistir."""

    @abstractmethod
    async def show_help(self, transport: ITransportAdapter) -> None:
        """Mostra instruções do jogo."""
