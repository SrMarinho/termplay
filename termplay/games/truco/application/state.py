from __future__ import annotations
from dataclasses import dataclass, field
from termplay.games.truco.conf import HAND_SIZE
from termplay.games.truco.domain.card import Card
from termplay.games.truco.domain.deck import Deck


@dataclass
class TrucoState:
    hands: list[list[Card]]    # one hand per player
    table: list[Card | None]   # card played this trick (None = not yet played)
    trick_order: list[int]     # player indices, current trick play order
    tricks: list[int | None]   # winning team per completed trick
    score: list[int]           # [team0_pts, team1_pts]
    stake: int                 # current round's point value
    vira: Card
    mao: int                   # index of first player this round
    current: int               # position in trick_order of active player
    envite: dict | None        # {"asker": idx, "offer": 3|6|9|12} or None
    folded: int | None         # team that folded (mão-de-onze), or None

    @classmethod
    def new(cls, num_players: int, mao: int, score: list[int] | None = None) -> TrucoState:
        deck = Deck()
        vira = deck.draw_one()
        hands = [deck.draw(HAND_SIZE) for _ in range(num_players)]
        order = [(mao + i) % num_players for i in range(num_players)]
        return cls(
            hands=hands,
            table=[None] * num_players,
            trick_order=order,
            tricks=[],
            score=score or [0, 0],
            stake=1,
            vira=vira,
            mao=mao,
            current=0,
            envite=None,
            folded=None,
        )

    @property
    def current_player(self) -> int:
        return self.trick_order[self.current]

    @property
    def all_played(self) -> bool:
        return all(c is not None for c in self.table)

    def plays_this_trick(self) -> list[tuple[int, Card]]:
        return [(i, c) for i, c in enumerate(self.table) if c is not None]

    def reset_table(self, lead: int) -> None:
        n = len(self.table)
        self.table = [None] * n
        start = self.trick_order.index(lead)
        self.trick_order = [self.trick_order[(start + i) % n] for i in range(n)]
        self.current = 0
