"""Bot A do pipeline S10-B: preflight, DataPool e disparo do Bot B."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from uuid import uuid4

from botcity.maestro import AutomationTaskFinishStatus, BotMaestroSDK

from config import (
    ARQUIVO_BASE_REFERENCIA,
    BASE_RETRY_DELAY_SECONDS,
    BASE_RETRY_MAX_ATTEMPTS,
    MAESTRO_ENABLED,
    MAESTRO_KEY,
    MAESTRO_LOGIN,
    MAESTRO_SERVER,
    PIPELINE_BOT_A_LABEL,
    PIPELINE_BOT_B_LABEL,
    PIPELINE_PRIORITY,
    PIPELINE_TEST_MODE,
)
from dispatcher import popular_fila
from src.base_referencia import carregar_base_referencia
from src.logger import setup_logger
from src.resilience import RetryExhaustedError, executar_com_retry_linear


logger = setup_logger(__name__)


def executar_orquestrador(
    maestro=None,
    *,
    load_base=carregar_base_referencia,
    populate_queue=popular_fila,
    next_bot_label: str = PIPELINE_BOT_B_LABEL,
    priority: int = PIPELINE_PRIORITY,
    test_mode: bool = PIPELINE_TEST_MODE,
    retry_max_attempts: int = BASE_RETRY_MAX_ATTEMPTS,
    retry_delay_seconds: float = BASE_RETRY_DELAY_SECONDS,
    sleep_fn=None,
) -> dict:
    """Executa o Bot A e cria a tarefa sequencial do Bot B.

    Sem conexao com o Maestro, executa apenas o preflight em modo local e
    devolve os parametros que seriam enviados. Isso permite validar a
    configuracao sem criar tarefas externas acidentalmente.
    """
    _validate_priority(priority)
    maestro, connected = _get_maestro(maestro)
    task_id = getattr(maestro, "task_id", None)
    current_task = maestro.get_task(task_id) if connected and task_id else None
    incoming_parameters = dict(getattr(current_task, "parameters", None) or {})
    pipeline_id = str(incoming_parameters.get("pipeline_id") or uuid4())
    correlation_id = str(
        incoming_parameters.get("correlation_id") or pipeline_id
    )

    base_status = "disponivel"
    predecessor_result = "BASE_REFERENCIA_OK"
    base_count = 0

    retry_kwargs = {
        "operation_name": "carregar_base_referencia",
        "max_attempts": retry_max_attempts,
        "initial_delay_seconds": retry_delay_seconds,
        "logger": logger,
    }
    if sleep_fn is not None:
        retry_kwargs["sleep_fn"] = sleep_fn

    try:
        base_reference = executar_com_retry_linear(
            lambda: load_base(ARQUIVO_BASE_REFERENCIA),
            **retry_kwargs,
        )
        base_count = len(base_reference)
        logger.info(
            "Base de referencia disponivel com %d lote(s). pipeline_id=%s",
            base_count,
            pipeline_id,
        )
    except RetryExhaustedError as error:
        base_status = "indisponivel"
        predecessor_result = "PENDENTE_REVISAO"
        logger.error(
            "Base de referencia indisponivel apos retry; pipeline segue "
            "degradado. pipeline_id=%s erro=%s",
            pipeline_id,
            error,
        )

    dispatch_summary = {
        "enviados": 0,
        "ignorados": 0,
        "fila_ja_populada": False,
        "modo": "simulacao_local",
    }
    if connected:
        dispatch_summary = populate_queue(maestro)

    parameters = _build_next_task_parameters(
        incoming_parameters=incoming_parameters,
        pipeline_id=pipeline_id,
        correlation_id=correlation_id,
        predecessor_task_id=task_id,
        predecessor_result=predecessor_result,
        base_status=base_status,
        base_count=base_count,
        dispatch_summary=dispatch_summary,
    )

    next_task = None
    if connected:
        next_task = maestro.create_task(
            activity_label=next_bot_label,
            parameters=parameters,
            test=test_mode,
            priority=priority,
        )
        logger.info(
            "Bot B criado. pipeline_id=%s predecessor_task_id=%s "
            "next_task_id=%s activity_label=%s",
            pipeline_id,
            task_id,
            getattr(next_task, "id", None),
            next_bot_label,
        )

        if task_id:
            finish_status = (
                AutomationTaskFinishStatus.SUCCESS
                if base_status == "disponivel"
                else AutomationTaskFinishStatus.PARTIALLY_COMPLETED
            )
            dispatched_items = int(dispatch_summary.get("enviados", 0) or 0)
            ignored_items = int(dispatch_summary.get("ignorados", 0) or 0)
            maestro.finish_task(
                task_id=task_id,
                status=finish_status,
                message=(
                    f"Bot A concluido; Bot B criado para pipeline {pipeline_id}. "
                    f"Base de referencia: {base_status}."
                ),
                total_items=dispatched_items + ignored_items,
                processed_items=dispatched_items,
                failed_items=ignored_items,
            )
    else:
        logger.info(
            "Simulacao local concluida; nenhuma tarefa foi criada. "
            "pipeline_id=%s next_activity=%s",
            pipeline_id,
            next_bot_label,
        )

    return {
        "pipeline_id": pipeline_id,
        "correlation_id": correlation_id,
        "connected_maestro": connected,
        "base_reference_status": base_status,
        "base_reference_count": base_count,
        "predecessor_result": predecessor_result,
        "dispatch_summary": dispatch_summary,
        "next_activity_label": next_bot_label,
        "next_task_id": getattr(next_task, "id", None),
        "next_task_parameters": parameters,
    }


def _build_next_task_parameters(
    *,
    incoming_parameters: dict,
    pipeline_id: str,
    correlation_id: str,
    predecessor_task_id,
    predecessor_result: str,
    base_status: str,
    base_count: int,
    dispatch_summary: dict,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    chain = list(incoming_parameters.get("execution_chain") or [])
    chain.append(
        {
            "activity_label": PIPELINE_BOT_A_LABEL,
            "task_id": str(predecessor_task_id or "local"),
            "result": predecessor_result,
            "finished_at": now,
        }
    )

    parameters = dict(incoming_parameters)
    parameters.update(
        {
            "pipeline_id": pipeline_id,
            "correlation_id": correlation_id,
            "predecessor_task_id": (
                str(predecessor_task_id) if predecessor_task_id else None
            ),
            "predecessor_activity_label": PIPELINE_BOT_A_LABEL,
            "predecessor_result": predecessor_result,
            "base_reference_status": base_status,
            "base_reference_count": base_count,
            "dispatcher_result": dispatch_summary,
            "execution_chain": chain,
            "triggered_at": now,
        }
    )
    return parameters


def _get_maestro(maestro):
    if maestro is not None:
        return maestro, True

    sdk = BotMaestroSDK.from_sys_args()
    task_id = getattr(sdk, "task_id", None)
    if task_id:
        logger.info("Execucao do Bot A iniciada pelo Runner. task_id=%s", task_id)
        return sdk, True

    if MAESTRO_ENABLED:
        sdk.login(server=MAESTRO_SERVER, login=MAESTRO_LOGIN, key=MAESTRO_KEY)
        logger.info("Execucao local do Bot A conectada ao Maestro.")
        return sdk, True

    sdk.RAISE_NOT_CONNECTED = False
    logger.info("Execucao local do Bot A em modo de simulacao.")
    return sdk, False


def _validate_priority(priority: int) -> None:
    if priority < 0 or priority > 10:
        raise ValueError("PIPELINE_PRIORITY deve estar entre 0 e 10")


def main():
    try:
        result = executar_orquestrador()
        print(
            "Pipeline iniciado: "
            f"pipeline_id={result['pipeline_id']} "
            f"base={result['base_reference_status']} "
            f"next_task_id={result['next_task_id'] or 'simulacao'}"
        )
    except Exception as error:
        logger.exception("Falha no Bot A/orquestrador: %s", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
