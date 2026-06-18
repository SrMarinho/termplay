"""Testes do GameRegistry — núcleo da engine de plugins."""

from __future__ import annotations

from typing_extensions import override

from termplay.engine.game import IGame
from termplay.engine.interfaces import ITransportAdapter
from termplay.engine.registry import GameRegistry


class _FakeGame(IGame):
    """Jogo fake para testes."""

    name = "TestGame"

    @property
    @override
    def description(self) -> str:
        return "Um jogo de teste"

    @override
    async def run(self, transport: ITransportAdapter) -> None:
        pass

    @override
    async def show_help(self, transport: ITransportAdapter) -> None:
        pass


class _FakeGame2(IGame):
    """Outro jogo fake para testes."""

    name = "OutroJogo"

    @property
    @override
    def description(self) -> str:
        return "Segundo jogo"

    @override
    async def run(self, transport: ITransportAdapter) -> None:
        pass

    @override
    async def show_help(self, transport: ITransportAdapter) -> None:
        pass


class TestGameRegistry:
    """Testes do GameRegistry (Singleton registry pattern)."""

    def setup_method(self) -> None:
        """Limpa o registro antes de cada teste."""
        GameRegistry.clear()

    def teardown_method(self) -> None:
        """Limpa após cada teste."""
        GameRegistry.clear()

    def test_register_adds_game(self) -> None:
        """register() adiciona um jogo ao registro."""

        @GameRegistry.register
        class MyGame(_FakeGame):
            pass

        assert GameRegistry.get("testgame") is MyGame

    def test_get_returns_none_for_unknown(self) -> None:
        """get() retorna None para jogo desconhecido."""
        assert GameRegistry.get("nonexistent") is None

    def test_get_case_insensitive(self) -> None:
        """get() é case-insensitive."""

        @GameRegistry.register
        class MyGame(_FakeGame):
            pass

        assert GameRegistry.get("TESTGAME") is MyGame
        assert GameRegistry.get("testgame") is MyGame
        assert GameRegistry.get("TestGame") is MyGame

    def test_list_games_returns_sorted(self) -> None:
        """list_games() retorna jogos ordenados."""

        @GameRegistry.register
        class Z(_FakeGame2):
            pass

        @GameRegistry.register
        class A(_FakeGame):
            pass

        games = GameRegistry.list_games()
        assert len(games) == 2
        # Ordenado por nome (segundo jogo primeiro: "OutroJogo" < "TestGame")
        assert games[0][0] == "outrojogo"
        assert games[1][0] == "testgame"

    def test_list_empty_registry(self) -> None:
        """list_games() retorna lista vazia quando não há jogos."""
        assert GameRegistry.list_games() == []

    def test_clear_removes_all(self) -> None:
        """clear() remove todos os jogos registrados."""

        @GameRegistry.register
        class MyGame(_FakeGame):
            pass

        assert len(GameRegistry.list_games()) == 1
        GameRegistry.clear()
        assert len(GameRegistry.list_games()) == 0

    def test_register_as_decorator_returns_class(self) -> None:
        """O decorador @register retorna a classe original."""

        @GameRegistry.register
        class MyGame(_FakeGame):
            pass

        # Deve ser possível instanciar a classe normalmente
        game = MyGame()
        assert game.name == "TestGame"

    def test_register_multiple_games(self) -> None:
        """Pode registrar múltiplos jogos."""

        @GameRegistry.register
        class G1(_FakeGame):
            pass

        @GameRegistry.register
        class G2(_FakeGame2):
            pass

        assert GameRegistry.get("testgame") is G1
        assert GameRegistry.get("outrojogo") is G2
        assert len(GameRegistry.list_games()) == 2
