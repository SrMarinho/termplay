# termplay — Architecture

## Component Map

```
termplay/
├── config/
│   └── settings.py          nickname, last_host/port (JSON persistence)
│
├── engine/                  ← NO UI imports allowed
│   ├── interfaces.py        ITransportAdapter
│   ├── protocol.py          ACTION_* / TYPE_* constants + encode/decode
│   ├── protocol_adapter.py  ProtocolServerAdapter (JSON over TCP, server-side)
│   ├── transport/
│   │   └── queued_adapter.py  QueuedAdapter (relay: socket → game queue)
│   ├── room.py              RoomPlayer, Room, RoomManager
│   ├── server.py            TermPlayServer (TCP P2P, embeds broadcaster)
│   ├── discovery.py         RoomBroadcaster (UDP tx) + RoomDiscoverer (UDP rx)
│   ├── registry.py          GameRegistry (@register decorator)
│   └── game.py              IGame interface
│
├── games/
│   └── blackjack/
│       ├── plugin.py        @GameRegistry.register("blackjack", ...)
│       ├── conf.py          constants (STARTING_BALANCE, MIN_BET, ...)
│       ├── domain/          Card, Deck, Hand, BlackjackRules — zero I/O
│       ├── display/
│       │   └── renderer.py  RichRenderer (ANSI via Rich → TCP string)
│       └── application/
│           └── multiplayer_controller.py  concurrent round orchestration
│
└── frontends/
    ├── textual_app.py       TermplayTUIApp (App root, server lifecycle)
    ├── net.py               ServerConnection (TCP client, recv loop)
    ├── textual_adapter.py   TextualTransportAdapter (solo game bridge)
    └── screens/
        ├── home.py             Main menu
        ├── game_select.py      Game table (solo nav OR modal select_mode)
        ├── game.py             Solo game screen
        ├── multiplayer_menu.py Create / Join
        ├── create_room.py      Game select → server start → waiting room
        ├── join_room.py        LAN discovery DataTable + manual fallback
        ├── waiting_room.py     Lobby + WhatsApp-style chat
        └── mp_game.py          In-game render + Hit/Stand/Double buttons
```

---

## Layer Dependencies

```
config/        ←  stdlib only
domain/        ←  stdlib only
engine/        ←  domain/ + stdlib + asyncio   (zero frontend/game imports)
games/*/       ←  engine/interfaces + domain/  (zero frontend imports)
frontends/     ←  engine/ + games/ + textual + config/
```

**Inversion of control**: `MultiplayerGameController` receives a list of
`ITransportAdapter`. During multiplayer the adapters are `ProtocolServerAdapter`
(JSON over TCP); during solo they are `TextualTransportAdapter` (Rich widget I/O).
The controller is identical in both cases.

---

## Multiplayer Flow

```
Host TUI (TermplayTUIApp)
    │
    ├─ CreateRoomScreen._create()
    │     │  push_screen_wait(GameSelectScreen(select_mode=True))
    │     │       → returns game_name
    │     │
    │     ├─ app.start_embedded_server(game_name)
    │     │       TermPlayServer("0.0.0.0", port, game_name)
    │     │       server.start() → asyncio.start_server + broadcaster.run()
    │     │
    │     └─ app.connect_server("127.0.0.1", port)
    │           ServerConnection.connect() → _listen() worker
    │           send ACTION_CREATE_ROOM → WaitingRoomScreen
    │
    ├─ WaitingRoomScreen (lobby)
    │     │  receives TYPE_ROOM_STATE → updates player list
    │     │  chat: ACTION_CHAT ↔ TYPE_CHAT (WhatsApp style)
    │     │  host sends ACTION_START_GAME
    │     │
    │     └─ on TYPE_GAME_START:
    │           mp = MpGameScreen()
    │           app.set_message_handler(mp.on_server_message)  # before push!
    │           app.push_screen(mp)
    │
    └─ MpGameScreen
          buffers TYPE_GAME_RENDER until mounted (_pending list)
          receives renders → RichLog.clear() on box chars, append otherwise
          sends ACTION_GAME_INPUT → relayed to controller input queue

Guest TUI: same flow but send ACTION_JOIN_ROOM; JoinRoomScreen discovers
           rooms via RoomDiscoverer (UDP, TTL 6s) and shows live DataTable.
```

---

## Server-Side Flow

```
TermPlayServer._handle_client()
    │
    ├─ ACTION_CREATE_ROOM → _host_flow(adapter, name)
    │     RoomManager.create(player)
    │     broadcaster.update(host, game, players, status, port)
    │     loop: recv ACTION_START_GAME / ACTION_CHAT
    │     room.ready.set()
    │     broadcaster.update(status="playing")
    │     broadcast TYPE_GAME_START to all
    │     asyncio.create_task(_relay(adapter, room, name))
    │     await _run_controller(room)   ← blocks until game ends
    │
    ├─ ACTION_JOIN_ROOM → _guest_flow(adapter, name, code)
    │     RoomManager.get(code) or first()
    │     room.add_player(player)
    │     poll room.ready with asyncio.wait_for(0.3s timeout)
    │     asyncio.create_task(_relay(adapter, room, name))
    │     await room.game_complete.wait()
    │
    └─ _run_controller(room)
          MultiplayerGameController(transports, BlackjackRules(), names)
          controller.run()
              asyncio.gather(bets)          # simultaneous
              asyncio.gather(player turns)  # simultaneous
              each action → broadcast_tables(all_active)
          room.game_complete.set()
          broadcast TYPE_GAME_OVER
```

---

## UDP Discovery

```
RoomBroadcaster (server process)       RoomDiscoverer (guest TUI)
─────────────────────────────          ──────────────────────────
socket(AF_INET, SOCK_DGRAM)            create_datagram_endpoint(
setsockopt(SO_BROADCAST, 1)              _UDPDiscoveryProtocol,
setblocking(False)                       "0.0.0.0:4444",
                                         allow_broadcast=True)
loop every 2s:
  payload = json.dumps({               datagram_received(data, addr):
    host, game, players,                 ip = addr[0]
    max_players, status, port            rooms[ip] = DiscoveredRoom(
  })                                       seen_at=time.monotonic()
  sock_sendto(                           )
    payload,
    ("255.255.255.255", 4444)
  )                                    rooms() → [r for r in rooms
                                         if monotonic()-r.seen_at < 6.0]
```

---

## Message Dispatch (TUI side)

```
ServerConnection._listen() worker
    │
    │  msg = await conn.recv()   # JSON line from TCP
    │
    └─ await app._msg_handler(msg)
            │
            └─ set by each screen on mount / before push:
                 WaitingRoomScreen.on_server_message   (lobby)
                 MpGameScreen.on_server_message        (in-game)
```

**Race condition fix**: when TYPE_GAME_START arrives, `MpGameScreen` is created
and its handler set **before** `push_screen()`. Early `TYPE_GAME_RENDER` messages
arriving before `on_mount` are buffered in `_pending` and replayed on mount.

---

## Chat Rendering

```python
# waiting_room.py
def _chat_renderable(name: str, text: str, is_mine: bool) -> object:
    if is_mine:
        nick = Text(name, style="bold white on dark_blue")
    else:
        nick = Text(name, style=f"bold {_nick_color(name)}")   # hash → color
    return Text.assemble(nick, Text(f": {text}", style="white"))
```

Own nick: white bold on blue background.
Others: deterministic color from `hash(name) % 6`.
Single-line per message — Twitch-chat style.

---

## Action Prompt Design

`action_prompt()` intentionally uses **plain text** (no Rich Panel).
Plain text has no box-drawing characters, so `MpGameScreen` does **not**
call `RichLog.clear()`. The prompt appends below the table instead of
replacing it — table stays visible throughout the player's turn.

Box characters (`╭╰╔╚┌└`) from Panels trigger `log.clear()` in `MpGameScreen`,
which is the mechanism used to refresh the game table on each state change.
