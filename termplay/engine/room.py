"""Gerenciamento de salas para sessões multiplayer."""

from __future__ import annotations

import asyncio
import random
import string
import uuid
from dataclasses import dataclass, field
from typing import ClassVar

from termplay.engine.interfaces import ITransportAdapter


@dataclass
class RoomPlayer:
    """Jogador registrado em uma sala."""

    name: str
    transport: ITransportAdapter
    stealth: bool = False
    is_bot: bool = False
    input_queue: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    token: str = field(default_factory=lambda: uuid.uuid4().hex)
    connected: bool = True


@dataclass
class Room:
    """Sala de jogo multiplayer com canal de chat e coordenação de estado."""

    code: str
    host: RoomPlayer
    game: str = "uno"
    rules: object = "standard"  # preset name or a flags dict (Uno rule variants)
    max_players: int = 8
    players: list[RoomPlayer] = field(default_factory=list)
    ready: asyncio.Event = field(default_factory=asyncio.Event)
    game_complete: asyncio.Event = field(default_factory=asyncio.Event)

    def add_player(self, player: RoomPlayer) -> bool:
        if self.is_full:
            return False
        self.players.append(player)
        return True

    def remove_player(self, player: RoomPlayer) -> None:
        if player in self.players:
            self.players.remove(player)

    async def broadcast(self, text: str) -> None:
        await asyncio.gather(
            *(p.transport.write(text) for p in self.players if p.connected)
        )

    def find_by_token(self, token: str) -> RoomPlayer | None:
        return next((p for p in self.players if p.token == token), None)

    @property
    def is_full(self) -> bool:
        return len(self.players) >= self.max_players

    @property
    def player_count(self) -> int:
        return len(self.players)


class RoomManager:
    """Registro global de salas ativas — singleton baseado em variável de classe."""

    _rooms: ClassVar[dict[str, Room]] = {}

    @classmethod
    def create(
        cls,
        host: RoomPlayer,
        max_players: int = 8,
        game: str = "uno",
        rules: object = "standard",
    ) -> Room:
        code = cls._gen_code()
        room = Room(
            code=code, host=host, game=game, rules=rules, max_players=max_players
        )
        room.players.append(host)
        cls._rooms[code] = room
        return room

    @classmethod
    def get(cls, code: str) -> Room | None:
        return cls._rooms.get(code.upper())

    @classmethod
    def remove(cls, code: str) -> None:
        cls._rooms.pop(code.upper(), None)

    @classmethod
    def clear(cls) -> None:
        cls._rooms.clear()

    @classmethod
    def find_player(cls, token: str) -> tuple[Room, RoomPlayer] | None:
        """Locate a player by session token across every active room."""
        for room in cls._rooms.values():
            player = room.find_by_token(token)
            if player is not None:
                return room, player
        return None

    @classmethod
    def first(cls) -> Room | None:
        """Retorna a primeira sala disponível (para servidores P2P com uma sala)."""
        return next(iter(cls._rooms.values()), None)

    @classmethod
    def _gen_code(cls) -> str:
        chars = string.ascii_uppercase + string.digits
        while True:
            code = "".join(random.choices(chars, k=4))
            if code not in cls._rooms:
                return code
