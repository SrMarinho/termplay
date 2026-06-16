"""Interfaces do domínio — contratos que a camada de regras deve implementar."""

from __future__ import annotations

from enum import Enum, auto
from typing import Protocol

from py21ssh.domain.deck import Deck
from py21ssh.domain.hand import Hand


class RoundResult(Enum):
    """Resultado de uma rodada."""

    WIN = auto()
    LOSE = auto()
    PUSH = auto()
    BLACKJACK = auto()


class PlayerAction(Enum):
    """Ações que o jogador pode tomar."""

    HIT = auto()
    STAND = auto()
    DOUBLE = auto()
    QUIT = auto()


class IGameRules(Protocol):
    """Contrato para as regras do Blackjack.

    Qualquer implementação concreta (BlackjackRules, variações)
    deve respeitar este protocolo.
    """

    def initial_deal(self, deck: Deck) -> tuple[Hand, Hand]:
        """Distribui 2 cartas para jogador e dealer."""
        ...

    def player_hit(self, hand: Hand, deck: Deck) -> None:
        """Adiciona uma carta à mão do jogador."""
        ...

    def dealer_play(self, hand: Hand, deck: Deck) -> None:
        """Jogada automática do dealer (compra até 17+)."""
        ...

    def resolve(self, player: Hand, dealer: Hand) -> RoundResult:
        """Determina o resultado final da rodada."""
        ...
