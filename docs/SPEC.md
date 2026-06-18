# termplay — Technical Specification (SPEC)

## 1. Overview

**termplay** is a multiplayer card-game platform playable entirely in the terminal.
Players run `uv run termplay` and get a full Textual TUI — game lobby, LAN room discovery,
real-time chat, and concurrent multiplayer rounds.

The engine is transport-agnostic: game logic knows nothing about Textual, TCP, or JSON.
New games and new frontends can be added independently.

**Target audience**: LAN parties, intranet, local development.

---

## 2. Functional Requirements

| ID | Description | Priority |
|----|-------------|----------|
| F1 | Solo Blackjack via TUI (full session) | High |
| F2 | Create a multiplayer room (embedded P2P server) | High |
| F3 | Discover LAN rooms via UDP broadcast | High |
| F4 | Join a room by selecting from live discovery table | High |
| F5 | Manual IP/port fallback for join | Medium |
| F6 | Real-time waiting room with WhatsApp-style chat | High |
| F7 | Host starts game when ≥ 2 players present | High |
| F8 | All players bet simultaneously (concurrent) | High |
| F9 | All players take turns simultaneously (concurrent) | High |
| F10 | Table broadcast to all players after every action | High |
| F11 | Hit / Stand / Double Down per player | High |
| F12 | Dealer draws to 17 (stand on soft 17) | High |
| F13 | Natural Blackjack pays 3:2 | High |
| F14 | Ace adjusts 11 → 1 to avoid bust | High |
| F15 | Starting balance 1000, min bet 1 | Medium |
| F16 | Game selection screen (extensible registry) | Medium |
| F17 | Last-used host/port persisted across sessions | Low |

---

## 3. Non-Functional Requirements

| ID | Description |
|----|-------------|
| NF1 | No shell: no `subprocess`, `Popen`, `os.system`, `pty.spawn` |
| NF2 | No eval: user input never touches `eval()` / `exec()` |
| NF3 | Static typing: `mypy --strict` zero errors |
| NF4 | Layered architecture: Domain → Engine → Games → Frontends |
| NF5 | Engine has zero UI imports (pure network + asyncio logic) |
| NF6 | Games have zero frontend imports (pure game logic) |
| NF7 | 111 tests, all passing |

---

## 4. Architecture

### 4.1 Layer Diagram

```
┌──────────────────────────────────────────────────────────┐
│  FRONTENDS  (termplay/frontends/)                        │
│  Textual TUI — screens, widgets, textual_app.py          │
│  TextualTransportAdapter — solo game I/O bridge          │
├──────────────────────────────────────────────────────────┤
│  ENGINE  (termplay/engine/)                              │
│  TermPlayServer — TCP P2P server (host embeds it)        │
│  ProtocolServerAdapter — JSON protocol over TCP          │
│  QueuedAdapter — relay between socket and game loop      │
│  RoomManager — room lifecycle (create / join / remove)   │
│  RoomBroadcaster — UDP beacon every 2s (SO_BROADCAST)    │
│  RoomDiscoverer  — UDP listener, TTL-6s room list        │
│  GameRegistry — plugin registry (@register decorator)    │
├──────────────────────────────────────────────────────────┤
│  GAMES  (termplay/games/<name>/)                         │
│  Blackjack: domain/, display/, application/              │
│  IGame interface — engine only talks to this             │
├──────────────────────────────────────────────────────────┤
│  CONFIG  (termplay/config/)                              │
│  settings.py — nickname, last_host/port (JSON file)      │
└──────────────────────────────────────────────────────────┘
```

### 4.2 Import Rules

```
domain/        →  stdlib only
engine/        →  domain/ + stdlib + asyncio  (NO frontend imports)
games/*/       →  engine/interfaces + domain/ (NO frontend imports)
frontends/     →  engine/ + games/ + textual
config/        →  stdlib only
```

### 4.3 LAN Multiplayer Flow

```
Host TUI                    Server (embedded)           Guest TUI
───────────────             ─────────────────           ──────────────
push_screen_wait            start()                     RoomDiscoverer
  GameSelectScreen            broadcaster.run()    ←──  sees beacon
    → game_name=...
start_embedded_server       TermPlayServer              join: selects room
connect("127.0.0.1", port)                              connect(ip, port)
ACTION_CREATE_ROOM   ──────▶ _host_flow()
                              RoomManager.create()
                              broadcaster.update(...)
                                                   ◀── ACTION_JOIN_ROOM
WaitingRoomScreen    ◀──── TYPE_ROOM_STATE ────────▶   WaitingRoomScreen
  (chat, players)                                         (chat, players)
ACTION_START_GAME    ──────▶ room.ready.set()
                              TYPE_GAME_START ─────▶     MpGameScreen
MpGameScreen                  _run_controller()
  concurrent bet/play ◀──── TYPE_GAME_RENDER ─────▶     concurrent bet/play
```

### 4.4 Concurrent Round Flow

```
_play_round()
  │
  ├── asyncio.gather(bet_prompt for each player)       # simultaneous
  ├── asyncio.gather(_get_bet for each player)         # simultaneous
  │
  ├── deal cards
  ├── broadcast initial table to all
  │
  ├── asyncio.gather(_play_turn for each player)       # simultaneous
  │     each turn:
  │       broadcast_tables(all) → action_prompt(player)
  │       → get_action → hit/stand/double
  │       → broadcast_tables(all) after each action
  │
  ├── dealer draws
  ├── resolve all results
  └── broadcast final table + individual results
```

---

## 5. Protocol (Engine ↔ TUI)

All messages are newline-delimited JSON over TCP.

### Client → Server (actions)

| `action` | Fields | Description |
|----------|--------|-------------|
| `create_room` | `name` | Host creates room |
| `join_room` | `name`, `code` | Guest joins (code="" = auto-join first room) |
| `start_game` | — | Host starts game |
| `game_input` | `text` | In-game input (bet, hit/stand/double) |
| `chat` | `text` | Chat message |
| `leave` | — | Leave room |

### Server → Client (types)

| `type` | Fields | Description |
|--------|--------|-------------|
| `room_created` | `code`, `you` | Room created confirmation |
| `room_joined` | `code`, `you` | Join confirmation |
| `room_state` | `players`, `can_start`, ... | Lobby update |
| `game_start` | — | Game is starting |
| `game_render` | `content` | ANSI render (table, prompts) |
| `game_over` | — | Game ended |
| `chat` | `name`, `text` | Chat message broadcast |
| `error` | `message`, `fatal` | Error (fatal=true closes connection) |

---

## 6. LAN Discovery

```
Server (broadcaster)                    Clients (discoverer)
─────────────────────                   ────────────────────
socket UDP SO_BROADCAST                 socket UDP listen 0.0.0.0:4444
every 2s → sendto(                      datagram_received():
  255.255.255.255:4444,                   parse JSON → DiscoveredRoom
  JSON{host,game,players,                 rooms[ip] = room
       max_players,status,port}         )
)
                                        rooms() → filter TTL < 6s
```

**Cross-platform**: `reuse_port=hasattr(socket, "SO_REUSEPORT")` (Linux/macOS only).

---

## 7. Game Plugin System

```python
# termplay/games/blackjack/plugin.py
from termplay.engine.registry import GameRegistry

@GameRegistry.register("blackjack", "Classic casino card game")
class BlackjackGame(IGame):
    async def run(self, transport: ITransportAdapter) -> None: ...
```

`GameSelectScreen` calls `GameRegistry.list_games()` to populate the table.
Adding a new game = new directory + `@register` decorator + import in `textual_app.py`.

---

## 8. Key Files

| File | Role |
|------|------|
| `termplay/frontends/textual_app.py` | App root, server lifecycle, message dispatch |
| `termplay/frontends/screens/home.py` | Main menu |
| `termplay/frontends/screens/multiplayer_menu.py` | Create / Join |
| `termplay/frontends/screens/create_room.py` | Game select → start server → waiting room |
| `termplay/frontends/screens/join_room.py` | LAN discovery table + manual fallback |
| `termplay/frontends/screens/waiting_room.py` | Lobby + WhatsApp chat |
| `termplay/frontends/screens/mp_game.py` | In-game render + action buttons |
| `termplay/frontends/screens/game_select.py` | Game list (solo or modal select) |
| `termplay/engine/server.py` | TCP P2P server + room coordinator |
| `termplay/engine/discovery.py` | UDP broadcast + discovery |
| `termplay/engine/room.py` | RoomManager, RoomPlayer |
| `termplay/engine/protocol_adapter.py` | JSON protocol adapter (server-side) |
| `termplay/engine/registry.py` | GameRegistry plugin system |
| `termplay/games/blackjack/application/multiplayer_controller.py` | Concurrent round orchestration |
| `termplay/games/blackjack/display/renderer.py` | ANSI renders via Rich |

---

## 9. Dependencies

| Package | Version | Use |
|---------|---------|-----|
| `textual>=0.70` | Production | TUI framework |
| `rich>=13.0` | Production | ANSI rendering |
| `pytest>=8.0` | Dev | Unit tests |
| `pytest-asyncio>=0.24` | Dev | Async test support |
| `mypy>=1.8` | Dev | Strict type checking |
| `ruff>=0.3` | Dev | Lint + format |

---

## 10. Tests

| Suite | File | Count |
|-------|------|-------|
| Domain: Card | `test_domain/test_card.py` | 11 |
| Domain: Deck | `test_domain/test_deck.py` | 8 |
| Domain: Hand | `test_domain/test_hand.py` | 14 |
| Domain: Rules | `test_domain/test_rules.py` | 12 |
| Transport: TCP | `test_transport/test_tcp_adapter.py` | 16 |
| Transport: Queued | `test_transport/test_queued_adapter.py` | ~10 |
| Engine | `test_engine/` | ~20 |
| Config | `test_config/` | ~10 |
| Frontends | `test_frontends/` | ~10 |
| **Total** | | **111** |

---

## 11. Security

| Threat | Mitigation |
|--------|------------|
| Shell injection | No shell exists. Input is JSON-parsed, then matched against whitelist. |
| Buffer overflow | `asyncio.StreamReader` manages buffers internally. |
| Malformed JSON | `try/except ValueError` in `recv_control()` → returns `{}` (ignored). |
| Idle connections | Guest loop has `asyncio.wait_for(timeout=0.3)` polling `room.ready`. |
| Socket write after close | `writer.is_closing()` guard in `send_control`. |

---

## 12. License

MIT
