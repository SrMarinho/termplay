"""WebGateway — bridges browser WebSocket clients to the TCP game server.

One process serves the static web client over HTTP and exposes a WebSocket
endpoint at ``/ws``. Each WebSocket connection is relayed 1:1 to a fresh TCP
connection to a chosen game server, speaking the existing JSON-line protocol
(``engine/protocol.py``). A shared ``RoomDiscoverer`` listens for UDP beacons and
the gateway pushes the live room list to every connected browser, since browsers
cannot do UDP themselves.

The gateway imports only from ``engine`` — never from ``frontends`` — preserving
the project's layering.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from pathlib import Path

from termplay.engine.discovery import RoomDiscoverer
from termplay.engine.protocol import (
    ACTION_CREATE_ROOM,
    ACTION_JOIN_ROOM,
    ACTION_RECONNECT,
    encode,
)
from termplay.gateway.ws import WebSocket, WebSocketClosed, read_http_head

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"
_ROOM_LIST_INTERVAL = 1.0
_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".ico": "image/x-icon",
}


class WebGateway:
    """HTTP + WebSocket gateway in front of the TCP game server."""

    def __init__(
        self,
        bind: str = "0.0.0.0",
        http_port: int = 8080,
        game_server: tuple[str, int] = ("127.0.0.1", 4443),
    ) -> None:
        self._bind = bind
        self._http_port = http_port
        self._game_server = game_server
        self._discoverer = RoomDiscoverer()
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        await self._discoverer.start()
        self._server = await asyncio.start_server(
            self._handle, self._bind, self._http_port
        )
        logger.info("Web gateway on http://%s:%d", self._bind, self._http_port)

    async def serve_forever(self) -> None:
        assert self._server is not None
        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        await self._discoverer.stop()
        if self._server is not None:
            self._server.close()
            with contextlib.suppress(Exception):
                await self._server.wait_closed()

    # ── connection routing ───────────────────────────────────────────────────

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            head = await read_http_head(reader)
            if head is None:
                return
            request_line, headers = head
            path = [*request_line.split(" "), "", "/"][1]
            if (
                headers.get("upgrade", "").lower() == "websocket"
                and headers.get("sec-websocket-key")
            ):
                ws = await WebSocket.upgrade(
                    reader, writer, headers["sec-websocket-key"]
                )
                await self._ws_session(ws)
            else:
                await self._serve_static(writer, path)
        except (ConnectionError, OSError):
            pass
        except Exception:
            logger.exception("Gateway connection error")
        finally:
            with contextlib.suppress(Exception):
                writer.close()

    # ── static files ─────────────────────────────────────────────────────────

    async def _serve_static(self, writer: asyncio.StreamWriter, path: str) -> None:
        rel = path.split("?", 1)[0].lstrip("/") or "index.html"
        target = (_STATIC_DIR / rel).resolve()
        inside = str(target).startswith(str(_STATIC_DIR.resolve()))
        if not inside or not target.is_file():
            writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
            return
        body = target.read_bytes()
        ctype = _CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        writer.write(
            f"HTTP/1.1 200 OK\r\nContent-Type: {ctype}\r\n"
            f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode()
            + body
        )
        await writer.drain()

    # ── WebSocket session ──────────────────────────────────────────────────────

    async def _ws_session(self, ws: WebSocket) -> None:
        """Feed room list until the browser connects, then relay to TCP."""
        feed = asyncio.create_task(self._room_list_feed(ws))
        tcp_writer: asyncio.StreamWriter | None = None
        try:
            msg = await self._await_connect(ws)
            if msg is None:
                return
            feed.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await feed
            tcp_payload = self._build_connect_payload(msg)
            tcp_host, tcp_port = self._resolve_server(msg)
            try:
                tcp_reader, tcp_writer = await asyncio.open_connection(
                    tcp_host, tcp_port
                )
            except OSError:
                await ws.send_text(json.dumps({
                    "type": "error",
                    "message": (
                        f"Cannot connect to game server at {tcp_host}:{tcp_port}. "
                        "Make sure 'termplay-server --game uno' is running."
                    ),
                    "fatal": True,
                }))
                return
            tcp_writer.write(encode(tcp_payload))
            await tcp_writer.drain()
            await self._relay(ws, tcp_reader, tcp_writer)
        except WebSocketClosed:
            pass
        finally:
            feed.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await feed
            if tcp_writer is not None:
                with contextlib.suppress(Exception):
                    tcp_writer.close()
            await ws.close()

    async def _await_connect(self, ws: WebSocket) -> dict[str, object] | None:
        """Wait for the browser's first connect message (create/join/reconnect)."""
        while True:
            msg = _safe_json(await ws.recv_text())
            if msg.get("action") in ("create_room", "join_room", "reconnect"):
                return msg

    def _resolve_server(self, msg: dict[str, object]) -> tuple[str, int]:
        """Return (host, port) of the game server for this connection.

        For create_room, always use the configured game server.
        For join_room/reconnect, use ip/port carried by the browser (falls back
        to the configured game server).
        """
        if msg.get("action") == "create_room":
            return self._game_server
        return (
            str(msg.get("ip") or self._game_server[0]),
            int(str(msg.get("port") or self._game_server[1])),
        )

    @staticmethod
    def _build_connect_payload(msg: dict[str, object]) -> dict[str, object]:
        """Build the first TCP payload (create_room / join_room / reconnect)."""
        action = msg.get("action")
        if action == "create_room":
            return {
                "action": ACTION_CREATE_ROOM,
                "name": str(msg.get("name") or "Player"),
                "game": str(msg.get("game") or "uno"),
                "rules": str(msg.get("rules") or "standard"),
            }
        if action == "reconnect":
            return {
                "action": ACTION_RECONNECT,
                "token": str(msg.get("token") or ""),
            }
        return {
            "action": ACTION_JOIN_ROOM,
            "name": str(msg.get("name") or "Player"),
            "code": str(msg.get("code") or ""),
        }

    def room_list_message(self) -> dict[str, object]:
        """Build the synthetic ``room_list`` message from current discovery state.

        Includes ``server`` so the browser knows where to send ``create_room``.
        """
        gs_host, gs_port = self._game_server
        return {
            "type": "room_list",
            "rooms": [
                {
                    "ip": r.ip,
                    "port": r.port,
                    "host": r.host,
                    "game": r.game,
                    "players": r.players,
                    "max_players": r.max_players,
                    "status": r.status,
                }
                for r in self._discoverer.rooms()
            ],
            "server": {"ip": gs_host, "port": gs_port},
        }

    async def _room_list_feed(self, ws: WebSocket) -> None:
        while True:
            await ws.send_text(json.dumps(self.room_list_message()))
            await asyncio.sleep(_ROOM_LIST_INTERVAL)

    async def _relay(
        self,
        ws: WebSocket,
        tcp_reader: asyncio.StreamReader,
        tcp_writer: asyncio.StreamWriter,
    ) -> None:
        async def ws_to_tcp() -> None:
            while True:
                text = await ws.recv_text()
                tcp_writer.write((text.strip() + "\n").encode("utf-8"))
                await tcp_writer.drain()

        async def tcp_to_ws() -> None:
            while True:
                line = await tcp_reader.readline()
                if not line:
                    raise WebSocketClosed
                await ws.send_text(line.decode("utf-8").rstrip("\r\n"))

        tasks = [asyncio.create_task(ws_to_tcp()), asyncio.create_task(tcp_to_ws())]
        try:
            await asyncio.gather(*tasks)
        except (WebSocketClosed, ConnectionError, OSError):
            pass
        finally:
            for t in tasks:
                t.cancel()
            for t in tasks:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await t


def _safe_json(text: str) -> dict[str, object]:
    try:
        data = json.loads(text)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}
