"""Hangman constants and word bank (ASCII uppercase, no accents)."""

from __future__ import annotations

MAX_WRONG: int = 6

WORDS: list[str] = [
    "PYTHON",
    "TERMINAL",
    "COMPUTADOR",
    "TECLADO",
    "SERVIDOR",
    "ARQUIVO",
    "JANELA",
    "PROCESSO",
    "MEMORIA",
    "REDE",
    "CODIGO",
    "VARIAVEL",
    "FUNCAO",
    "PROGRAMA",
    "MONITOR",
]

# Hangman art indexed by wrong-guess count (0..MAX_WRONG).
STAGES: list[str] = [
    r"""
  +---+
  |   |
      |
      |
      |
      |
=========""",
    r"""
  +---+
  |   |
  O   |
      |
      |
      |
=========""",
    r"""
  +---+
  |   |
  O   |
  |   |
      |
      |
=========""",
    r"""
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========""",
    r"""
  +---+
  |   |
  O   |
 /|\  |
      |
      |
=========""",
    r"""
  +---+
  |   |
  O   |
 /|\  |
 /    |
      |
=========""",
    r"""
  +---+
  |   |
  O   |
 /|\  |
 / \  |
      |
=========""",
]
