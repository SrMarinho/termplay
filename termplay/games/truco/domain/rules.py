from __future__ import annotations
from termplay.games.truco.domain.card import Card, card_strength


def trick_winner(plays: list[tuple[int, Card]], vira: Card) -> int | None:
    """Return winning team index, or None if tied."""
    strengths = [(card_strength(card, vira), team) for team, card in plays]
    max_s = max(s for s, _ in strengths)
    top_teams = [team for s, team in strengths if s == max_s]
    return top_teams[0] if len(set(top_teams)) == 1 else None


def round_winner(tricks: list[int | None], mao_team: int) -> int | None:
    """
    tricks: completed trick results (int = winning team, None = tie).
    Returns winning team or None if undecided.
    """
    n = len(tricks)
    if n == 0:
        return None

    wins = [tricks.count(0), tricks.count(1)]
    if wins[0] >= 2:
        return 0
    if wins[1] >= 2:
        return 1

    if n >= 2 and tricks[0] is None:
        # Trick 1 tied: winner of trick 2 wins the round
        if tricks[1] is not None:
            return tricks[1]
        # Both tricks 1 and 2 tied — fall through to trick 3 check

    if n < 3:
        return None

    # All 3 tricks played
    if all(t is None for t in tricks):
        return mao_team
    for t in tricks:
        if t is not None:
            return t
    return mao_team
