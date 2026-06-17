# py21ssh — Blackjack via TCP, sem shell

Jogue 21 (Blackjack) pela sua intranet conectando com `nc`. Zero shell, zero SSH, zero web.

## Filosofia

> Um jogo de Blackjack que você joga conectando com `nc IP 4443`.
> O servidor não tem shell. Não tem subprocess. Não tem eval.
> Apenas um socket TCP que só sabe rodar Blackjack.

## Quickstart

```bash
# Servidor (Linux/macOS/Windows)
uv sync
uv run py21ssh                   # 0.0.0.0:4443

# Cliente — opção 1: netcat (Linux/macOS)
nc 192.168.1.100 4443

# Cliente — opção 2: ncat (Windows via winget install nmap)
ncat 127.0.0.1 4443

# Cliente — opção 3: Python (Windows, sem instalar nada)
uv run python client.py          # 127.0.0.1:4443
uv run python client.py 192.168.1.100
```

## Instalação

```bash
# Clonar
cd py21ssh

# Instalar dependências
uv sync

# (Opcional) Dev — testes + type checking
uv sync --extra dev

# Rodar servidor
uv run py21ssh --host 0.0.0.0 --port 4443
```

## Comandos do jogo

| Comando | Ação |
|---------|------|
| `1` ou `h` | Hit — comprar carta |
| `2` ou `s` | Stand — parar |
| `3` ou `d` | Double — dobrar aposta (só nas 2 primeiras) |
| `q` | Sair |

## Conectar

```bash
# Terminal 1 — servidor
uv run py21ssh --host 0.0.0.0 --port 4443

# Terminal 2 — cliente (3 opções)
nc <ip> 4443                # Linux/macOS
ncat <ip> 4443              # Windows (nmap)
uv run python client.py     # Windows (uv + Python)
```

## Arquitetura

```
src/py21ssh/
├── domain/          # Regras de negócio (Card, Deck, Hand, Rules)
│   ├── card.py      #   — zero I/O
│   ├── deck.py      #   — puro Python
│   ├── hand.py      #   — testável sem mock
│   └── rules.py     #
├── application/     # Orquestração (GameController)
│   ├── interfaces.py#   — depende de interfaces (DIP)
│   └── game_controller.py
├── transport/       # I/O (TCPAdapter, TCPServer)
│   ├── tcp_adapter.py#  — sem shell, sem subprocess
│   └── server.py    #   — isolamento por task
└── display/         # Renderização ANSI (Rich)
    └── renderer.py
```

Veja [docs/SPEC.md](docs/SPEC.md) para especificação completa.

## Segurança

- **Zero shell**: o servidor não spawna `/bin/sh`, `/bin/bash`, nem `subprocess`
- **Zero eval**: nenhuma entrada do usuário passa por `eval()` ou `exec()`
- **Task isolada**: cada cliente roda em uma `asyncio.Task` separada
- **Timeout**: leitura expira após 300s de inatividade
- **Limite de sessões**: máximo de sessões simultâneas configurável
- **Read-only**: o código do jogo não escreve arquivos durante execução

## Testes

```bash
uv run pytest -v          # 65 testes
uv run mypy src/ --strict # 19 arquivos, 0 erros
uv run ruff check src/    # all checks passed
```

## Roadmap

- [x] Domain layer (Card, Deck, Hand, Rules)
- [x] Application layer (GameController)
- [x] Transport layer (TCPAdapter, TCPServer)
- [x] Display layer (RichRenderer — ANSI via TCP)
- [x] Testes de domínio (49) e transporte (16)
- [x] mypy --strict + ruff
- [ ] Testes do GameController (application layer)
- [ ] Servidor SSH dedicado (asyncssh)
- [ ] Split / Insurance / Surrender
- [ ] Leaderboard (SQLite opcional)