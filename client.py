"""Cliente TCP para py21ssh — conectar e jogar sem instalar nada."""

from __future__ import annotations

import argparse
import asyncio
import sys


async def _run(host: str, port: int) -> None:
    try:
        reader, writer = await asyncio.open_connection(host, port)
    except ConnectionRefusedError:
        print(f"✗ Servidor não encontrado em {host}:{port}")
        sys.exit(1)
    except OSError as exc:
        print(f"✗ Erro de conexão: {exc}")
        sys.exit(1)

    async def _reader() -> None:
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                sys.stdout.write(data.decode())
                sys.stdout.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    async def _writer() -> None:
        try:
            loop = asyncio.get_event_loop()
            while True:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                writer.write(line.encode())
                await writer.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            writer.close()

    try:
        await asyncio.gather(_reader(), _writer())
    except asyncio.CancelledError:
        pass
    finally:
        writer.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cliente py21ssh")
    parser.add_argument("host", nargs="?", default="127.0.0.1", help="IP do servidor")
    parser.add_argument("port", nargs="?", type=int, default=4443, help="Porta TCP")
    args = parser.parse_args()
    asyncio.run(_run(args.host, args.port))


if __name__ == "__main__":
    main()