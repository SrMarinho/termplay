# Velha TUI Completo — Design Spec

**Date:** 2026-06-19  
**Status:** Approved  
**Scope:** Replace text-based Velha with native Textual TUI for both solo and multiplayer.

---

## Goal

- 3x3 interactive grid with arrow-key navigation and Enter to place mark
- Solo mode: play vs bot (Easy = random, Hard = minimax), preceded by difficulty modal
- Multiplayer mode: native TUI grid instead of text ASCII board
- All rendered via Textual widgets (no RichLog ASCII art for Velha)

---

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `termplay/games/tictactoe/bot.py` | `VelhaBot` AI + `VelhaBotTransportAdapter` |
| `termplay/frontends/screens/velha_screen.py` | `VelhaDifficultyModal` + `VelhaScreen` (solo) |
| `termplay/frontends/screens/velha_mp_screen.py` | `VelhaMpScreen` (multiplayer) |

### Modified Files

| File | Change |
|------|--------|
| `termplay/games/tictactoe/controller.py` | Send JSON state per player instead of ASCII text |
| `termplay/games/tictactoe/plugin.py` | Use `VelhaBotTransportAdapter` instead of Uno bot |
| `termplay/frontends/screens/game_select.py` | Route "Velha" → `VelhaDifficultyModal` → `VelhaScreen` |
| `termplay/frontends/screens/waiting_room.py` | Route `TYPE_GAME_START` with `game="velha"` → `VelhaMpScreen` |

---

## Server Protocol

`TicTacToeController` sends one JSON line per player via `transport.write()`. Each player receives their own copy with `your_mark` set:

```json
{"v": "velha.state", "cells": ["X", " ", "O", " ", " ", " ", " ", " ", " "],
 "turn": "X", "phase": "play", "your_mark": "X", "winner": null}
```

| Field | Values | Notes |
|-------|--------|-------|
| `v` | `"velha.state"` | Version/type tag |
| `cells` | `list[str]` (len=9) | `"X"`, `"O"`, or `" "` |
| `turn` | `"X"` \| `"O"` \| `""` | Whose turn (empty after game over) |
| `phase` | `"play"` \| `"over"` | Game phase |
| `your_mark` | `"X"` \| `"O"` \| `""` | Spectators get `""` |
| `winner` | `"X"` \| `"O"` \| `null` | `null` = draw or in-progress |

Input from client: plain cell number `"1"`–`"9"` (1-indexed, same as current).  
Quit: `"q"`.

---

## Component: VelhaBot (`bot.py`)

```python
class VelhaBot:
    @staticmethod
    def easy_move(cells: list[str]) -> int:
        """Random empty cell index (0-8)."""

    @staticmethod
    def hard_move(cells: list[str], mark: str) -> int:
        """Minimax: returns best cell index (0-8). Never loses."""
```

```python
class VelhaBotTransportAdapter(ITransportAdapter):
    """Plugs into TicTacToeController as a player transport.

    Parses velha.state JSON from write(), picks move via VelhaBot,
    returns 1-indexed cell number via read_line().
    """
```

Difficulty is set at construction: `VelhaBotTransportAdapter(difficulty="easy"|"hard")`.

---

## Component: VelhaDifficultyModal

`ModalScreen[str]` — dismisses with `"easy"` or `"hard"`.

Layout (centered box, 36 wide):
```
┌─ Dificuldade ──────────────────┐
│   [ Fácil ]    [ Difícil ]     │
└────────────────────────────────┘
```

Arrow keys cycle focus between buttons. Enter selects.

---

## Component: VelhaScreen (solo)

`Screen[None]` — launched after difficulty modal resolves.

### Layout (centered, all elements)

```
         JOGO DA VELHA
         Você: X  Bot: O

    ┌───┬───┬───┐
    │ X │   │ O │
    ├───┼───┼───┤
    │   │ X │   │
    ├───┼───┼───┤
    │   │   │   │
    └───┴───┴───┘

       Sua vez (X)
```

- Grid: 3×3 of `Button` widgets inside Textual `Grid(id="board")`
- Cursor cell: `variant="warning"` (yellow highlight)
- X cells: `variant="error"` (red), disabled
- O cells: `variant="primary"` (blue), disabled
- Empty non-cursor cells: `variant="default"`, disabled (navigation only via keys)

### Bindings

| Key | Action |
|-----|--------|
| `up` | Move cursor up (wraps row) |
| `down` | Move cursor down (wraps row) |
| `left` | Move cursor left (wraps col) |
| `right` | Move cursor right (wraps col) |
| `enter` / `space` | Place human mark on cursor cell |
| `escape` | Return to game select |

### Bot flow

1. Human presses Enter → mark placed on cursor cell
2. Check winner/draw → if over, show result label + `[Nova Partida]` / `[Sair]` buttons
3. If not over → `asyncio.sleep(0.4)` → bot picks move → place bot mark → check again

### State managed in-screen (no transport needed for solo)

---

## Component: VelhaMpScreen (multiplayer)

`Screen[None]` — pushed by `WaitingRoomScreen` when `TYPE_GAME_START` with `game="velha"`.

### Layout

Same centered grid as `VelhaScreen`, plus:
- Status bar: `"Vez de X (Oponente)"` or `"Sua vez! (X)"`
- `[Sair]` button (sends `"q"` to server)

### Message handling

Registers via `app.set_message_handler(self.on_server_message)` on mount.

```
TYPE_GAME_RENDER → parse JSON → update grid cells + turn label
TYPE_GAME_OVER   → disable grid, show result
TYPE_ERROR fatal → pop_screen
```

`on_server_message` signature matches `MpGameScreen` (dict → Awaitable[None]).

### Input

- Arrow keys: move local cursor (only visually; no server round-trip)
- Enter: send `str(cursor + 1)` to server via `app.connection.send(action=ACTION_GAME_INPUT, text="N")`
- Input blocked when `phase == "over"` or it's not your turn (cursor still moveable, Enter ignored)

### Stealth mode

When `get_stealth()` is true: hide grid, show `RichLog` with raw JSON lines (same disguise pattern as `MpGameScreen`).

---

## Modified: game_select.py

Add case alongside Uno:

```python
if game_name.lower() == "velha":
    from termplay.frontends.screens.velha_screen import VelhaDifficultyModal, VelhaScreen

    def start_velha(difficulty: str | None) -> None:
        self.app.push_screen(VelhaScreen(difficulty=difficulty or "easy"))

    self.app.push_screen(VelhaDifficultyModal(), start_velha)
```

---

## Modified: waiting_room.py

Add case in `TYPE_GAME_START` handler:

```python
elif game.lower() == "velha" and not get_stealth():
    from termplay.frontends.screens.velha_mp_screen import VelhaMpScreen
    screen = VelhaMpScreen()
```

---

## Modified: controller.py

Replace `_board_pretty` and `_board_log` with `_state_json(player)`:

```python
def _state_json(self, state: TicTacToeState, phase: str, turn: str, player: _Player) -> str:
    import json
    return json.dumps({
        "v": "velha.state",
        "cells": state.cells,
        "turn": turn,
        "phase": phase,
        "your_mark": player.mark,
        "winner": state.winner(),
    }) + "\r\n"
```

All `_broadcast_board` calls replaced with per-player `_state_json` writes.

---

## Error Handling

- Invalid cell (occupied/out-of-range): server sends existing error text; `VelhaMpScreen` ignores (client prevents invalid attempts via UI)
- Connection drop: `TYPE_ERROR fatal=True` → pop screen
- Bot crash (should not happen with minimax): log + treat as draw

---

## Out of Scope

- Replay / undo
- Time limits per turn
- Spectator TUI (spectators receive `your_mark=""` and see read-only grid — phase 2)
- Online ranking
