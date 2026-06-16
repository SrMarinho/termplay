"""IDisplayRenderer — contrato para renderização da interface."""

from __future__ import annotations

from typing import Protocol

from py21ssh.domain.hand import Hand
from py21ssh.domain.interfaces import RoundResult


class IDisplayRenderer(Protocol):
    """Contrato para renderização visual do jogo."""

    def welcome(self) -> str:
        """Tela inicial."""
        ...

    def table(
        self,
        player_hand: Hand,
        dealer_hand: Hand,
        balance: int,
        bet: int,
        reveal_dealer: bool = False,
        doubled: bool = False,
    ) -> str:
        """Mesa do jogo com cartas e valores."""
        ...

    def bet_prompt(self, balance: int) -> str:
        """Prompt de aposta."""
        ...

    def action_prompt(self, hand: Hand, bet: int) -> str:
        """Prompt de ações disponíveis."""
        ...

    def result(self, result: RoundResult, bet: int, balance: int) -> str:
        """Tela de resultado da rodada."""
        ...

    def bust(self) -> str:
        """Mensagem de estouro."""
        ...

    def goodbye(self, balance: int) -> str:
        """Tela de despedida."""
        ...

    def error(self, message: str) -> str:
        """Mensagem de erro."""
        ...

    def history(self, balance: int) -> str:
        """Histórico / saldo atual."""
        ...

    def prompt(self, message: str) -> str:
        """Prompt genérico."""
        ...
