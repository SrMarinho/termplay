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
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


async def _run(bind: str, http_port: int) -> None:
    gateway = WebGateway(bind, http_port)
    await gateway.start()
    print(f"termplay web gateway on http://{bind}:{http_port}")
    print("Open it in a browser and join a room. Ctrl+C to stop.")
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
        asyncio.run(_run(args.bind, args.http_port))
    except KeyboardInterrupt:
        print("\nGateway stopped.")


if __name__ == "__main__":
    main()
