"""Espera controlada por uma tarefa predecessora no BotCity Maestro."""

from __future__ import annotations

import time
from dataclasses import dataclass

from botcity.maestro import AutomationTaskFinishStatus

from config import PIPELINE_POLL_INTERVAL_SECONDS, PIPELINE_WAIT_TIMEOUT_SECONDS
from src.logger import setup_logger


logger = setup_logger(__name__)


class PredecessorTimeoutError(TimeoutError):
    """A tarefa predecessora nao terminou dentro do limite configurado."""


class PredecessorFailedError(RuntimeError):
    """A tarefa predecessora terminou com falha ou foi cancelada."""


@dataclass(frozen=True)
class PredecessorResult:
    task_id: str
    finish_status: str
    finish_message: str


def wait_for_predecessor(
    maestro,
    predecessor_task_id,
    *,
    timeout_seconds: float = PIPELINE_WAIT_TIMEOUT_SECONDS,
    poll_interval_seconds: float = PIPELINE_POLL_INTERVAL_SECONDS,
    sleep_fn=time.sleep,
    monotonic_fn=time.monotonic,
) -> PredecessorResult:
    """Aguarda uma tarefa e aceita SUCCESS ou PARTIALLY_COMPLETED.

    A espera possui timeout explicito para impedir que um bot permaneça
    bloqueado indefinidamente caso a tarefa anterior nao seja finalizada.
    """
    if not predecessor_task_id:
        raise ValueError("predecessor_task_id e obrigatorio")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds deve ser maior que zero")
    if poll_interval_seconds <= 0:
        raise ValueError("poll_interval_seconds deve ser maior que zero")

    task_id = str(predecessor_task_id)
    started_at = monotonic_fn()
    accepted_statuses = {
        AutomationTaskFinishStatus.SUCCESS.value,
        AutomationTaskFinishStatus.PARTIALLY_COMPLETED.value,
    }

    while True:
        task = maestro.get_task(task_id)
        state = _enum_value(getattr(task, "state", ""))
        finish_status = _enum_value(getattr(task, "finish_status", ""))
        finish_message = str(getattr(task, "finish_message", "") or "")

        if state == "FINISHED":
            if finish_status not in accepted_statuses:
                raise PredecessorFailedError(
                    f"Tarefa predecessora {task_id} terminou com "
                    f"{finish_status or 'status desconhecido'}: {finish_message}"
                )
            logger.info(
                "Tarefa predecessora %s concluida com %s.",
                task_id,
                finish_status,
            )
            return PredecessorResult(task_id, finish_status, finish_message)

        if state == "CANCELED":
            raise PredecessorFailedError(
                f"Tarefa predecessora {task_id} foi cancelada."
            )

        elapsed = monotonic_fn() - started_at
        if elapsed >= timeout_seconds:
            raise PredecessorTimeoutError(
                f"Timeout de {timeout_seconds:.0f}s aguardando a tarefa "
                f"predecessora {task_id}."
            )

        sleep_fn(min(poll_interval_seconds, timeout_seconds - elapsed))


def predecessor_task_id_from_parameters(parameters: dict | None) -> str | None:
    """Extrai o id da tarefa anterior dos parametros recebidos pelo bot."""
    if not parameters:
        return None
    value = parameters.get("predecessor_task_id")
    return str(value) if value not in (None, "") else None


def _enum_value(value) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").upper()
