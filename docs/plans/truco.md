# Plan: Truco Brasileiro

## Context

Implement Truco Brasileiro as a new game in termplay. Supports 1v1 and 2v2 (partners). Full envite system (Truco→Seis→Nove→Doze). Follows Blackjack's layered architecture (domain / application / display) — not UNO's flat structure.

---

## Truco Rules (BR)

- **Deck**: 40 cards — A,2,3,4,5,6,7,J,Q,K × 4 suits (remove 8,9)
- **Vira**: card turned up before deal; rank immediately above it becomes **manilha**
- **Manilha suit order** (strongest→weakest): ♣ > ♥ > ♠ > ♦
- **Base strength**: 3 > 2 > A > K > J > Q > 7 > 6 > 5 > 4 (manilhas beat all)
- **Round**: 3 tricks; best of 3 wins the round
  - First trick tie → whoever wins 2nd wins round
  - All tied → `mão` (first player) wins round
- **Points**: normal=2; after envite: Truco=3, Seis=6, Nove=9, Doze=12
- **Match**: first to 12 pts wins
- **Envite flow** (any player on their turn):
  - "truco" → opponent: accept (stake=3), raise to "seis", or run (prev_stake to asker)
  - Each raise: accept / raise next / run (prev_stake to asker)
  - Up to "doze" (12); if run: asker gets value before the raise
- **2v2**: players alternate teams (P0,P2=teamA; P1,P3=teamB); partners see each other's cards, hidden from opponents
- **Mão de onze**: when a team reaches 11 pts they choose to play or fold before the hand is revealed (2v2 only)

---

## Backend Architecture

```
termplay/games/truco/
├── __init__.py
├── conf.py                  # DECK_RANKS, SUIT_ORDER, WINNING_SCORE=12, TURN_TIMEOUT=20
├── plugin.py                # @GameRegistry.register + MultiplayerRegistry
├── ruleset.py               # TrucoRuleset(mode="2v2"|"1v1")
├── domain/
│   ├── __init__.py
│   ├── card.py              # Card(suit, rank); card_strength(card, vira) → int
│   ├── deck.py              # build_deck() → list[Card]; Deck class with draw()
│   └── rules.py             # trick_winner(plays, vira) → int|None; round_winner(tricks) → int|None
├── application/
│   ├── __init__.py
│   ├── context.py           # TrucoContext, Player; player_team(ctx, idx) → int
│   ├── state.py             # TrucoState: hands, table, tricks, score, stake, vira, mao, current, envite
│   ├── envite.py            # negotiate_envite(ctx, asker_idx) → int (final stake, 0=folded)
│   ├── trick_handler.py     # play_trick(ctx) → int|None (winning team, None=tie)
│   ├── round_handler.py     # play_round(ctx) → int (winning team); handles mão-de-onze
│   └── controller.py        # TrucoController.run() — match loop
└── display/
    ├── __init__.py
    ├── broadcaster.py       # broadcast(ctx), notify_private(ctx, player, text)
    └── input_reader.py      # get_play(ctx, player, idx) → int|None
                             # get_envite_response(ctx, player) → "accept"|"raise"|"run"
```

### Key types

```python
# domain/card.py
@dataclass(frozen=True)
class Card:
    suit: str   # "C","H","S","D"
    rank: str   # "3","2","A","K","J","Q","7","6","5","4"

def card_strength(card: Card, vira: Card) -> int:
    # manilhas → 100..103 by suit; base strength 0..9

# application/state.py
@dataclass
class TrucoState:
    hands: list[list[Card]]
    table: list[Card | None]        # played this trick (None = not played yet)
    tricks: list[int | None]        # which team won each of 3 tricks (None=tie/pending)
    score: list[int]
    stake: int
    vira: Card
    mao: int                        # first player this round
    current: int
    envite: dict | None             # {"asker": idx, "offer": 3|6|9|12} or None

# application/context.py
@dataclass
class Player:
    transport: ITransportAdapter
    name: str
    active: bool = True

@dataclass
class TrucoContext:
    players: list[Player]
    teams: list[list[int]]          # [[0,2],[1,3]] or [[0],[1]]
    state: TrucoState
    rules: TrucoRuleset
    log: GameLogger
    message: str = ""
    turn_deadline: float = 0.0
```

### State JSON (`"v": "truco.state"`)

```json
{
  "v": "truco.state",
  "phase": "play | envite | mao_de_onze | over",
  "your_hand": ["3C","7H","JC"],
  "partner_hand": ["AC","5S","QD"],
  "vira": "4D",
  "table": [null, "AH", null, "5C"],
  "tricks": [0, null, null],
  "score": [5, 8],
  "stake": 2,
  "envite": null,
  "mao": 0,
  "current": 2,
  "your_turn": true,
  "deadline": 1234567890.0,
  "you": 0,
  "players": ["Alice","Bob","Charlie","Diana"],
  "teams": [[0,2],[1,3]],
  "mode": "2v2",
  "message": "Bob jogou AH"
}
```

### Plugin

```python
MultiplayerRegistry.register(
    "truco",
    lambda t, n, s, rules: TrucoController(t, n, s, TrucoRuleset.from_spec(rules)),
)
```

---

## Frontend

```
termplay/gateway/static/games/truco/
├── index.js        # registerView("truco.state", TrucoView)
└── truco.css       # table layout, hand, score panel, envite overlay
```

Reuse `makeCard()` from `../../core/cards.js` and `.bj-card` CSS primitives from `style.css`.

**UI sections:**
- Top bar: score (Team A vs Team B) + vira card
- Center table: played cards (4 or 2 slots)
- Trick history: 3 pips per team (won/lost/tie)
- Bottom: player's hand (clickable), action bar (Truco / Aceitar / Aumentar / Correr)
- Envite overlay appears when `state.envite !== null && !state.your_turn`

---

## Files to modify (existing)

| File | Change |
|---|---|
| `termplay/gateway/static/index.html` | Add game-tile `data-game="truco"` (2–4 players) |
| `termplay/gateway/static/games/games.js` | Add `import "./truco/index.js"` |
| `termplay/gateway/static/core/rules-modal.js` | Add `truco` rule defs: mode (`1v1`/`2v2`) |

---

## Implementation order

1. `domain/` — Card, deck, trick_winner, round_winner (pure, no I/O)
2. `application/state.py` + `context.py`
3. `display/input_reader.py` + `display/broadcaster.py`
4. `application/envite.py`
5. `application/trick_handler.py` + `round_handler.py`
6. `application/controller.py` + `plugin.py` + `ruleset.py` + `conf.py`
7. Frontend: `truco/index.js` + `truco.css`
8. Wire: `index.html`, `games.js`, `rules-modal.js`

---

## Verification

1. 2-player session: host selects Truco → lobby tile appears
2. Game starts: vira shown, 3 cards dealt to each
3. Play card → table updates for both players
4. Say "truco" → envite overlay on opponent side
5. Accept/run → stake updates, round resolves
6. 3 tricks → round scored, new round dealt
7. First to 12 → game over screen
8. 4-player: partner's hand visible, alternating seats correct
