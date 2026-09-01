"""Bot 1: inicia o pipeline Capstone no Maestro ou em modo local."""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from uuid import uuid4

from botcity.maestro import AutomationTaskFinishStatus

from config import (
    CAPSTONE_BUSINESS_KEY,
    CAPSTONE_STATE_DIR,
    ORCHESTRATOR_MODE,
    PIPELINE_BOT_CAPSTONE_LABEL,
    PIPELINE_BOT_DESKTOP_LABEL,
    PIPELINE_DESKTOP_PRIORITY,
    PIPELINE_TEST_MODE,
)
from dispatcher import popular_fila
from src.logger import setup_logger
from src.migration_control import MigrationController
from src.pipeline_runtime import append_chain, get_maestro, resolve_parameters


logger = setup_logger(__name__)


def executar_capstone_orchestrador(
    maestro=None,
    *,
    parameters=None,
    migration_controller=None,
    populate_queue=popular_fila,
    business_key: str | None = None,
) -> dict:
    maestro, connected = get_maestro(maestro)
    task_id = getattr(maestro, "task_id", None)
    incoming = resolve_parameters(maestro, connected, parameters)
    pipeline_id = str(incoming.get("pipeline_id") or uuid4())
    correlation_id = str(incoming.get("correlation_id") or pipeline_id)
    selected_business_key = str(
        business_key
        or incoming.get("business_key")
        or CAPSTONE_BUSINESS_KEY
        or f"conferencia-lotes:{date.today().isoformat()}"
    )

    controller = migration_controller or MigrationController(
        CAPSTONE_STATE_DIR,
        incoming.get("orchestrator_mode") or ORCHESTRATOR_MODE,
    )
    claim = controller.claim_execution(selected_business_key, pipeline_id)

    dispatch_summary = {
        "enviados": 0,
        "ignorados": 0,
        "fila_ja_populada": False,
        "modo": "simulacao_local",
    }
    if claim.allowed and connected:
        dispatch_summary = populate_queue(maestro)

    next_parameters = append_chain(
        incoming,
        activity_label=PIPELINE_BOT_CAPSTONE_LABEL,
        task_id=task_id,
        result="PIPELINE_INICIADO" if claim.allowed else "PIPELINE_IGNORADO",
    )
    next_parameters.update(
        {
            "pipeline_id": pipeline_id,
            "correlation_id": correlation_id,
            "business_key": selected_business_key,
            "orchestrator_mode": controller.mode,
            "official_output": claim.official,
            "migration_claim": claim.to_dict(),
            "dispatcher_result": dispatch_summary,
            "predecessor_task_id": str(task_id) if task_id else None,
            "predecessor_activity_label": PIPELINE_BOT_CAPSTONE_LABEL,
            "predecessor_result": (
                "PIPELINE_INICIADO" if claim.allowed else "PIPELINE_IGNORADO"
            ),
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    next_task = None
    if connected and claim.allowed:
        next_task = maestro.create_task(
            activity_label=PIPELINE_BOT_DESKTOP_LABEL,
            parameters=next_parameters,
            test=PIPELINE_TEST_MODE,
            priority=PIPELINE_DESKTOP_PRIORITY,
        )

    if connected and task_id:
        sent = int(dispatch_summary.get("enviados", 0) or 0)
        ignored = int(dispatch_summary.get("ignorados", 0) or 0)
        maestro.finish_task(
            task_id=task_id,
            status=AutomationTaskFinishStatus.SUCCESS,
            message=(
                f"Pipeline {pipeline_id} iniciado no modo {controller.mode}."
                if claim.allowed
                else f"Pipeline ignorado: {claim.reason}."
            ),
            total_items=sent + ignored,
            processed_items=sent,
            failed_items=ignored,
        )

    return {
        "pipeline_id": pipeline_id,
        "correlation_id": correlation_id,
        "connected_maestro": connected,
        "claim": claim.to_dict(),
        "dispatch_summary": dispatch_summary,
        "next_task_id": getattr(next_task, "id", None),
        "next_task_parameters": next_parameters,
    }


def main():
    try:
        result = executar_capstone_orchestrador()
        print(
            f"Capstone iniciado: pipeline_id={result['pipeline_id']} "
            f"allowed={result['claim']['allowed']} "
            f"next_task_id={result['next_task_id'] or 'local'}"
        )
    except Exception as error:
        logger.exception("Falha no orquestrador Capstone: %s", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
