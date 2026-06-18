"""Servidor TCP da engine termplay — protocolo JSON puro.

O cliente é o TUI Python (Textual). O servidor não renderiza menus em texto:
apenas troca mensagens JSON (ver termplay.engine.protocol). Salas multiplayer são
coordenadas por RoomManager; o jogo em si é renderizado como ANSI dentro de
mensagens game_render.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from termplay.engine.protocol import (
    ACTION_CHAT,
    ACTION_CREATE_ROOM,
    ACTION_GAME_INPUT,
    ACTION_JOIN_ROOM,
    ACTION_LEAVE,
    ACTION_START_GAME,
    TYPE_CHAT,
    TYPE_ERROR,
    TYPE_GAME_OVER,
    TYPE_GAME_START,
    TYPE_ROOM_CREATED,
    TYPE_ROOM_JOINED,
    TYPE_ROOM_STATE,
)
from termplay.engine.protocol_adapter import ProtocolServerAdapter
from termplay.engine.room import Room, RoomManager, RoomPlayer

if TYPE_CHECKING:
    from termplay.engine.interfaces import ITransportAdapter

logger = logging.getLogger(__name__)

MIN_PLAYERS = 2


class TermPlayServer:
    """Servidor TCP que coordena salas multiplayer via protocolo JSON."""

    def __init__(self, host: str = "0.0.0.0", port: int = 4443) -> None:
        self.host = host
        self.port = port
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        logger.info(f"Servidor termplay rodando em {self.host}:{self.port}")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        logger.info(f"Conexão aceita de {peer}")
        adapter = ProtocolServerAdapter(reader, writer)
        try:
            first = await adapter.recv_control()
            if first is None:
                return
            action = first.get("action")
            if action == ACTION_CREATE_ROOM:
                await self._host_flow(adapter, str(first.get("name") or "Host"))
            elif action == ACTION_JOIN_ROOM:
                await self._guest_flow(
                    adapter,
                    str(first.get("name") or "Player"),
                    str(first.get("code") or "").upper(),
                )
            else:
                await adapter.send_control(
                    type=TYPE_ERROR, message="Ação inválida", fatal=True
                )
        except Exception:
            logger.exception(f"Erro na sessão de {peer}")
        finally:
            await adapter.close()
            logger.info(f"Conexão fechada para {peer}")

    # ── Host ─────────────────────────────────────────────────────────────────

    async def _host_flow(self, adapter: ProtocolServerAdapter, name: str) -> None:
        player = RoomPlayer(name=name, transport=adapter)
        room = RoomManager.create(player)
        await adapter.send_control(type=TYPE_ROOM_CREATED, code=room.code, you=name)
        await self._broadcast_state(room)

        while True:
            msg = await adapter.recv_control()
            if msg is None:
                RoomManager.remove(room.code)
                await self._broadcast_state(room)
                return
            action = msg.get("action")
            if action == ACTION_START_GAME:
                if room.player_count >= MIN_PLAYERS:
                    break
                await adapter.send_control(
                    type=TYPE_ERROR,
                    message=f"Mínimo {MIN_PLAYERS} jogadores para iniciar.",
                )
            elif action == ACTION_CHAT:
                await self._broadcast_chat(room, name, str(msg.get("text") or ""))

        room.ready.set()
        await self._broadcast(room, type=TYPE_GAME_START)
        relay = asyncio.create_task(self._relay(adapter, room, name))
        try:
            await self._run_controller(room)
        finally:
            await relay
            RoomManager.remove(room.code)

    # ── Guest ────────────────────────────────────────────────────────────────

    async def _guest_flow(
        self, adapter: ProtocolServerAdapter, name: str, code: str
    ) -> None:
        room = RoomManager.get(code)
        if room is None:
            await adapter.send_control(
                type=TYPE_ERROR, message=f"Sala '{code}' não encontrada.", fatal=True
            )
            return
        if room.is_full:
            await adapter.send_control(
                type=TYPE_ERROR, message="Sala cheia.", fatal=True
            )
            return

        player = RoomPlayer(name=name, transport=adapter)
        room.add_player(player)
        await adapter.send_control(type=TYPE_ROOM_JOINED, code=room.code, you=name)
        await self._broadcast_state(room)

        while not room.ready.is_set():
            try:
                msg = await asyncio.wait_for(adapter.recv_control(), timeout=0.3)
            except TimeoutError:
                continue
            if msg is None:
                room.remove_player(player)
                await self._broadcast_state(room)
                return
            action = msg.get("action")
            if action == ACTION_LEAVE:
                room.remove_player(player)
                await self._broadcast_state(room)
                return
            if action == ACTION_CHAT:
                await self._broadcast_chat(room, name, str(msg.get("text") or ""))

        relay = asyncio.create_task(self._relay(adapter, room, name))
        await room.game_complete.wait()
        await relay

    # ── Jogo ─────────────────────────────────────────────────────────────────

    async def _run_controller(self, room: Room) -> None:
        from termplay.games.blackjack.application.multiplayer_controller import (
            MultiplayerGameController,
        )
        from termplay.games.blackjack.domain.rules import BlackjackRules

        transports: list[ITransportAdapter] = [p.transport for p in room.players]
        names = [p.name for p in room.players]
        controller = MultiplayerGameController(
            transports, BlackjackRules(), names=names
        )
        try:
            await controller.run()
        finally:
            room.game_complete.set()
            await self._broadcast(room, type=TYPE_GAME_OVER)

    async def _relay(
        self, adapter: ProtocolServerAdapter, room: Room, name: str
    ) -> None:
        """Lê mensagens do socket durante o jogo, roteando inputs para a queue."""
        while not room.game_complete.is_set():
            try:
                msg = await asyncio.wait_for(adapter.recv_control(), timeout=0.2)
            except TimeoutError:
                continue
            if msg is None:
                break
            action = msg.get("action")
            if action == ACTION_GAME_INPUT:
                await adapter.input_queue.put(str(msg.get("text") or ""))
            elif action == ACTION_CHAT:
                await self._broadcast_chat(room, name, str(msg.get("text") or ""))

    # ── Broadcast helpers ────────────────────────────────────────────────────

    async def _broadcast(self, room: Room, **msg: object) -> None:
        async def send(player: RoomPlayer) -> None:
            transport = player.transport
            if isinstance(transport, ProtocolServerAdapter):
                with contextlib.suppress(Exception):
                    await transport.send_control(**msg)

        await asyncio.gather(*(send(p) for p in room.players))

    async def _broadcast_state(self, room: Room) -> None:
        await self._broadcast(
            room,
            type=TYPE_ROOM_STATE,
            code=room.code,
            host=room.host.name,
            players=[p.name for p in room.players],
            player_count=room.player_count,
            min_players=MIN_PLAYERS,
            max_players=room.max_players,
            can_start=room.player_count >= MIN_PLAYERS,
        )

    async def _broadcast_chat(self, room: Room, name: str, text: str) -> None:
        if text:
            await self._broadcast(room, type=TYPE_CHAT, name=name, text=text)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Servidor parado")
