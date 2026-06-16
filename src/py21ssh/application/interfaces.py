"""Interfaces da camada de aplicação — contratos de transporte e display."""

from __future__ import annotations

from typing import Protocol


class ITransportAdapter(Protocol):
    """Contrato para transporte de I/O.

    Qualquer implementação (TCP, SSH, pipe) deve seguir
    este protocolo. O GameController depende apenas disso,
    nunca de detalhes de socket.
    """

    async def write(self, text: str) -> None:
        """Envia texto (com ANSI) para o cliente."""
        ...

    async def read_line(self) -> str:
        """Lê uma linha de entrada do cliente."""
        ...

    async def read_char(self) -> str:
        """Lê um caractere do cliente (sem esperar Enter)."""
        ...

    @property
    def terminal_width(self) -> int:
        """Largura do terminal do cliente (cols)."""
        ...

    async def close(self) -> None:
        """Fecha a conexão."""
        ...
