"""Bot 5: enriquece divergencias sem decidir o status de negocio."""

from __future__ import annotations

from uuid import uuid4

from botcity.maestro import AutomationTaskFinishStatus

from config import (
    LOGS_DIR,
    ML_CONFIANCA_MINIMA,
    ML_DIVERGENCIA_FORCE_CONFIDENCE,
    ML_DIVERGENCIA_FORCE_ERROR,
    ML_DIVERGENCIA_MOCK_DELAY_SECONDS,
    ML_DIVERGENCIA_TIMEOUT_SECONDS,
    ML_DIVERGENCIA_URL,
    ML_ENABLED,
    PIPELINE_BOT_ML_LABEL,
    PIPELINE_BOT_RELATORIO_LABEL,
    PIPELINE_RELATORIO_PRIORITY,
    PIPELINE_TEST_MODE,
)
from src.classificador_divergencia import ClassificadorDivergencia
from src.logger import setup_logger
from src.pipeline_runtime import (
    append_chain,
    get_maestro,
    resolve_parameters,
    write_evidence,
)
from wait_for_predecessor import predecessor_task_id_from_parameters, wait_for_predecessor


logger = setup_logger(__name__)


def enriquecer_resultados(results: list[dict], classifier) -> list[dict]:
    enriched = []
    for original in results:
        result = dict(original)
        if result.get("status_decisao") == "DIVERGENCIA":
            classification = classifier.classificar(result.get("observacao"))
            result.update(classification.to_dict())
        enriched.append(result)
    return enriched


def executar_bot_classificador_ml(
    maestro=None,
    *,
    parameters=None,
    classifier=None,
    wait_predecessor_fn=wait_for_predecessor,
) -> dict:
    maestro, connected = get_maestro(maestro)
    task_id = getattr(maestro, "task_id", None)
    incoming = resolve_parameters(maestro, connected, parameters)
    pipeline_id = str(incoming.get("pipeline_id") or uuid4())
    predecessor_id = predecessor_task_id_from_parameters(incoming)
    if connected and predecessor_id:
        wait_predecessor_fn(maestro, predecessor_id)

    classifier = classifier or _build_classifier()
    original_results = list(incoming.get("consolidation_results") or [])
    results = enriquecer_resultados(original_results, classifier)
    consolidation_summary = dict(incoming.get("consolidation_summary") or {})
    summary = _summarize(results, consolidation_summary)
    evidence_path = write_evidence(
        LOGS_DIR,
        pipeline_id,
        "ml",
        {"pipeline_id": pipeline_id, "summary": summary, "results": results},
    )

    next_parameters = append_chain(
        incoming,
        activity_label=PIPELINE_BOT_ML_LABEL,
        task_id=task_id,
        result="CLASSIFICACAO_ML_CONCLUIDA",
    )
    next_parameters.update(
        {
            "pipeline_id": pipeline_id,
            "pipeline_results": results,
            "bot_b_summary": summary,
            "capstone_summary": summary,
            "ml_evidence_path": str(evidence_path),
            "predecessor_task_id": str(task_id) if task_id else None,
            "predecessor_activity_label": PIPELINE_BOT_ML_LABEL,
            "predecessor_result": "CLASSIFICACAO_ML_CONCLUIDA",
        }
    )

    next_task = None
    if connected:
        next_task = maestro.create_task(
            activity_label=PIPELINE_BOT_RELATORIO_LABEL,
            parameters=next_parameters,
            test=PIPELINE_TEST_MODE,
            priority=PIPELINE_RELATORIO_PRIORITY,
        )
        if task_id:
            maestro.post_artifact(
                task_id=task_id,
                artifact_name=evidence_path.name,
                filepath=str(evidence_path),
            )
            maestro.finish_task(
                task_id=task_id,
                status=AutomationTaskFinishStatus.SUCCESS,
                message=(
                    f"ML processou {summary['divergencias']} divergencia(s); "
                    f"fallback={summary['fallback_ml']}."
                ),
                total_items=len(results),
                processed_items=len(results),
                failed_items=0,
            )

    return {
        "pipeline_id": pipeline_id,
        "results": results,
        "summary": summary,
        "evidence_path": str(evidence_path),
        "next_task_id": getattr(next_task, "id", None),
        "next_task_parameters": next_parameters,
    }


def _build_classifier():
    forced_confidence = (
        float(ML_DIVERGENCIA_FORCE_CONFIDENCE)
        if ML_DIVERGENCIA_FORCE_CONFIDENCE
        else None
    )
    return ClassificadorDivergencia(
        enabled=ML_ENABLED,
        confidence_min=ML_CONFIANCA_MINIMA,
        timeout_seconds=ML_DIVERGENCIA_TIMEOUT_SECONDS,
        endpoint_url=ML_DIVERGENCIA_URL,
        mock_delay_seconds=ML_DIVERGENCIA_MOCK_DELAY_SECONDS,
        force_confidence=forced_confidence,
        force_error=ML_DIVERGENCIA_FORCE_ERROR,
        logger=logger,
    )


def _summarize(results, consolidation_summary):
    divergences = [r for r in results if r.get("status_decisao") == "DIVERGENCIA"]
    fallbacks = [r for r in divergences if r.get("origem_decisao") == "fallback"]
    summary = dict(consolidation_summary)
    summary.update(
        {
            "total": len(results),
            "validos": sum(r.get("status_decisao") == "VALIDO" for r in results),
            "divergencias": len(divergences),
            "pendentes_revisao": sum(
                r.get("status_decisao") == "PENDENTE_REVISAO" for r in results
            ),
            "fallback_ml": len(fallbacks),
            "pipeline_sem_ml": bool(
                divergences and len(fallbacks) == len(divergences)
            ),
        }
    )
    return summary


def main():
    result = executar_bot_classificador_ml()
    print(
        f"ML: pipeline_id={result['pipeline_id']} "
        f"divergencias={result['summary']['divergencias']} "
        f"fallback={result['summary']['fallback_ml']}"
    )


if __name__ == "__main__":
    main()
