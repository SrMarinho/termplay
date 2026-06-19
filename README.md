# termplay — multiplayer games in the terminal

Terminal game platform with a full Textual TUI. Play over LAN with friends — no browser, no server setup, just install and run.

**Bundled games:** Uno · Blackjack · Forca (Hangman) · Velha (Tic-tac-toe)

## Install

```bash
pip install git+https://github.com/SrMarinho/termplay.git
```

Requires Python 3.11+.

## Play

```bash
termplay
```

The TUI walks you through everything: solo games, creating a room, or joining a friend's room on the same network.

### Multiplayer (LAN)

**Host:**
1. Open `termplay` → Multiplayer → Create Room → pick a game → wait for friends → Start

**Guest:**
1. Open `termplay` → Multiplayer → rooms appear automatically via LAN discovery → Join

No manual IP needed — rooms are discovered automatically. If discovery fails, join by IP/port manually.

## Development

```bash
git clone https://github.com/SrMarinho/termplay.git
cd termplay
uv sync --extra dev

uv run python -m pytest tests/ -q
uv run python -m mypy termplay/ --strict
uv run python -m ruff check termplay/
```

## Architecture

```
termplay/
├── engine/          # transport-agnostic core (rooms, protocol, server, game log)
├── frontends/       # Textual TUI (screens, net client)
├── games/           # game plugins (blackjack, uno, hangman, tictactoe)
└── config/          # persistent settings (nickname)
```

Games register themselves via `GameRegistry` (solo) and `MultiplayerRegistry` (multiplayer).
Server speaks newline-delimited JSON over TCP. Client is a pure Textual shell — no raw ANSI.

## Adding a game

1. Create `termplay/games/<name>/plugin.py` implementing `IGame` and/or `IMultiplayerController`.
2. Register with `@GameRegistry.register(...)` / `MultiplayerRegistry.register(...)`.
3. Import the plugin in `textual_app.py` for auto-registration.

See `termplay/games/uno/` for a full multiplayer example.
