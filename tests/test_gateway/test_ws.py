"""WebSocket frame codec and handshake tests."""

from __future__ import annotations

import asyncio
import struct

import pytest

from termplay.gateway.ws import WebSocket, WebSocketClosed, accept_key


class _FakeWriter:
    """Captures bytes written; satisfies the StreamWriter surface ws.py uses."""

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.closed = False

    def write(self, data: bytes) -> None:
        self.buffer += data

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


def _reader_with(data: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


def _masked_text_frame(text: str, mask: bytes = b"\x01\x02\x03\x04") -> bytes:
    payload = text.encode("utf-8")
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    header = bytes([0x81, 0x80 | len(payload)])
    return header + mask + masked


def test_accept_key_rfc_vector() -> None:
    assert accept_key("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="


async def test_send_text_frame_is_unmasked() -> None:
    writer = _FakeWriter()
    ws = WebSocket(asyncio.StreamReader(), writer)  # type: ignore[arg-type]
    await ws.send_text("hi")
    assert writer.buffer == bytes([0x81, 0x02]) + b"hi"


async def test_recv_masked_client_frame() -> None:
    reader = _reader_with(_masked_text_frame("ping"))
    ws = WebSocket(reader, _FakeWriter())  # type: ignore[arg-type]
    assert await ws.recv_text() == "ping"


async def test_recv_extended_length_frame() -> None:
    text = "x" * 200
    payload = text.encode()
    mask = b"\x00\x00\x00\x00"
    frame = bytes([0x81, 0x80 | 126]) + struct.pack("!H", len(payload)) + mask + payload
    ws = WebSocket(_reader_with(frame), _FakeWriter())  # type: ignore[arg-type]
    assert await ws.recv_text() == text


async def test_recv_close_raises() -> None:
    frame = bytes([0x88, 0x00])  # close, no payload
    ws = WebSocket(_reader_with(frame), _FakeWriter())  # type: ignore[arg-type]
    with pytest.raises(WebSocketClosed):
        await ws.recv_text()


async def test_recv_eof_raises() -> None:
    ws = WebSocket(_reader_with(b""), _FakeWriter())  # type: ignore[arg-type]
    with pytest.raises(WebSocketClosed):
        await ws.recv_text()
