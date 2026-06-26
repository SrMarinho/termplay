# Uno Rule Variants — Standard + Brazilian + UX Polish

## Context

Uno controller implements only basic rules. Missing: draw-then-play, initial card
effect, Wild+4 legality, and no rule variant system. User wants a ruleset selector
in room creation (Standard vs Brazilian 🇧🇷), post-game returning to homepage
(rooms screen), and stronger visual emphasis on the active player (including self).

**Brazilian rules selected by user:** stack +2/+4, draw-until-play, Wild+4 always legal.

---

## New File: `termplay/games/uno/ruleset.py`

```python
@dataclass
class UnoRuleset:
    draw_then_play: bool = False     # standard: may play drawn card if legal
    initial_card_effect: bool = False # first discard card applies action
    wild4_strict: bool = False        # wild4 illegal if non-wild card playable
    stack_draws: bool = False         # BR: +2/+4 accumulate across players
    draw_until_play: bool = False     # BR: draw until playable, then must play

    @classmethod
    def standard(cls) -> "UnoRuleset":
        return cls(draw_then_play=True, initial_card_effect=True, wild4_strict=True)

    @classmethod
    def brazilian(cls) -> "UnoRuleset":
        return cls(stack_draws=True, draw_until_play=True)  # wild4 always legal (all False)

    @classmethod
    def from_name(cls, name: str) -> "UnoRuleset":
        return {"standard": cls.standard, "br": cls.brazilian}.get(name, cls.standard)()
```

---

## `termplay/games/uno/state.py`

Add two fields to `UnoState`:
```python
pending_draws: int = 0        # accumulated draw count (stacking)
pending_draw_value: str = ""  # "draw2" or "wild4" — restricts what can stack
```

No change to `playable()` — controller handles stack filtering.

---

## `termplay/games/uno/controller.py`

**Constructor:** accept `UnoRuleset`; if `ruleset.initial_card_effect`, apply first
card effect after `UnoState.new()`:
- `skip` → `state.advance()`
- `reverse` → `state.direction = -1`, start from last player
- `draw2` → first player draws 2, `state.advance()`

**`run()` loop changes:**
1. Before broadcast, check if `state.pending_draws > 0` and player has no matching
   draw card → force-draw `pending_draws`, reset, advance, `continue`
2. Set `self._turn_deadline` then broadcast as before
3. Dispatch move: `(move_type, value)` tuple returned from `_get_move()`

**`_get_move()` refactor** — returns `(type, value)`:
- `"leave"` / `"pass"` / `"timeout"` / `("draw", None)` / `("play", idx)`
- Wild+4 strict check: if `ruleset.wild4_strict` and player has non-wild playable card → reject, notify, loop
- Stack constraint: if `pending_draws > 0`, only accept cards matching `pending_draw_value`

**New `_handle_draw(player, idx)`:**
- `draw_until_play=True`: loop `state.draw(idx, 1)` until playable card drawn → **auto-play** that card (call `_apply_move`)
- `draw_then_play=True`: draw 1; if drawn card playable → broadcast special state (`may_play_drawn=True`, `drawn_card_idx`), wait for play or "p"/"pass" → if timeout, advance turn
- Default (neither): draw 1, advance turn (current behavior)

**`_apply_effect()` with stack_draws:**
- `draw2`/`wild4`: accumulate `state.pending_draws += N`, set `state.pending_draw_value`, `advance()` (no skip — next player acts)

**Payload additions:**
```python
"pending_draws": self._state.pending_draws,
"may_play_drawn": bool,    # only when draw_then_play triggered
"drawn_card_idx": int,     # index of drawn card when may_play_drawn
```

---

## `termplay/engine/multiplayer.py`

Update `MpFactory` signature to accept `rules: str` as 4th arg:
```python
MpFactory = Callable[
    [Sequence[ITransportAdapter], list[str], list[bool], str],
    IMultiplayerController
]
```

---

## `termplay/games/uno/plugin.py`

```python
MultiplayerRegistry.register(
    "uno",
    lambda t, n, s, rules="standard": UnoController(t, n, s, UnoRuleset.from_name(rules))
)
```

Other game plugins (`velha`, `hangman`) ignore the 4th arg via default param.

---

## `termplay/engine/room.py`

Add `rules: str = "standard"` to `Room` dataclass.
Add `rules: str = "standard"` param to `RoomManager.create()`.

---

## `termplay/engine/server.py`

- `_handle_client`: extract `rules = str(first.get("rules") or "standard")`, pass to `_host_flow`
- `_host_flow`: pass `rules` to `RoomManager.create(rules=rules)`
- `_run_controller(room)`: call `factory(transports, names, stealth_flags, room.rules)`
- Broadcaster: include `rules` in UDP beacon if needed (nice-to-have)

---

## `termplay/gateway/server.py`

`_build_connect_payload`: add `"rules": str(msg.get("rules") or "standard")` to create_room payload.

---

## Browser

### `index.html`
Below game selector, add rules selector (initially visible only for uno):
```html
<select id="host-rules" class="field" style="width:auto">
  <option value="standard">Standard</option>
  <option value="br">🇧🇷 Brazilian</option>
</select>
```

### `app.js`
- `hostRoom()`: include `rules: document.getElementById("host-rules").value`
- Show/hide rules selector based on selected game (only uno has variants for now)
- `onMessage game_over`: call `showScreen("rooms")` helper instead of nothing

### `uno.js`
- `renderOver()`: "Back to rooms" button → call `actions.backToRooms()` (switch screen, no full reload)
- `render()`: `isMyTurn = state.current === state.you` → `els.handZone.classList.toggle("your-turn", isMyTurn)`
- `render()`: `pending_draws > 0` → show badge on discard pile showing accumulated draw count
- When `state.may_play_drawn=true`: only drawn card is playable; add "Pass" button in hand-info

### `style.css`
```css
.hand-zone.your-turn {
  border-top: 2px solid var(--gold);
  box-shadow: 0 -4px 24px rgba(233,196,106,.18);
}
.pending-draws-badge {
  /* absolute on discard-wrap, shows "+4" "+6" etc */
}
.card.drawn-option { border-color: var(--G); box-shadow: 0 0 0 3px var(--G),...; }
```

Also strengthen `.opponent.active` — currently just gold name + fan glow. Add scale or brighter glow.

---

## Verification

1. `pytest tests/ -q` — all 139 pass (+ new tests for ruleset)
2. Standard game: Wild+4 rejected if you have R:7 and top is R; draw gives option to play
3. Brazilian game: Player A plays +2, Player B plays +2, Player C must draw 4; draw loops until playable
4. Post-game: overlay → "Back to rooms" → rooms screen appears (no reload)
5. Self turn: hand-zone gets gold border; opponent turn: hand-zone returns to normal
