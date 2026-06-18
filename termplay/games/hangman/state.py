"""HangmanState — pure game state, zero I/O."""

from __future__ import annotations

from dataclasses import dataclass, field

from termplay.games.hangman.conf import MAX_WRONG


@dataclass
class HangmanState:
    """Shared hangman puzzle: a word, the set of guesses, wrong-count limit."""

    word: str
    guessed: set[str] = field(default_factory=set)
    wrong_marks: int = 0
    max_wrong: int = MAX_WRONG

    @property
    def wrong_letters(self) -> list[str]:
        return sorted(g for g in self.guessed if g not in self.word)

    @property
    def wrong(self) -> int:
        return len(self.wrong_letters) + self.wrong_marks

    @property
    def masked(self) -> str:
        return " ".join(c if c in self.guessed else "_" for c in self.word)

    @property
    def is_won(self) -> bool:
        return all(c in self.guessed for c in self.word)

    @property
    def is_lost(self) -> bool:
        return self.wrong >= self.max_wrong

    def guess_letter(self, letter: str) -> bool:
        """Register a single-letter guess. Returns True if correct."""
        letter = letter.upper()
        self.guessed.add(letter)
        return letter in self.word

    def guess_word(self, word: str) -> bool:
        """Attempt the whole word. Reveals it on hit; adds a wrong mark on miss."""
        if word.upper() == self.word:
            self.guessed.update(self.word)
            return True
        self.wrong_marks += 1
        return False
