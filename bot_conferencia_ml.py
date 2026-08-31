"""Bot B do S10-B: regras RN01-RN03 e enriquecimento opcional por ML."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from botcity.maestro import AutomationTaskFinishStatus, BotMaestroSDK, ErrorType

from config import (
    ARQUIVO_BASE_REFERENCIA,
    ARQUIVO_INSPECAO,
    BASE_RETRY_DELAY_SECONDS,
    BASE_RETRY_MAX_ATTEMPTS,
    DATAPOOL_LABEL,
    DEAD_LETTER_FILE,
    LOGS_DIR,
    MAESTRO_ENABLED,
    MAESTRO_KEY,
    MAESTRO_LOGIN,
    MAESTRO_SERVER,
    ML_CONFIANCA_MINIMA,
    ML_DIVERGENCIA_FORCE_CONFIDENCE,
    ML_DIVERGENCIA_FORCE_ERROR,
    ML_DIVERGENCIA_MOCK_DELAY_SECONDS,
    ML_DIVERGENCIA_TIMEOUT_SECONDS,
    ML_DIVERGENCIA_URL,
    ML_ENABLED,
    PIPELINE_BOT_B_LABEL,
    PIPELINE_BOT_C_LABEL,
    PIPELINE_PRIORITY,
    PIPELINE_TEST_MODE,
)
from src.base_referencia import carregar_base_referencia, verificar_lote_na_base
from src.classificador_divergencia import ClassificadorDivergencia
from src.dead_letter import DeadLetterStore
from src.logger import setup_logger
from src.resilience import RetryExhaustedError, executar_com_retry_linear
from src.validacao import COLUNAS_OBRIGATORIAS, carregar_planilha, valida_estrutura
from wait_for_predecessor import (
    predecessor_task_id_from_parameters,
    wait_for_predecessor,
)


logger = setup_logger(__name__)


def processar_item_hibrido(
    item,
    *,
    base_reference: set,
    base_available: bool,
    classifier: ClassificadorDivergencia,
    pipeline_id: str,
) -> dict:
    values = {column: _value(item, column) for column in COLUNAS_OBRIGATORIAS}
    values["observacao"] = _value(item, "observacao")
    lot_id = values.get("lote_id")
    violated_rules = []
    empty_fields = [
        column for column in COLUNAS_OBRIGATORIAS if _is_empty(values.get(column))
    ]
    if empty_fields:
        violated_rules.append(f"RN02: campos vazios: {', '.join(empty_fields)}")

    if base_available and not _is_empty(lot_id):
        if not verificar_lote_na_base(str(lot_id), base_reference):
            violated_rules.append("RN03: lote_id nao existe na base de referencia")

    if not base_available:
        business_status = "PENDENTE_REVISAO"
    elif violated_rules:
        business_status = "DIVERGENCIA"
    else:
        business_status = "VALIDO"

    result = {
        "pipeline_id": pipeline_id,
        "lote_id": lot_id,
        "status_decisao": business_status,
        "regras_violadas": violated_rules,
        "observacao": values.get("observacao"),
        "causa_provavel": "nao_aplicavel",
        "origem_decisao": "nao_aplicavel",
        "confianca_ml": None,
        "motivo_fallback": None,
        "latencia_ml_ms": 0.0,
        "erro_dado": bool(empty_fields),
    }

    if business_status == "DIVERGENCIA":
        classification = classifier.classificar(values.get("observacao"))
        result.update(classification.to_dict())

    logger.info(
        "pipeline_decision=%s",
        json.dumps(result, ensure_ascii=False, default=str, sort_keys=True),
    )
    return result


def executar_bot_b(
    maestro=None,
    *,
    classifier=None,
    load_base=carregar_base_referencia,
    wait_predecessor=wait_for_predecessor,
    dead_letter_store=None,
    sleep_fn=None,
) -> dict:
    maestro, connected = _get_maestro(maestro)
    task_id = getattr(maestro, "task_id", None)
    current_task = maestro.get_task(task_id) if connected and task_id else None
    parameters = dict(getattr(current_task, "parameters", None) or {})
    pipeline_id = str(parameters.get("pipeline_id") or uuid4())

    predecessor_id = predecessor_task_id_from_parameters(parameters)
    if connected and predecessor_id:
        wait_predecessor(maestro, predecessor_id)

    classifier = classifier or _build_classifier()
    dead_letter_store = dead_letter_store or DeadLetterStore(DEAD_LETTER_FILE)

    base_available = parameters.get("base_reference_status") != "indisponivel"
    base_reference = set()
    if base_available:
        retry_kwargs = {
            "operation_name": "carregar_base_referencia_bot_b",
            "max_attempts": BASE_RETRY_MAX_ATTEMPTS,
            "initial_delay_seconds": BASE_RETRY_DELAY_SECONDS,
            "logger": logger,
        }
        if sleep_fn is not None:
            retry_kwargs["sleep_fn"] = sleep_fn
        try:
            base_reference = executar_com_retry_linear(
                lambda: load_base(ARQUIVO_BASE_REFERENCIA),
                **retry_kwargs,
            )
        except RetryExhaustedError:
            base_available = False

    items = _get_items(maestro, connected, task_id)
    results = []
    dead_letter_count = 0
    for item in items:
        result = processar_item_hibrido(
            item,
            base_reference=base_reference,
            base_available=base_available,
            classifier=classifier,
            pipeline_id=pipeline_id,
        )
        results.append(result)

        if result["erro_dado"]:
            dead_letter_count += 1
            dead_letter_store.register(
                pipeline_id=pipeline_id,
                item=_item_to_dict(item),
                reason="; ".join(result["regras_violadas"]),
            )
            if hasattr(item, "report_error"):
                item.report_error(
                    error_type=ErrorType.BUSINESS,
                    finish_message="Item enviado para dead letter por erro de dado.",
                )
        elif hasattr(item, "report_done"):
            item.report_done(finish_message=result["status_decisao"])

    summary = _summarize(results, dead_letter_count)
    evidence_path = _write_evidence(pipeline_id, results, summary)
    next_parameters = _build_next_parameters(
        parameters,
        pipeline_id,
        task_id,
        results,
        summary,
        evidence_path,
    )

    next_task = None
    if connected:
        next_task = maestro.create_task(
            activity_label=PIPELINE_BOT_C_LABEL,
            parameters=next_parameters,
            test=PIPELINE_TEST_MODE,
            priority=PIPELINE_PRIORITY,
        )
        if task_id:
            status = (
                AutomationTaskFinishStatus.PARTIALLY_COMPLETED
                if dead_letter_count or not base_available
                else AutomationTaskFinishStatus.SUCCESS
            )
            maestro.finish_task(
                task_id=task_id,
                status=status,
                message=(
                    f"Bot B concluiu {len(results)} itens; "
                    f"dead_letter={dead_letter_count}; Bot C criado."
                ),
                total_items=len(results),
                processed_items=len(results) - dead_letter_count,
                failed_items=dead_letter_count,
            )

    return {
        "pipeline_id": pipeline_id,
        "connected_maestro": connected,
        "results": results,
        "summary": summary,
        "evidence_path": str(evidence_path),
        "next_task_id": getattr(next_task, "id", None),
        "next_task_parameters": next_parameters,
    }


def _build_classifier() -> ClassificadorDivergencia:
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


def _get_items(maestro, connected: bool, task_id):
    if connected:
        datapool = maestro.get_datapool(DATAPOOL_LABEL)
        items = []
        while datapool.has_next():
            item = datapool.next(task_id=task_id)
            if item is None:
                break
            items.append(item)
        return items

    if not valida_estrutura(ARQUIVO_INSPECAO):
        raise ValueError("Estrutura da planilha invalida (RN01)")
    dataframe = carregar_planilha(ARQUIVO_INSPECAO)
    return [dict(row) for row in dataframe.to_dict(orient="records")]


def _build_next_parameters(parameters, pipeline_id, task_id, results, summary, evidence_path):
    now = datetime.now(timezone.utc).isoformat()
    chain = list(parameters.get("execution_chain") or [])
    chain.append(
        {
            "activity_label": PIPELINE_BOT_B_LABEL,
            "task_id": str(task_id or "local"),
            "result": "PROCESSAMENTO_CONCLUIDO",
            "finished_at": now,
        }
    )
    next_parameters = dict(parameters)
    next_parameters.update(
        {
            "pipeline_id": pipeline_id,
            "predecessor_task_id": str(task_id) if task_id else None,
            "predecessor_activity_label": PIPELINE_BOT_B_LABEL,
            "predecessor_result": "PROCESSAMENTO_CONCLUIDO",
            "pipeline_results": results,
            "bot_b_summary": summary,
            "bot_b_evidence_path": str(evidence_path),
            "execution_chain": chain,
            "triggered_at": now,
        }
    )
    return next_parameters


def _summarize(results, dead_letter_count):
    divergences = [r for r in results if r["status_decisao"] == "DIVERGENCIA"]
    fallback_count = sum(r["origem_decisao"] == "fallback" for r in divergences)
    return {
        "total": len(results),
        "validos": sum(r["status_decisao"] == "VALIDO" for r in results),
        "divergencias": len(divergences),
        "pendentes_revisao": sum(
            r["status_decisao"] == "PENDENTE_REVISAO" for r in results
        ),
        "fallback_ml": fallback_count,
        "dead_letter": dead_letter_count,
        "pipeline_sem_ml": bool(divergences and fallback_count == len(divergences)),
    }


def _write_evidence(pipeline_id, results, summary) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(char if char.isalnum() or char in "-_" else "_" for char in pipeline_id)
    path = LOGS_DIR / f"pipeline_{safe_id}_bot_b.json"
    path.write_text(
        json.dumps(
            {"pipeline_id": pipeline_id, "summary": summary, "results": results},
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return path


def _get_maestro(maestro):
    if maestro is not None:
        return maestro, True
    sdk = BotMaestroSDK.from_sys_args()
    if getattr(sdk, "task_id", None):
        return sdk, True
    if MAESTRO_ENABLED:
        sdk.login(server=MAESTRO_SERVER, login=MAESTRO_LOGIN, key=MAESTRO_KEY)
        return sdk, True
    sdk.RAISE_NOT_CONNECTED = False
    return sdk, False


def _item_to_dict(item):
    if isinstance(item, dict):
        return dict(item)
    values = getattr(item, "values", None)
    if isinstance(values, dict):
        return dict(values)
    return {column: _value(item, column) for column in (*COLUNAS_OBRIGATORIAS, "observacao")}


def _value(item, key):
    if hasattr(item, "get_value"):
        value = item.get_value(key)
    elif isinstance(item, dict):
        value = item.get(key)
    else:
        value = getattr(item, key, None)
    return None if _is_empty(value) else value


def _is_empty(value):
    if value is None:
        return True
    try:
        if value != value:  # NaN de pandas/numpy
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def main():
    result = executar_bot_b()
    print(
        f"Bot B concluido: pipeline_id={result['pipeline_id']} "
        f"total={result['summary']['total']} "
        f"divergencias={result['summary']['divergencias']} "
        f"next_task_id={result['next_task_id'] or 'simulacao'}"
    )


if __name__ == "__main__":
    main()
