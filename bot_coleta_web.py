"""Bot 3: coleta pedidos/lotes no portal web simulado."""

from __future__ import annotations

from uuid import uuid4

from botcity.maestro import AutomationTaskFinishStatus

from config import (
    CAPSTONE_RETRY_DELAY_SECONDS,
    CAPSTONE_WEB_RETRY_ATTEMPTS,
    LOGS_DIR,
    PIPELINE_BOT_CONSOLIDACAO_LABEL,
    PIPELINE_BOT_WEB_LABEL,
    PIPELINE_CONSOLIDACAO_PRIORITY,
    PIPELINE_TEST_MODE,
)
from src.capstone_collectors import WebOrderCollector
from src.capstone_errors import InfrastructureError
from src.logger import setup_logger
from src.pipeline_runtime import (
    append_chain,
    get_maestro,
    resolve_parameters,
    write_evidence,
)
from src.resilience import RetryExhaustedError, executar_com_retry_linear
from wait_for_predecessor import predecessor_task_id_from_parameters, wait_for_predecessor


logger = setup_logger(__name__)


def executar_bot_coleta_web(
    maestro=None,
    *,
    parameters=None,
    collector=None,
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

    collector = collector or WebOrderCollector()
    retry_kwargs = {
        "operation_name": "coleta_web",
        "max_attempts": CAPSTONE_WEB_RETRY_ATTEMPTS,
        "initial_delay_seconds": CAPSTONE_RETRY_DELAY_SECONDS,
        "retryable_exceptions": (OSError, InfrastructureError),
        "logger": logger,
    }
    if sleep_fn is not None:
        retry_kwargs["sleep_fn"] = sleep_fn
    try:
        collection = executar_com_retry_linear(
            lambda: collector.collect(pipeline_id),
            **retry_kwargs,
        )
    except RetryExhaustedError as error:
        collection = {
            "status": "indisponivel",
            "mode": getattr(collector, "mode", "desconhecido"),
            "records": [],
            "evidences": [],
            "error": str(error.last_error),
        }

    evidence_path = write_evidence(
        LOGS_DIR,
        pipeline_id,
        "web",
        {"pipeline_id": pipeline_id, "collection": collection},
    )
    next_parameters = append_chain(
        incoming,
        activity_label=PIPELINE_BOT_WEB_LABEL,
        task_id=task_id,
        result=(
            "COLETA_WEB_OK"
            if collection["status"] == "sucesso"
            else "COLETA_WEB_INDISPONIVEL"
        ),
    )
    next_parameters.update(
        {
            "pipeline_id": pipeline_id,
            "web_collection": collection,
            "web_evidence_path": str(evidence_path),
            "predecessor_task_id": str(task_id) if task_id else None,
            "predecessor_activity_label": PIPELINE_BOT_WEB_LABEL,
            "predecessor_result": (
                "COLETA_WEB_OK"
                if collection["status"] == "sucesso"
                else "COLETA_WEB_INDISPONIVEL"
            ),
        }
    )

    next_task = None
    if connected:
        next_task = maestro.create_task(
            activity_label=PIPELINE_BOT_CONSOLIDACAO_LABEL,
            parameters=next_parameters,
            test=PIPELINE_TEST_MODE,
            priority=PIPELINE_CONSOLIDACAO_PRIORITY,
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
                    f"Coleta web concluida com {total} registro(s)."
                    if not degraded
                    else "Portal web indisponivel; pipeline segue degradado."
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
    result = executar_bot_coleta_web()
    print(
        f"Coleta web: pipeline_id={result['pipeline_id']} "
        f"status={result['collection']['status']} "
        f"registros={len(result['collection'].get('records') or [])}"
    )


if __name__ == "__main__":
    main()
