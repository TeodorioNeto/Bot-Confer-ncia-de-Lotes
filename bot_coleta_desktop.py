"""Bot 2: coleta o estoque no sistema desktop legado simulado."""

from __future__ import annotations

from uuid import uuid4

from botcity.maestro import AutomationTaskFinishStatus

from config import (
    CAPSTONE_DESKTOP_RETRY_ATTEMPTS,
    CAPSTONE_RETRY_DELAY_SECONDS,
    CAPSTONE_STATE_DIR,
    LOGS_DIR,
    ORCHESTRATOR_MODE,
    PIPELINE_BOT_DESKTOP_LABEL,
    PIPELINE_BOT_WEB_LABEL,
    PIPELINE_TEST_MODE,
    PIPELINE_WEB_PRIORITY,
)
from src.capstone_collectors import DesktopInventoryCollector
from src.capstone_errors import InfrastructureError
from src.logger import setup_logger
from src.migration_control import DesktopSessionBusyError, MigrationController
from src.pipeline_runtime import (
    append_chain,
    get_maestro,
    resolve_parameters,
    write_evidence,
)
from src.resilience import RetryExhaustedError, executar_com_retry_linear
from wait_for_predecessor import predecessor_task_id_from_parameters, wait_for_predecessor


logger = setup_logger(__name__)


def executar_bot_coleta_desktop(
    maestro=None,
    *,
    parameters=None,
    collector=None,
    migration_controller=None,
    wait_predecessor_fn=wait_for_predecessor,
    sleep_fn=None,
) -> dict:
    maestro, connected = get_maestro(maestro)
    task_id = getattr(maestro, "task_id", None)
    incoming = resolve_parameters(maestro, connected, parameters)
    pipeline_id = str(incoming.get("pipeline_id") or uuid4())
    predecessor_id = predecessor_task_id_from_parameters(incoming)
    if connected and predecessor_id:
        wait_predecessor_fn(maestro, predecessor_id)

    collector = collector or DesktopInventoryCollector()
    controller = migration_controller or MigrationController(
        CAPSTONE_STATE_DIR,
        incoming.get("orchestrator_mode") or ORCHESTRATOR_MODE,
    )

    retry_kwargs = {
        "operation_name": "coleta_desktop",
        "max_attempts": CAPSTONE_DESKTOP_RETRY_ATTEMPTS,
        "initial_delay_seconds": CAPSTONE_RETRY_DELAY_SECONDS,
        "retryable_exceptions": (
            OSError,
            InfrastructureError,
            DesktopSessionBusyError,
        ),
        "logger": logger,
    }
    if sleep_fn is not None:
        retry_kwargs["sleep_fn"] = sleep_fn

    def collect_with_lock():
        with controller.desktop_session(pipeline_id):
            return collector.collect(pipeline_id)

    try:
        collection = executar_com_retry_linear(
            collect_with_lock,
            **retry_kwargs,
        )
    except RetryExhaustedError as error:
        collection = {
            "status": "indisponivel",
            "mode": getattr(collector, "mode", "desconhecido"),
            "records": [],
            "screenshot": None,
            "error": str(error.last_error),
        }

    evidence_path = write_evidence(
        LOGS_DIR,
        pipeline_id,
        "desktop",
        {"pipeline_id": pipeline_id, "collection": collection},
    )
    next_parameters = append_chain(
        incoming,
        activity_label=PIPELINE_BOT_DESKTOP_LABEL,
        task_id=task_id,
        result=(
            "COLETA_DESKTOP_OK"
            if collection["status"] == "sucesso"
            else "COLETA_DESKTOP_INDISPONIVEL"
        ),
    )
    next_parameters.update(
        {
            "pipeline_id": pipeline_id,
            "desktop_collection": collection,
            "desktop_evidence_path": str(evidence_path),
            "predecessor_task_id": str(task_id) if task_id else None,
            "predecessor_activity_label": PIPELINE_BOT_DESKTOP_LABEL,
            "predecessor_result": (
                "COLETA_DESKTOP_OK"
                if collection["status"] == "sucesso"
                else "COLETA_DESKTOP_INDISPONIVEL"
            ),
        }
    )

    next_task = None
    if connected:
        next_task = maestro.create_task(
            activity_label=PIPELINE_BOT_WEB_LABEL,
            parameters=next_parameters,
            test=PIPELINE_TEST_MODE,
            priority=PIPELINE_WEB_PRIORITY,
        )
        if task_id:
            total = len(collection.get("records") or [])
            degraded = collection["status"] != "sucesso"
            maestro.post_artifact(
                task_id=task_id,
                artifact_name=evidence_path.name,
                filepath=str(evidence_path),
            )
            maestro.finish_task(
                task_id=task_id,
                status=(
                    AutomationTaskFinishStatus.PARTIALLY_COMPLETED
                    if degraded
                    else AutomationTaskFinishStatus.SUCCESS
                ),
                message=(
                    f"Coleta desktop concluida com {total} registro(s)."
                    if not degraded
                    else "Sistema desktop indisponivel; pipeline segue degradado."
                ),
                total_items=total,
                processed_items=total,
                failed_items=1 if degraded else 0,
            )

    return {
        "pipeline_id": pipeline_id,
        "collection": collection,
        "evidence_path": str(evidence_path),
        "next_task_id": getattr(next_task, "id", None),
        "next_task_parameters": next_parameters,
    }


def main():
    result = executar_bot_coleta_desktop()
    print(
        f"Coleta desktop: pipeline_id={result['pipeline_id']} "
        f"status={result['collection']['status']} "
        f"registros={len(result['collection'].get('records') or [])}"
    )


if __name__ == "__main__":
    main()
