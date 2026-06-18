"""Discovery de salas LAN via UDP broadcast.

Separado de qualquer UI — só lógica de rede.
RoomBroadcaster: enviado pelo servidor.
RoomDiscoverer: usado pelo cliente para listar salas disponíveis.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import socket
import time
from dataclasses import dataclass, field
from typing import Any

DISCOVERY_PORT = 4444
_BROADCAST_INTERVAL = 2.0
_ROOM_TTL = 6.0


@dataclass
class DiscoveredRoom:
    ip: str
    port: int
    host: str
    game: str
    players: int
    max_players: int
    status: str
    seen_at: float = field(default_factory=time.monotonic)


class RoomBroadcaster:
    """Envia beacons UDP a cada 2s para a subnet local.

    Executar como asyncio.Task; cancelar para parar.
    """

    def __init__(self) -> None:
        self._info: dict[str, object] = {}
        self._running = False

    def update(self, **fields: object) -> None:
        self._info.update(fields)

    async def run(self) -> None:
        self._running = True
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setblocking(False)
            loop = asyncio.get_running_loop()
            while self._running:
                if self._info:
                    payload = json.dumps(self._info, ensure_ascii=False).encode()
                    with contextlib.suppress(OSError):
                        await loop.sock_sendto(
                            sock, payload, ("255.255.255.255", DISCOVERY_PORT)
                        )
                await asyncio.sleep(_BROADCAST_INTERVAL)

    def stop(self) -> None:
        self._running = False


class _UDPDiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, rooms: dict[str, DiscoveredRoom]) -> None:
        self._rooms = rooms

    def datagram_received(self, data: bytes, addr: tuple[Any, ...]) -> None:
        ip = str(addr[0])
        try:
            msg = json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return
        if not isinstance(msg, dict):
            return
        self._rooms[ip] = DiscoveredRoom(
            ip=ip,
            port=int(msg.get("port", 4443)),
            host=str(msg.get("host", "?")),
            game=str(msg.get("game", "?")),
            players=int(msg.get("players", 0)),
            max_players=int(msg.get("max_players", 4)),
            status=str(msg.get("status", "waiting")),
        )

    def error_received(self, exc: Exception) -> None:
        pass

    def connection_lost(self, exc: Exception | None) -> None:
        pass


class RoomDiscoverer:
    """Ouve beacons UDP e mantém lista de salas ativas (TTL 6s)."""

    def __init__(self) -> None:
        self._rooms: dict[str, DiscoveredRoom] = {}
        self._transport: asyncio.BaseTransport | None = None

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: _UDPDiscoveryProtocol(self._rooms),
            local_addr=("0.0.0.0", DISCOVERY_PORT),
            allow_broadcast=True,
            reuse_port=hasattr(socket, "SO_REUSEPORT"),
        )

    async def stop(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    def rooms(self) -> list[DiscoveredRoom]:
        cutoff = time.monotonic() - _ROOM_TTL
        expired = [ip for ip, r in self._rooms.items() if r.seen_at < cutoff]
        for ip in expired:
            del self._rooms[ip]
        return list(self._rooms.values())
