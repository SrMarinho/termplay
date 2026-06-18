# termplay — engine de jogos no terminal via TCP

Engine de jogos para terminal, extensível por plugins. Cliente TUI (Textual) e
servidor multiplayer falam um protocolo JSON sobre TCP. Vem com Blackjack — solo
contra o dealer ou multiplayer em salas com chat.

## Instalação

```bash
# Como ferramenta global (recomendado) — instala os executáveis termplay e termplay-server
uv tool install .
# ou a partir do diretório do projeto
uv tool install "C:/caminho/para/py21ssh"

# Com pip
pip install .
```

Isso registra dois comandos:

| Comando | Função |
|---------|--------|
| `termplay` | Cliente TUI (solo e multiplayer) |
| `termplay-server` | Servidor multiplayer (TCP, default `0.0.0.0:4443`) |

## Uso

### Solo (sem servidor)

```bash
termplay        # → Solo → Blackjack → joga contra o dealer
```

### Multiplayer (servidor + 2+ clientes)

```bash
# Terminal 1 — servidor
termplay-server                       # 0.0.0.0:4443
termplay-server --host 0.0.0.0 --port 4443

# Terminal 2 — líder
termplay   # → Multiplayer → Criar Sala → copia o código

# Terminal 3 — convidado
termplay   # → Multiplayer → Entrar Sala → digita o código
```

O líder vê os jogadores entrando ao vivo; o botão **Iniciar Partida** habilita
ao atingir o mínimo de jogadores. Sala tem chat.

### Configuração

`termplay` → **Configuração** → salva o nickname entre execuções
(`%APPDATA%/termplay/config.json` no Windows, `~/.config/termplay/config.json` no POSIX).

## Desenvolvimento

```bash
uv sync --extra dev          # deps de dev (pytest, mypy, ruff)

uv run python -m pytest tests/ -q    # testes
uv run python -m mypy src/ --strict  # type checking
uv run python -m ruff check src/     # lint
```

## Arquitetura

```
src/termplay/
├── engine/             # núcleo agnóstico de jogo
│   ├── registry.py     #   GameRegistry — plugins se registram via @register
│   ├── game.py         #   IGame — contrato de plugin
│   ├── room.py         #   Room/RoomManager — salas multiplayer
│   ├── protocol.py     #   protocolo JSON delimitado por linha
│   ├── protocol_adapter.py #  adapter server-side do protocolo
│   ├── server.py       #   servidor TCP (só comunicação)
│   └── transport/      #   adapters TCP/queued
├── frontends/          # cliente TUI (Textual)
│   ├── net.py          #   ServerConnection — transporte do cliente
│   ├── textual_app.py  #   App + listener central
│   └── screens/        #   telas nativas (home, salas, jogo, config)
├── games/
│   └── blackjack/      # plugin Blackjack (domain/application/display)
└── config/             # persistência de settings (nickname)
```

O servidor é **só comunicação**: recebe ações JSON, gerencia salas e repassa
I/O do jogo. O cliente renderiza telas nativas — sem dump de ANSI cru.

## Adicionar um jogo

1. Criar `src/termplay/games/<jogo>/plugin.py` implementando `IGame`.
2. Registrar com `@GameRegistry.register(...)`.
3. Importar o plugin em `games/__init__.py` para auto-registro.

## Segurança

- **Zero shell**: o servidor não spawna shell nem `subprocess`.
- **Zero eval**: nenhuma entrada do usuário passa por `eval()`/`exec()`.
- **Task isolada**: cada cliente roda em `asyncio.Task` separada.
