"""Adaptador TCP para ITransportAdapter.

Padrão: Adapter Pattern.
Responsabilidade: Adaptar asyncio.StreamReader/Writer para ITransportAdapter.
"""

from __future__ import annotations

import asyncio
import logging

from typing_extensions import override

from termplay.engine.interfaces import ITransportAdapter

logger = logging.getLogger(__name__)


class TCPAdapter(ITransportAdapter):
    """Adaptador TCP que implementa ITransportAdapter.

    Princípio: Adapter Pattern - adapta Stream API para nossa interface.
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        encoding: str = "utf-8",
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._encoding = encoding
        self._closed = False

    @override
    async def write(self, text: str) -> None:
        """Envia texto para o cliente."""
        if self._closed:
            return

        try:
            data = text.encode(self._encoding)
            self._writer.write(data)
            await self._writer.drain()
        except ConnectionError:
            logger.warning("Conexão perdida durante write")
            self._closed = True

    @override
    async def read_line(self) -> str:
        """Lê uma linha do cliente."""
        if self._closed:
            raise ConnectionError("Transporte fechado")

        try:
            data = await self._reader.readline()
            if not data:
                self._closed = True
                raise ConnectionError("Cliente desconectou")
            return data.decode(self._encoding).strip()
        except ConnectionError:
            self._closed = True
            raise

    @override
    async def read_char(self) -> str:
        """Lê um caractere do cliente."""
        if self._closed:
            raise ConnectionError("Transporte fechado")

        try:
            data = await self._reader.read(1)
            if not data:
                self._closed = True
                raise ConnectionError("Cliente desconectou")
            return data.decode(self._encoding)
        except ConnectionError:
            self._closed = True
            raise

    @override
    async def close(self) -> None:
        """Fecha a conexão."""
        if not self._closed:
            self._closed = True
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                logger.debug("Erro ao fechar writer", exc_info=True)

    @property
    @override
    def width(self) -> int:
        """Largura do terminal (padrão 80 para TCP)."""
        return 80


def create_tcp_adapter(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> TCPAdapter:
    """Factory para criar TCPAdapter.

    Padrão: Factory Method.
    """
    return TCPAdapter(reader, writer)
