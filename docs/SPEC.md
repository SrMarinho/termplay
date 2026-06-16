# py21ssh — Especificação Técnica (SPEC)

## 1. Visão Geral

**py21ssh** é um servidor de Blackjack (21) jogável via TCP puro.
O cliente conecta com `nc <host> <port>` e cai direto no jogo —
sem shell, sem SSH, sem web.

**Público-alvo**: intranet corporativa, LAN doméstica, VPN.

## 2. Requisitos

### Funcionais

| ID | Descrição | Prioridade |
|----|-----------|------------|
| F1 | Distribuir 2 cartas para jogador e dealer | Alta |
| F2 | Jogador pode Hit (comprar carta) | Alta |
| F3 | Jogador pode Stand (parar) | Alta |
| F4 | Jogador pode Double Down (dobrar aposta, 1 carta) | Média |
| F5 | Dealer compra até 17 (stand em soft 17) | Alta |
| F6 | Blackjack natural (A+10/J/Q/K) paga 3:2 | Alta |
| F7 | Sistema de fichas (saldo inicial 1000) | Média |
| F8 | Validação de aposta (mínimo 1, máximo = saldo) | Alta |
| F9 | Tratamento de Ás (11 → 1 se estourar) | Alta |
| F10 | Múltiplas sessões simultâneas | Média |
| F11 | Limite de sessões configurável | Baixa |
| F12 | Timeout de inatividade (300s) | Média |

### Não-funcionais

| ID | Descrição |
|----|-----------|
| NF1 | Zero shell: não spawna `/bin/sh`, `subprocess`, `Popen` |
| NF2 | Zero eval: entrada do usuário nunca passa por `eval()`/`exec()` |
| NF3 | Conexão criptografável via TLS (futuro) ou WireGuard (externo) |
| NF4 | Tipagem estática: `mypy --strict` sem erros |
| NF5 | Layer architecture: Domain → Application → Transport → Display |
| NF6 | SOLID: DIP, OCP, SRP aplicados nas camadas |
| NF7 | Testes unitários para Domain (49) e Transport (16) |

## 3. Arquitetura

### 3.1 Camadas

```
┌─────────────────────────────────────────────┐
│              DISPLAY (RichRenderer)         │
│  ANSI escape sequences via Rich             │
├─────────────────────────────────────────────┤
│            APPLICATION (GameController)      │
│  Orquestração do jogo, dependente de        │
│  interfaces (DIP)                           │
├─────────────────────────────────────────────┤
│              TRANSPORT (TCPAdapter)          │
│  asyncio.StreamReader/Writer → ITransport   │
│  Sem shell, sem subprocess                  │
├─────────────────────────────────────────────┤
│               DOMAIN (Card, Deck, Hand)     │
│  Regras de negócio puras, zero I/O          │
└─────────────────────────────────────────────┘
```

### 3.2 SOLID aplicado

| Princípio | Exemplo |
|-----------|---------|
| **SRP** | `Card` só modela carta. `Deck` só gerencia baralho. `TCPAdapter` só faz I/O. |
| **OCP** | Nova regra de jogo? Implementa `IGameRules`. Novo transporte? Implementa `ITransportAdapter`. |
| **LSP** | Qualquer implementação de `ITransportAdapter` substitui a original sem quebrar o controller. |
| **ISP** | Interfaces pequenas: `ITransportAdapter` tem 4 métodos. `IDisplayRenderer` tem 10 métodos específicos. |
| **DIP** | `GameController` recebe interfaces por injeção, nunca instancia TCP ou renderer concreto. |

### 3.3 Fluxo de Conexão

```
Cliente (nc)          Servidor (py21ssh)
    │                        │
    ├── TCP connect ────────▶│
    │                        ├── TCPServer._on_connect()
    │                        │   ├── verifica limite de sessões
    │                        │   ├── cria TCPAdapter
    │                        │   ├── cria RichRenderer
    │                        │   └── cria asyncio.Task
    │                        │
    │◀── ANSI: welcome ─────│
    │─── aposta: "100" ────▶│
    │◀── ANSI: mesa ────────│
    │─── ação: "h" ────────▶│
    │◀── ANSI: mesa ────────│
    │─── ação: "s" ────────▶│
    │◀── ANSI: resultado ───│
    │─── "s" (continuar) ──▶│
    │◀── ANSI: goodbye ─────│
    │                        ├── adapter.close()
    │◀── TCP close ─────────│
```

## 4. Segurança

### 4.1 Isolamento do Adaptador TCP

O `TCPAdapter` é a única ponte entre o cliente e o jogo.
Ele **não possui** nenhum mecanismo de escape:

```python
# O que NÃO existe no código:
import subprocess       # ❌
os.system()             # ❌
eval() / exec()          # ❌
pty.spawn()             # ❌
```

### 4.2 Validação de entrada

Toda entrada do usuário passa por validação antes de ser usada:

| Entrada | Validação |
|---------|-----------|
| Aposta | `int()` com try/except, range check (≥1, ≤saldo) |
| Ação | match contra `{"h","hit","1","s","stand","2","d","double","3"}` |
| Continuar | match contra `{"s","sim","y","yes",""}` |

### 4.3 Mitigação de Ataques

| Ameaça | Mitigação |
|--------|-----------|
| Cliente digitar comandos shell | Não existe shell pra interpretar. Vira entrada inválida. |
| Buffer overflow | `asyncio.StreamReader` gerencia buffers internamente |
| DoS por muitas conexões | `max_concurrent` limita sessões simultâneas |
| Conexão ociosa | Timeout de 300s por `asyncio.wait_for` |
| Escrita em socket fechado | `_closed` flag + early return + log warning |

## 5. Dependências

| Pacote | Versão | Uso |
|--------|--------|-----|
| `rich>=13.0` | Produção | Renderização ANSI (via console com `force_terminal=True`) |
| `pytest>=8.0` | Dev | Testes unitários |
| `pytest-asyncio>=0.24` | Dev | Testes de corrotinas |
| `mypy>=1.8` | Dev | Type checking strict |
| `ruff>=0.3` | Dev | Linter + formatter |
| `pre-commit>=3.6` | Dev | Git hooks |

**Zero dependências de rede**: o transporte é `asyncio` puro da stdlib.

## 6. API de Camadas

### 6.1 Domain

```python
class Card:
    suit: Suit       # HEARTS, DIAMONDS, CLUBS, SPADES
    rank: Rank       # A, 2-10, J, Q, K
    value -> int     # 1-11
    is_ace -> bool
    display -> str   # "A♠", "K♥"

class Deck:
    shuffle()
    draw() -> Card
    remaining -> int
    is_empty -> bool

class Hand:
    add(card: Card)
    value -> int     # com ajuste de Ás
    is_bust -> bool
    is_blackjack -> bool
    can_double -> bool

class BlackjackRules:
    initial_deal(deck) -> tuple[Hand, Hand]
    player_hit(hand, deck)
    dealer_play(hand, deck)
    resolve(player, dealer) -> RoundResult
```

### 6.2 Transport

```python
class TCPAdapter:
    async write(text: str)
    async read_line() -> str
    async read_char() -> str
    terminal_width -> int
    async close()

class TCPServer:
    async start()
    async serve_forever()
    async stop()
```

### 6.3 Display

```python
class RichRenderer:
    welcome() -> str
    table(player, dealer, balance, bet, ...) -> str
    bet_prompt(balance) -> str
    action_prompt(hand, bet) -> str
    result(result, bet, balance) -> str
    bust() -> str
    goodbye(balance) -> str
    error(message) -> str
    prompt(message) -> str
```

## 7. Testes

| Suite | Arquivos | Testes |
|-------|----------|--------|
| Domain: Card | `test_card.py` | 11 |
| Domain: Deck | `test_deck.py` | 8 |
| Domain: Hand | `test_hand.py` | 14 |
| Domain: Rules | `test_rules.py` | 12 |
| Transport: Isolation | `test_tcp_adapter.py` | 2 |
| Transport: I/O | `test_tcp_adapter.py` | 14 |
| **Total** | | **65** |

## 8. Transportes Futuros

A arquitetura em camadas permite adicionar novos transportes
sem modificar domain, application ou display:

| Transporte | Implementação | Mudança necessária |
|------------|---------------|--------------------|
| **SSH (asyncssh)** | `SSHAdapter(ITransportAdapter)` | `transport/ssh_adapter.py` + `SSHServer` |
| **WebSocket** | `WSAdapter(ITransportAdapter)` | `transport/ws_adapter.py` + `WSServer` |
| **TLS** | `TLSAdapter(ITransportAdapter)` | Reusa `TCPAdapter` com `ssl_context` |

## 9. Licença

MIT