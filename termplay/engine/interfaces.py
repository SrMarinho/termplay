"""Interface ITransportAdapter - contrato para transporte de I/O."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ITransportAdapter(ABC):
    """Contrato abstrato para adaptadores de transporte.

    Implementações concretas: TCPAdapter, SSHAdapter, etc.
    Princípio: Dependency Inversion (DIP).
    """

    @abstractmethod
    async def write(self, text: str) -> None:
        """Envia texto para o cliente."""

    @abstractmethod
    async def read_line(self) -> str:
        """Lê uma linha do cliente."""

    @abstractmethod
    async def read_char(self) -> str:
        """Lê um caractere do cliente."""

    @abstractmethod
    async def close(self) -> None:
        """Fecha a conexão."""

    @property
    @abstractmethod
    def width(self) -> int:
        """Largura do terminal do cliente."""
