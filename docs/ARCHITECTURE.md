# py21ssh — Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENTE                                   │
│              nc <host> 4443  /  telnet <host> 4443               │
└────────────────────────────┬─────────────────────────────────────┘
                             │  TCP socket (stdin/stdout raw)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  TRANSPORT LAYER              src/py21ssh/transport/             │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │ TCPServer                                                │     │
│  │  • asyncio.start_server(host, port)                      │     │
│  │  • max_concurrent (limite de sessões)                    │     │
│  │  • _on_connect → TCPAdapter + RichRenderer + Task        │     │
│  │  • serve_forever() / stop() (graceful shutdown)          │     │
│  └──────────────────────┬──────────────────────────────────┘     │
│                         │                                         │
│  ┌──────────────────────▼──────────────────────────────────┐     │
│  │ TCPAdapter                                              │     │
│  │  • StreamReader → read_line() / read_char()             │     │
│  │  • StreamWriter → write(text)                           │     │
│  │  • Sem subprocess, sem shell, sem eval                  │     │
│  │  • Timeout 300s por wait_for                            │     │
│  │  • Closed flag + early return em desconexão             │     │
│  └──────────────────────┬──────────────────────────────────┘     │
│                         │  ITransportAdapter (protocol)          │
├─────────────────────────┼────────────────────────────────────────┤
│  APPLICATION LAYER      │  src/py21ssh/application/              │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │ GameController                                          │     │
│  │  • run() → welcome → loop de rodadas → goodbye          │     │
│  │  • _play_round() → bet → deal → player → dealer →      │     │
│  │                       resolve                            │     │
│  │  • _player_turn() → loop hit/stand/double               │     │
│  │  • _get_bet() → valida entrada (int, range)             │     │
│  │  • DIP: depende de ITransportAdapter + IGameRules       │     │
│  └──────────────────────┬──────────────────────────────────┘     │
│                         │                                         │
│  ┌──────────────────────▼──────────────────────────────────┐     │
│  │ SessionManager                                          │     │
│  │  • run_session(transport, renderer) → saldo final       │     │
│  │  • UUID por sessão + log + finally cleanup              │     │
│  └─────────────────────────────────────────────────────────┘     │
├──────────────────────────────────────────────────────────────────┤
│  DISPLAY LAYER              src/py21ssh/display/                 │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │ RichRenderer                                             │     │
│  │  • Renderiza ANSI via Rich (force_terminal=True)         │     │
│  │  • welcome(), table(), bet_prompt(), action_prompt()     │     │
│  │  • result(), bust(), goodbye(), error(), prompt()        │     │
│  │  • Saída vai para StringIO → enviada via TCP             │     │
│  └─────────────────────────────────────────────────────────┘     │
├──────────────────────────────────────────────────────────────────┤
│  DOMAIN LAYER               src/py21ssh/domain/                 │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │   Card   │  │   Deck   │  │   Hand   │  │ BlackjackRules │   │
│  │ frozen   │  │ shuffle  │  │ value    │  │ initial_deal   │   │
│  │ dataclass│  │ draw     │  │ is_bust  │  │ player_hit     │   │
│  │ Suit/Rank│  │ remaining│  │ is_black │  │ dealer_play    │   │
│  │ is_ace   │  │          │  │ can_dbl  │  │ resolve        │   │
│  └──────────┘  └──────────┘  └──────────┘  └───────┬───────────┘   │
│                                                     │               │
│                                                     │ IGameRules    │
│                                                     ▼               │
│                                        ┌──────────────────────┐    │
│                                        │  RoundResult (enum)   │    │
│                                        │  WIN / LOSE / PUSH /  │    │
│                                        │  BLACKJACK            │    │
│                                        └──────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘

══════════════════════════════════════════════════════════════════════

                    DIAGRAMA DE FLUXO (1 rodada)

  ┌─────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐
  │ WELCOME │───▶│   BET    │───▶│   DEAL    │───▶│ PLAYER   │
  │         │    │          │    │           │    │  TURN    │
  └─────────┘    └──────────┘    └───────────┘    └────┬─────┘
                                                        │
                                              ┌─────────┴─────────┐
                                              ▼                   ▼
                                         ┌─────────┐       ┌─────────┐
                                         │  BUST?  │       │  STAND  │
                                         │  → LOSE │       │  → DEAL │
                                         └─────────┘       │  TURN   │
                                                            └────┬────┘
                                                                 │
                                                            ┌────▼────┐
                                                            │ DEALER  │
                                                            │  PLAY   │
                                                            └────┬────┘
                                                                 │
                                                            ┌────▼────┐
                                                            │ RESOLVE │
                                                            │ WIN/LOSE│
                                                            │ PUSH/BJ │
                                                            └────┬────┘
                                                                 │
                                                            ┌────▼────┐
                                                            │ CONTINUE│──▶ BET
                                                            │  s/n?   │
                                                            └────┬────┘
                                                                 │ (n)
                                                            ┌────▼────┐
                                                            │ GOODBYE │
                                                            └─────────┘
```

## Camadas e Interdependências

```
display/          transport/
    │                  │
    │ depende de       │ implementa
    ▼                  ▼
application/ ◀────────┘
    │
    │ depende de
    ▼
domain/
    │
    └── zero imports externos (só stdlib)
```

**Regra de ouro**: Uma camada só importa da camada imediatamente inferior
ou de interfaces em `application/interfaces.py`.

```
domain/       →  NADA (stdlib only)
application/  →  domain/ + interfaces
transport/    →  application/interfaces.py
display/      →  domain/ + conf
__main__.py   →  transport/ (ponto de entrada)
```

## Segurança em Camadas

```
┌─────────────────────────────────────────────┐
│ 1. Rede: TCP puro (intranet)                │
│    WireGuard opcional (criptografia externa) │
├─────────────────────────────────────────────┤
│ 2. TCPServer: limite de sessões             │
│    Rejeita excesso com mensagem             │
├─────────────────────────────────────────────┤
│ 3. TCPAdapter: sem shell, sem subprocess    │
│    Timeout 300s, closed flag                │
├─────────────────────────────────────────────┤
│ 4. GameController: validação de entrada     │
│    try/except int, whitelist de comandos    │
├─────────────────────────────────────────────┤
│ 5. Domain: regras puras, sem I/O            │
│    Dados imutáveis (Card frozen dataclass)  │
└─────────────────────────────────────────────┘
```
