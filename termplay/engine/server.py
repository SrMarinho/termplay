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

from termplay.engine.discovery import RoomBroadcaster
from termplay.engine.protocol import (
    ACTION_ADD_BOT,
    ACTION_CHAT,
    ACTION_CREATE_ROOM,
    ACTION_GAME_INPUT,
    ACTION_JOIN_ROOM,
    ACTION_KICK,
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

    def __init__(
        self, host: str = "0.0.0.0", port: int = 4443, game_name: str = "blackjack"
    ) -> None:
        self.host = host
        self.port = port
        self._game_name = game_name
        self._server: asyncio.Server | None = None
        self._broadcaster = RoomBroadcaster()
        self._broadcast_task: asyncio.Task[None] | None = None
        self._clients: set[asyncio.Task[None]] = set()
        self._runners: dict[str, asyncio.Task[None]] = {}

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        logger.info(f"Servidor termplay rodando em {self.host}:{self.port}")
        self._broadcast_task = asyncio.create_task(self._broadcaster.run())

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._clients.add(task)
        peer = writer.get_extra_info("peername")
        logger.info(f"Conexão aceita de {peer}")
        adapter = ProtocolServerAdapter(reader, writer)
        try:
            first = await adapter.recv_control()
            if first is None:
                return
            action = first.get("action")
            stealth = bool(first.get("stealth"))
            if action == ACTION_CREATE_ROOM:
                await self._host_flow(
                    adapter,
                    str(first.get("name") or "Host"),
                    stealth,
                    str(first.get("game") or self._game_name),
                    str(first.get("rules") or "standard"),
                )
            elif action == ACTION_JOIN_ROOM:
                await self._guest_flow(
                    adapter,
                    str(first.get("name") or "Player"),
                    str(first.get("code") or "").upper(),
                    stealth,
                )
            else:
                await adapter.send_control(
                    type=TYPE_ERROR, message="Ação inválida", fatal=True
                )
        except Exception:
            logger.exception(f"Erro na sessão de {peer}")
        finally:
            await adapter.close()
            if task is not None:
                self._clients.discard(task)
            logger.info(f"Conexão fechada para {peer}")

    # ── Host ─────────────────────────────────────────────────────────────────

    async def _host_flow(
        self,
        adapter: ProtocolServerAdapter,
        name: str,
        stealth: bool = False,
        game: str = "",
        rules: str = "standard",
    ) -> None:
        player = RoomPlayer(name=name, transport=adapter, stealth=stealth)
        room = RoomManager.create(player, game=game or self._game_name, rules=rules)
        self._broadcaster.update(
            host=name,
            game=room.game,
            players=room.player_count,
            max_players=room.max_players,
            status="waiting",
            port=self.actual_port,
        )
        # The game lifecycle runs in a room-scoped task, independent of any single
        # connection, so the host may leave (and leadership migrate) without
        # tearing down the room.
        self._runners[room.code] = asyncio.create_task(self._room_runner(room))
        await adapter.send_control(type=TYPE_ROOM_CREATED, code=room.code, you=name)
        await self._broadcast_state(room)
        await self._serve_player(adapter, room, player)

    # ── Guest ────────────────────────────────────────────────────────────────

    async def _guest_flow(
        self,
        adapter: ProtocolServerAdapter,
        name: str,
        code: str,
        stealth: bool = False,
    ) -> None:
        # P2P: código vazio → auto-join na única sala disponível
        room = RoomManager.get(code) if code else RoomManager.first()
        if room is None:
            err = (
                "Sala não encontrada." if not code else f"Sala '{code}' não encontrada."
            )
            await adapter.send_control(type=TYPE_ERROR, message=err, fatal=True)
            return
        if room.is_full:
            await adapter.send_control(
                type=TYPE_ERROR, message="Sala cheia.", fatal=True
            )
            return

        # Evict stale ghost with the same name (reconnect / reload race).
        stale = next(
            (p for p in room.players if p.name == name and not p.is_bot), None
        )
        stale_was_host = stale is not None and stale is room.host
        if stale is not None:
            room.remove_player(stale)
            with contextlib.suppress(Exception):
                await stale.transport.close()

        player = RoomPlayer(name=name, transport=adapter, stealth=stealth)
        room.add_player(player)
        # A reconnecting host keeps leadership across a reload.
        if stale_was_host:
            room.host = player
        await adapter.send_control(type=TYPE_ROOM_JOINED, code=room.code, you=name)
        await self._broadcast_state(room)
        await self._serve_player(adapter, room, player)

    # ── Unified per-player loop ──────────────────────────────────────────────

    async def _serve_player(
        self, adapter: ProtocolServerAdapter, room: Room, player: RoomPlayer
    ) -> None:
        """Lobby + game loop shared by host and guests. Host-only actions are
        gated on ``player is room.host`` so leadership can migrate freely. After a
        match the loop returns to the lobby so players can rematch."""
        try:
            while True:
                # Lobby phase: wait for the host to start (or the player to leave).
                while not room.ready.is_set():
                    try:
                        msg = await asyncio.wait_for(
                            adapter.recv_control(), timeout=0.3
                        )
                    except TimeoutError:
                        continue
                    if msg is None:
                        return
                    action = msg.get("action")
                    if action == ACTION_LEAVE:
                        return
                    if action == ACTION_CHAT:
                        await self._broadcast_chat(
                            room, player.name, str(msg.get("text") or "")
                        )
                    elif player is room.host:
                        await self._handle_host_action(adapter, room, action, msg)

                # Game phase: relay input until the match completes.
                relay = asyncio.create_task(self._relay(adapter, room, player.name))
                await room.game_complete.wait()
                relay.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await relay
                # Wait for the runner to return the room to the lobby, then loop
                # back so the player can play another round.
                while room.ready.is_set():
                    await asyncio.sleep(0.05)
        finally:
            await self._handle_departure(room, player)

    async def _handle_host_action(
        self,
        adapter: ProtocolServerAdapter,
        room: Room,
        action: object,
        msg: dict[str, object],
    ) -> None:
        if action == ACTION_START_GAME:
            if msg.get("rules") is not None:
                room.rules = msg.get("rules")
            if room.player_count >= MIN_PLAYERS:
                room.ready.set()
            else:
                await adapter.send_control(
                    type=TYPE_ERROR,
                    message=f"Mínimo {MIN_PLAYERS} jogadores para iniciar.",
                )
        elif action == ACTION_ADD_BOT:
            await self._add_bot(room)
        elif action == ACTION_KICK:
            await self._kick_player(room, str(msg.get("target") or ""))

    async def _room_runner(self, room: Room) -> None:
        """Owns the room's game lifecycle, decoupled from any connection. Loops so
        the same room can host repeated matches (rematches) from its lobby."""
        try:
            while True:
                await room.ready.wait()
                self._broadcaster.update(status="playing")
                await self._broadcast(room, type=TYPE_GAME_START, game=room.game)
                await self._run_controller(room)  # sets game_complete + GAME_OVER
                # Back to the lobby for a rematch. Clear game_complete first (no
                # waiters), then ready last so _serve_player loops cleanly.
                room.game_complete.clear()
                self._broadcaster.update(status="waiting")
                await self._broadcast_state(room)
                room.ready.clear()
                if not any(not p.is_bot for p in room.players):
                    break  # no humans left to rematch
        except asyncio.CancelledError:
            raise
        finally:
            self._runners.pop(room.code, None)
            RoomManager.remove(room.code)
            self._broadcaster.update(players=0, status="waiting")

    async def _handle_departure(self, room: Room, player: RoomPlayer) -> None:
        """Remove a player; migrate host if they led; drop the room if empty."""
        was_host = player is room.host
        room.remove_player(player)
        humans = [p for p in room.players if not p.is_bot]
        if not humans:
            # No real players left — cancel the (possibly idle) runner and drop.
            runner = self._runners.pop(room.code, None)
            if runner is not None and not room.ready.is_set():
                runner.cancel()
            RoomManager.remove(room.code)
            self._broadcaster.update(players=0, status="waiting")
            return
        if was_host:
            room.host = humans[0]
            self._broadcaster.update(host=room.host.name)
        await self._broadcast_state(room)

    # ── Jogo ─────────────────────────────────────────────────────────────────

    async def _run_controller(self, room: Room) -> None:
        from termplay.engine.multiplayer import (
            IMultiplayerController,
            MultiplayerRegistry,
        )

        transports: list[ITransportAdapter] = [p.transport for p in room.players]
        names = [p.name for p in room.players]
        stealth_flags = [p.stealth for p in room.players]

        factory = MultiplayerRegistry.get(room.game)
        controller: IMultiplayerController
        if factory is None:
            from termplay.games.blackjack.application.multiplayer_controller import (
                MultiplayerGameController,
            )
            from termplay.games.blackjack.domain.rules import BlackjackRules

            controller = MultiplayerGameController(
                transports, BlackjackRules(), names=names, stealth_flags=stealth_flags
            )
        else:
            controller = factory(transports, names, stealth_flags, room.rules)
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
        self._broadcaster.update(players=room.player_count)
        await self._broadcast(
            room,
            type=TYPE_ROOM_STATE,
            code=room.code,
            host=room.host.name,
            players=[p.name for p in room.players],
            bots=[p.name for p in room.players if p.is_bot],
            player_count=room.player_count,
            min_players=MIN_PLAYERS,
            max_players=room.max_players,
            can_start=room.player_count >= MIN_PLAYERS,
        )

    async def _broadcast_chat(self, room: Room, name: str, text: str) -> None:
        if text:
            await self._broadcast(room, type=TYPE_CHAT, name=name, text=text)

    async def _add_bot(self, room: Room) -> None:
        if room.is_full:
            return
        bot_num = sum(1 for p in room.players if p.is_bot) + 1
        bot_name = f"Bot {bot_num}"
        bot = RoomPlayer(
            name=bot_name,
            transport=self._make_bot_transport(room.game, bot_name),
            is_bot=True,
        )
        room.add_player(bot)
        await self._broadcast_state(room)

    @staticmethod
    def _make_bot_transport(game: str, name: str) -> ITransportAdapter:
        """Pick the CPU transport whose AI matches the room's game."""
        if (game or "").lower() == "blackjack":
            from termplay.games.blackjack.application.bot_transport import (
                BlackjackBotTransportAdapter,
            )
            return BlackjackBotTransportAdapter(name)
        from termplay.engine.bot_transport import BotTransportAdapter
        return BotTransportAdapter(name)

    async def _kick_player(self, room: Room, target: str) -> None:
        player = next((p for p in room.players if p.name == target), None)
        if player is None or player is room.host:
            return
        room.remove_player(player)
        if not player.is_bot:
            with contextlib.suppress(Exception):
                await player.transport.close()
        await self._broadcast_state(room)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    @property
    def actual_port(self) -> int:
        """Porta real após bind (útil quando porta 0 foi pedida ao OS)."""
        assert self._server is not None
        addr = self._server.sockets[0].getsockname()
        return int(addr[1])

    async def stop(self) -> None:
        self._broadcaster.stop()
        if self._broadcast_task is not None:
            self._broadcast_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._broadcast_task
        # Cancel in-flight client handlers (game loops, relays) and room runners
        # so the event loop has nothing left blocking shutdown.
        runners = list(self._runners.values())
        self._runners.clear()
        clients = list(self._clients) + runners
        self._clients.clear()
        for task in clients:
            task.cancel()
        for task in clients:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        if self._server:
            self._server.close()
            with contextlib.suppress(Exception):
                await self._server.wait_closed()
            logger.info("Servidor parado")
