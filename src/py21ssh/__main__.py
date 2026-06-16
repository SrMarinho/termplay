"""Entry point — inicia o servidor TCP."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from py21ssh.transport.server import TCPServer


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="py21ssh — Blackjack via TCP, sem shell",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  py21ssh                           # 0.0.0.0:4443
  py21ssh --host 192.168.1.100      # IP específico
  py21ssh --port 7777               # porta diferente
  py21ssh --log-level DEBUG         # debug
        """,
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Endereço para escutar (padrão: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=4443,
        help="Porta TCP (padrão: 4443)",
    )
    parser.add_argument(
        "--max-sessions",
        type=int,
        default=10,
        help="Máximo de sessões simultâneas (padrão: 10)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nível de log (padrão: INFO)",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point principal. Inicia o servidor e aguarda Ctrl+C."""
    args = _parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    server = TCPServer(
        host=args.host,
        port=args.port,
        max_concurrent=args.max_sessions,
    )

    async def _run() -> None:
        await server.start()
        print(
            f"🃏 py21ssh rodando em {args.host}:{args.port}\n"
            f"   Conecte com: nc {args.host if args.host != '0.0.0.0' else '<IP>'}"
            f" {args.port}\n"
            f"   Pressione Ctrl+C para parar."
        )
        await server.serve_forever()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
        sys.exit(0)


if __name__ == "__main__":
    main()
