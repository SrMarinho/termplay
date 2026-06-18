"""Registro de jogos — Singleton que mantém classes de jogos disponíveis.

Padrão: Registry Pattern.
Responsabilidade: Registrar, buscar e listar jogos.
"""

from __future__ import annotations

from typing import ClassVar

from termplay.engine.game import IGame


class GameRegistry:
    """Registro global de jogos — singleton thread-safe."""

    _games: ClassVar[dict[str, type[IGame]]] = {}

    @classmethod
    def register(cls, game_class: type[IGame]) -> type[IGame]:
        """Decora uma classe de jogo para registrá-la automaticamente."""
        instance = game_class()
        name = instance.name
        if not name:
            raise ValueError(
                f"Jogo {game_class.__name__} deve ter atributo 'name'"
            )

        name_lower = name.lower()
        if name_lower in cls._games:
            raise ValueError(
                f"Jogo '{name}' já registrado como "
                f"{cls._games[name_lower].__name__}"
            )

        cls._games[name_lower] = game_class
        return game_class

    @classmethod
    def get(cls, name: str) -> type[IGame] | None:
        """Recupera um jogo pelo nome (case-insensitive)."""
        return cls._games.get(name.lower())

    @classmethod
    def list_games(cls) -> list[tuple[str, str]]:
        """Lista de tuplas (nome, descrição) ordenadas por nome."""
        return sorted(
            [
                (name, klass().description)
                for name, klass in cls._games.items()
            ],
            key=lambda x: x[0],
        )

    @classmethod
    def clear(cls) -> None:
        """Limpa todos os jogos registrados (usado em testes)."""
        cls._games.clear()
