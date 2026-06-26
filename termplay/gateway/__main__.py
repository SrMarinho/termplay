"""CLI entry point for the web gateway.

Run with ``python -m termplay.gateway`` or the ``termplay-web`` script.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from termplay.gateway.server import WebGateway


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="termplay web gateway — browser frontend bridge"
    )
    parser.add_argument("--bind", default="0.0.0.0", help="HTTP bind address")
    parser.add_argument(
        "--http-port", type=int, default=8080, help="HTTP/WebSocket port"
    )
    parser.add_argument(
        "--server",
        default="127.0.0.1:4443",
        metavar="HOST:PORT",
        help="Game server address for room creation (default: 127.0.0.1:4443)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def _parse_server(addr: str) -> tuple[str, int]:
    host, _, port_str = addr.rpartition(":")
    return (host or "127.0.0.1", int(port_str or "4443"))


def _make_exception_handler(
    default: object,
) -> object:
    """Suppress WinError 10054 ConnectionResetError from ProactorEventLoop callbacks.

    On Windows, closing a WebSocket causes asyncio to call sock.shutdown(SHUT_RDWR)
    on an already-reset socket, raising ConnectionResetError internally. This is
    harmless noise — the connection is already gone.
    """
    import logging as _logging
    _log = _logging.getLogger(__name__)

    def handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:  # type: ignore[type-arg]
        exc = context.get("exception")
        if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
            return  # normal peer disconnect on Windows — suppress
        loop.default_exception_handler(context)  # type: ignore[attr-defined]

    return handler


async def _run(bind: str, http_port: int, game_server: tuple[str, int]) -> None:
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(_make_exception_handler(loop.default_exception_handler))  # type: ignore[arg-type]
    gateway = WebGateway(bind, http_port, game_server)
    await gateway.start()
    print(f"termplay web gateway on http://{bind}:{http_port}")
    print(f"Game server: {game_server[0]}:{game_server[1]}")
    print("Open in a browser — create or join a room. Ctrl+C to stop.")
    try:
        await gateway.serve_forever()
    finally:
        await gateway.stop()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        asyncio.run(_run(args.bind, args.http_port, _parse_server(args.server)))
    except KeyboardInterrupt:
        print("\nGateway stopped.")


if __name__ == "__main__":
    main()
