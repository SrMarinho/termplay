"""RichRenderer — renderização ANSI via Rich para envio sobre TCP."""

from __future__ import annotations

from typing import Final

from rich.panel import Panel
from rich.table import Table

from termplay.engine.interfaces import ITransportAdapter
from termplay.games.blackjack.conf import CONSOLE_WIDTH, MIN_BET
from termplay.games.blackjack.domain.card import Card
from termplay.games.blackjack.domain.hand import Hand
from termplay.games.blackjack.domain.interfaces import RoundResult

_TERMINAL_WIDTH: Final[int] = CONSOLE_WIDTH


def _render_console(*items: object, width: int = _TERMINAL_WIDTH) -> str:
    """Renderiza objetos Rich para string ANSI.

    force_terminal=True garante que ANSI codes sejam emitidos
    mesmo sem um terminal real (envio sobre TCP).
    """
    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    console = Console(file=buf, width=width, force_terminal=True, highlight=False)
    for item in items:
        console.print(item)
    return buf.getvalue()


def _cards_line(cards: list[Card], hide_first: bool = False) -> str:
    """Retorna linha de cartas, opcionalmente ocultando a primeira."""
    parts: list[str] = []
    for i, card in enumerate(cards):
        if i == 0 and hide_first:
            parts.append("[white on black]🂠[/]")
        else:
            parts.append(f"[bold]{card.display}[/]")
    return " ".join(parts)


def _value_display(cards: list[Card], hide_first: bool) -> str:
    """Valor visível da mão."""
    if hide_first and len(cards) > 1:
        # Só mostra valor da segunda carta
        return str(cards[1].value)
    # Calcula o valor real
    total = sum(c.value for c in cards)
    aces = sum(1 for c in cards if c.is_ace)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return str(total)


class RichRenderer:
    """Renderizador que produz ANSI via Rich para envio sobre TCP.

    Implementa IDisplayRenderer. Toda saída é ANSI pura
    (force_terminal=True) para funcionar sobre TCP cru.
    """

    def __init__(self, transport: ITransportAdapter) -> None:
        self._transport = transport
        self._width = transport.width

    # ── implementação IDisplayRenderer ──────────────────

    def welcome(self) -> str:
        return _render_console(
            "",
            Panel(
                "[bold green]🃏  BLACKJACK[/]\n\n"
                "[yellow]Bem-vindo ao Blackjack via TCP![/]\n\n"
                "Comandos:\n"
                "  [cyan]h[/] ou [cyan]1[/] — Hit (comprar carta)\n"
                "  [cyan]s[/] ou [cyan]2[/] — Stand (parar)\n"
                "  [cyan]d[/] ou [cyan]3[/] — Double (dobrar aposta)\n"
                "  [cyan]q[/] — Sair\n\n"
                "[dim]Digite sua aposta para começar...[/]",
                title="🃏 Blackjack",
                border_style="green",
            ),
            "",
        )

    def banner(self) -> str:
        return (
            "\r\n╔══════════════════════════════╗\r\n"
            "║   BLACKJACK MULTIPLAYER 🃏   ║\r\n"
            "╚══════════════════════════════╝\r\n\r\n"
        )

    def farewell(self) -> str:
        return "\r\nFim de jogo! Obrigado por jogar.\r\n"

    def multiplayer_table(
        self,
        my_name: str,
        my_hand: Hand,
        dealer_hand: Hand,
        balance: int,
        bet: int,
        others: list[tuple[str, Hand]],
        active_name: str = "",
        reveal_dealer: bool = False,
    ) -> str:
        tb = Table.grid(padding=(0, 2))
        tb.add_column("", style="bold yellow", width=14)
        tb.add_column("", width=28)
        tb.add_column("", style="bold cyan", width=6)

        dc = _cards_line(dealer_hand.cards, hide_first=not reveal_dealer)
        dv = _value_display(dealer_hand.cards, hide_first=not reveal_dealer)
        tb.add_row("Dealer", dc, dv)
        tb.add_row("", "", "")

        for name, hand in others:
            arrow = "[bold green]▶[/] " if name == active_name else "  "
            tb.add_row(
                f"{arrow}{name}",
                _cards_line(hand.cards),
                _value_display(hand.cards, False),
            )

        my_arrow = "[bold green]▶[/] " if my_name == active_name else "  "
        tb.add_row(
            f"{my_arrow}Você ({my_name})",
            _cards_line(my_hand.cards),
            _value_display(my_hand.cards, False),
        )

        status = f"💰 {balance}"
        if bet:
            status += f"  |  🎲 {bet}"
        if active_name:
            status += f"  |  Vez de {active_name}"
        if my_hand.is_blackjack:
            status += "  |  [bold green]BLACKJACK![/]"

        return _render_console(
            "",
            Panel(
                tb,
                title="[bold green]🃏  BLACKJACK MULTIPLAYER[/]",
                subtitle=f"[dim]{status}[/]",
                border_style="green",
                width=self._width - 2,
            ),
            "",
        )

    def table(
        self,
        player_hand: Hand,
        dealer_hand: Hand,
        balance: int,
        bet: int,
        reveal_dealer: bool = False,
        doubled: bool = False,
    ) -> str:
        tb = Table.grid(padding=(0, 2))
        tb.add_column("", style="bold yellow", width=10)
        tb.add_column("", width=32)
        tb.add_column("", style="bold cyan", width=6)

        dealer_cards_display = _cards_line(
            dealer_hand.cards, hide_first=not reveal_dealer
        )
        dealer_value = _value_display(dealer_hand.cards, hide_first=not reveal_dealer)

        tb.add_row("Dealer", dealer_cards_display, dealer_value)
        tb.add_row("", "", "")
        tb.add_row(
            "Você",
            _cards_line(player_hand.cards),
            _value_display(player_hand.cards, hide_first=False),
        )

        status = f"💰 {balance}"
        if bet:
            label = "x2 " if doubled else ""
            status += f"  |  🎲 {label}{bet}"
        if player_hand.is_blackjack:
            status += "  |  [bold green]BLACKJACK![/]"

        return _render_console(
            "",
            Panel(
                tb,
                title="[bold green]🃏  BLACKJACK[/]",
                subtitle=f"[dim]{status}[/]",
                border_style="green",
                width=self._width - 2,
            ),
            "",
        )

    def bet_prompt(self, balance: int) -> str:
        return _render_console(
            Panel(
                f"[yellow]Quanto você aposta?[/]\n"
                f"[dim]Saldo: {balance}  |  Mínimo: {MIN_BET}[/]\n\n"
                "[cyan]Digite o valor e pressione Enter:[/]",
                title="🎲 Aposta",
                border_style="cyan",
            ),
            "",
        )

    def action_prompt(self, hand: Hand, bet: int) -> str:
        opts = [("[1]", "Hit"), ("[2]", "Stand")]
        if hand.can_double:
            opts.append(("[3]", f"Double (x2 = {bet * 2})"))
        line = "  ".join(f"[bold cyan]{k}[/] [white]{v}[/]" for k, v in opts)
        return _render_console(f"[yellow]▶ Sua vez![/]  {line}")

    def result(self, result: RoundResult, bet: int, balance: int) -> str:
        mapping: dict[RoundResult, tuple[str, str]] = {
            RoundResult.WIN: ("[bold green]🏆 VOCÊ VENCEU![/]", f"+{bet}"),
            RoundResult.LOSE: ("[bold red]💀 DEALER VENCEU![/]", f"-{bet}"),
            RoundResult.PUSH: ("[bold yellow]🤝 EMPATE![/]", "0"),
            RoundResult.BLACKJACK: (
                "[bold green]🌟 BLACKJACK! Pagamento 3:2[/]",
                f"+{int(bet * 1.5)}",
            ),
        }
        title, delta = mapping[result]
        border = (
            "green" if result in (RoundResult.WIN, RoundResult.BLACKJACK) else "red"
        )
        if result is RoundResult.PUSH:
            border = "yellow"
        return _render_console(
            Panel(
                f"{title}\n\n[dim]Aposta: {bet}  |  Resultado:"
                f" {delta}  |  Saldo: {balance}[/]",
                border_style=border,
            ),
            "",
        )

    def bust(self) -> str:
        return _render_console(
            Panel("[bold red]💥 ESTOUROU! Você passou de 21.[/]", border_style="red"),
            "",
        )

    def goodbye(self, balance: int) -> str:
        return _render_console(
            "",
            Panel(
                f"[bold]Obrigado por jogar![/]\n\n"
                f"Saldo final: [cyan]{balance}[/]\n\n"
                "[dim]Conexão encerrada.[/]",
                title="👋 Até mais!",
                border_style="green",
            ),
            "",
        )

    def error(self, message: str) -> str:
        return _render_console(f"\n[bold red]✗[/] {message}")

    def history(self, balance: int) -> str:
        return _render_console(f"\n[dim]━━━━━━━  Saldo: {balance}  ━━━━━━━━━━━━━[/]")

    def prompt(self, message: str) -> str:
        return _render_console(f"\n[bold]{message}[/] ")
