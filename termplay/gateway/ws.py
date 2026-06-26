"""Minimal RFC 6455 WebSocket server side over asyncio streams.

Stdlib only — no third-party dependency. Supports the subset the gateway needs:
the opening handshake plus masked client text frames and unmasked server text
frames, with ping/pong and close handling. Binary and continuation frames are
not used by the JSON-line protocol, so they are rejected.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import struct

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

_OP_CONT = 0x0
_OP_TEXT = 0x1
_OP_BINARY = 0x2
_OP_CLOSE = 0x8
_OP_PING = 0x9
_OP_PONG = 0xA


def accept_key(client_key: str) -> str:
    """Compute the Sec-WebSocket-Accept value for a client key."""
    digest = hashlib.sha1((client_key + _GUID).encode()).digest()
    return base64.b64encode(digest).decode()


class WebSocketClosed(Exception):  # noqa: N818  # idiomatic WS close sentinel
    """Raised when the peer closed the connection or the stream ended."""


class WebSocket:
    """A connected WebSocket peer. Text-frame oriented."""

    def __init__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._closed = False

    @classmethod
    async def upgrade(
        cls,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        client_key: str,
    ) -> WebSocket:
        """Write the 101 handshake response and return the connected socket."""
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key(client_key)}\r\n\r\n"
        )
        writer.write(response.encode())
        await writer.drain()
        return cls(reader, writer)

    async def send_text(self, text: str) -> None:
        if self._closed:
            return
        payload = text.encode("utf-8")
        header = bytearray([0x80 | _OP_TEXT])
        length = len(payload)
        if length < 126:
            header.append(length)
        elif length < 65536:
            header.append(126)
            header += struct.pack("!H", length)
        else:
            header.append(127)
            header += struct.pack("!Q", length)
        self._writer.write(bytes(header) + payload)
        await self._writer.drain()

    async def recv_text(self) -> str:
        """Read the next text message. Raises WebSocketClosed on close/EOF."""
        while True:
            opcode, payload = await self._read_frame()
            if opcode == _OP_TEXT:
                return payload.decode("utf-8")
            if opcode == _OP_CLOSE:
                await self.close()
                raise WebSocketClosed
            if opcode == _OP_PING:
                await self._send_control(_OP_PONG, payload)
            # pong / unsupported opcodes are ignored

    async def _read_frame(self) -> tuple[int, bytes]:
        try:
            first2 = await self._reader.readexactly(2)
        except (asyncio.IncompleteReadError, ConnectionError) as exc:
            raise WebSocketClosed from exc
        opcode = first2[0] & 0x0F
        masked = bool(first2[1] & 0x80)
        length = first2[1] & 0x7F
        try:
            if length == 126:
                length = struct.unpack("!H", await self._reader.readexactly(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", await self._reader.readexactly(8))[0]
            mask = await self._reader.readexactly(4) if masked else b""
            data = await self._reader.readexactly(length)
        except (asyncio.IncompleteReadError, ConnectionError) as exc:
            raise WebSocketClosed from exc
        if masked:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        return opcode, data

    async def _send_control(self, opcode: int, payload: bytes) -> None:
        if self._closed:
            return
        header = bytes([0x80 | opcode, len(payload) & 0x7F])
        self._writer.write(header + payload)
        await self._writer.drain()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._writer.write(bytes([0x80 | _OP_CLOSE, 0]))
            await self._writer.drain()
        except (ConnectionError, OSError):
            pass
        self._writer.close()


async def read_http_head(
    reader: asyncio.StreamReader,
) -> tuple[str, dict[str, str]] | None:
    """Read an HTTP request head. Returns (request_line, lowercased headers)."""
    try:
        raw = await reader.readuntil(b"\r\n\r\n")
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError):
        return None
    lines = raw.decode("latin-1").split("\r\n")
    if not lines or not lines[0]:
        return None
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            name, _, value = line.partition(":")
            headers[name.strip().lower()] = value.strip()
    return lines[0], headers
