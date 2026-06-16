"""SessionManager — gerencia múltiplas sessões de jogo concorrentes."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from py21ssh.application.game_controller import GameController
from py21ssh.domain.rules import BlackjackRules

if TYPE_CHECKING:
    from py21ssh.application.interfaces import ITransportAdapter
    from py21ssh.display.interfaces import IDisplayRenderer

logger = logging.getLogger(__name__)

_active_sessions: dict[str, GameController] = {}


async def run_session(
    transport: ITransportAdapter,
    renderer: IDisplayRenderer,
) -> int:
    """Cria e executa uma sessão de jogo completa.

    Args:
        transport: adaptador de transporte conectado ao cliente.
        renderer: renderizador da interface.

    Returns:
        Saldo final do jogador.
    """
    session_id = uuid.uuid4().hex[:8]
    rules = BlackjackRules()
    controller = GameController(transport, rules, renderer)
    _active_sessions[session_id] = controller

    try:
        final_balance = await controller.run()
        logger.info("Sessão %s encerrada. Saldo final: %d", session_id, final_balance)
        return final_balance
    except Exception:
        logger.exception("Sessão %s encerrada com erro", session_id)
        raise
    finally:
        _active_sessions.pop(session_id, None)
        await transport.close()
