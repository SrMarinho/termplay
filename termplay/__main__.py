"""Entry point da engine termplay.

Responsabilidade: Inicializar a engine, registrar jogos e iniciar o servidor.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

# Importar plugins para registrá-los automaticamente (via @GameRegistry.register)
import termplay.games.blackjack.plugin  # noqa: F401
import termplay.games.hangman.plugin  # noqa: F401
import termplay.games.tictactoe.plugin  # noqa: F401
import termplay.games.uno.plugin  # noqa: F401
from termplay.engine.registry import GameRegistry
from termplay.engine.server import TermPlayServer


def parse_args() -> argparse.Namespace:
    """Parse de argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="termplay - Engine de jogos via TCP/SSH"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host do servidor (padrão: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=4443,
        help="Porta do servidor (padrão: 4443)",
    )
    parser.add_argument(
        "--game",
        default="blackjack",
        help="Jogo hospedado pela sala (padrão: blackjack)",
    )
    parser.add_argument(
        "--list-games",
        action="store_true",
        help="Lista jogos disponíveis e sai",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nível de log (padrão: INFO)",
    )
    return parser.parse_args()


def setup_logging(level: str) -> None:
    """Configura o sistema de logging."""
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def run_server(host: str, port: int, game: str = "blackjack") -> None:
    """Executa o servidor principal."""
    server = TermPlayServer(host, port, game)
    await server.start()

    ip = "127.0.0.1" if host == "0.0.0.0" else host
    print(f"termplay (protocolo) rodando em {host}:{port}")
    print("   Conecte com o cliente TUI:")
    print(f"     uv run termplay   (host {ip}, porta {port})")
    print("\nPressione Ctrl+C para parar.")

    try:
        # Manter rodando até Ctrl+C
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


def main() -> None:
    """Função principal."""
    args = parse_args()
    setup_logging(args.log_level)

    # Se --list-games, apenas listar e sair
    if args.list_games:
        games = GameRegistry.list_games()
        if not games:
            print("Nenhum jogo registrado.")
            sys.exit(0)

        print("Jogos disponíveis:\n")
        for name, desc in games:
            print(f"  {name:15s} {desc}")
        sys.exit(0)

    # Caso contrário, iniciar o servidor
    try:
        asyncio.run(run_server(args.host, args.port, args.game))
    except KeyboardInterrupt:
        print("\nServidor interrompido.")
        sys.exit(0)


if __name__ == "__main__":
    main()
