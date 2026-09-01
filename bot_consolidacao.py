"""Bot 4: consolida as coletas e aplica somente regras deterministicas."""

from __future__ import annotations

from uuid import uuid4

from botcity.maestro import AutomationTaskFinishStatus, ErrorType

from config import (
    DATAPOOL_LABEL,
    DEAD_LETTER_FILE,
    LOGS_DIR,
    PIPELINE_BOT_CONSOLIDACAO_LABEL,
    PIPELINE_BOT_ML_LABEL,
    PIPELINE_ML_PRIORITY,
    PIPELINE_TEST_MODE,
)
from src.dead_letter import DeadLetterStore
from src.logger import setup_logger
from src.pipeline_runtime import (
    append_chain,
    get_maestro,
    resolve_parameters,
    write_evidence,
)
from src.validacao import (
    COLUNAS_OBRIGATORIAS,
    normalizar_status,
    status_ambiguo,
    valida_status,
)
from wait_for_predecessor import predecessor_task_id_from_parameters, wait_for_predecessor


logger = setup_logger(__name__)


def consolidar_item(
    order: dict,
    *,
    inventory_by_lot: dict,
    desktop_available: bool,
    web_available: bool,
    pipeline_id: str,
) -> dict:
    """Decide o status apenas por regras; ML nao participa desta funcao."""
    lot_id = _clean(order.get("lote_id"))
    violations = []
    warnings = []
    missing = [
        column for column in COLUNAS_OBRIGATORIAS if _is_empty(order.get(column))
    ]
    if missing:
        violations.append(f"RN02: campos vazios: {', '.join(missing)}")

    inventory = inventory_by_lot.get(str(lot_id)) if lot_id is not None else None
    if desktop_available and lot_id is not None and inventory is None:
        violations.append("RN03: lote_id nao existe no estoque de referencia")
    if inventory is not None:
        inventory_product = _clean(inventory.get("produto"))
        order_product = _clean(order.get("produto"))
        if inventory_product and order_product and inventory_product != order_product:
            violations.append("RN08: produto diverge entre estoque e pedido")

    raw_status = order.get("status")
    if not _is_empty(raw_status):
        normalized = normalizar_status(raw_status)
        if str(raw_status).strip().upper() != normalized:
            warnings.append(f"RN05: status normalizado para {normalized}")
        if not valida_status(raw_status):
            violations.append("RN04: status fora do dominio permitido")
        if status_ambiguo(raw_status):
            violations.append("RN06: status ambiguo requer revisao humana")

    normalized_status = normalizar_status(raw_status)
    if normalized_status == "REPROVADO" and _is_empty(order.get("observacao")):
        violations.append("RN07: observacao obrigatoria para lote reprovado")

    if not web_available or not desktop_available:
        decision = "PENDENTE_REVISAO"
    elif violations:
        decision = "DIVERGENCIA"
    else:
        decision = "VALIDO"

    return {
        "pipeline_id": pipeline_id,
        "lote_id": lot_id,
        "produto": _clean(order.get("produto")),
        "status_original": _clean(raw_status),
        "status_normalizado": normalized_status,
        "status_decisao": decision,
        "regras_violadas": violations,
        "avisos": warnings,
        "observacao": _clean(order.get("observacao")),
        "estoque_encontrado": inventory is not None,
        "produto_estoque": inventory.get("produto") if inventory else None,
        "quantidade_estoque": inventory.get("quantidade_estoque") if inventory else None,
        "quantidade_pedido": order.get("quantidade_pedido", 1),
        "desktop_disponivel": desktop_available,
        "web_disponivel": web_available,
        "causa_provavel": "nao_aplicavel",
        "origem_decisao": "nao_aplicavel",
        "confianca_ml": None,
        "motivo_fallback": None,
        "latencia_ml_ms": 0.0,
        "erro_dado": bool(missing),
    }


def executar_bot_consolidacao(
    maestro=None,
    *,
    parameters=None,
    wait_predecessor_fn=wait_for_predecessor,
    dead_letter_store=None,
) -> dict:
    maestro, connected = get_maestro(maestro)
    task_id = getattr(maestro, "task_id", None)
    incoming = resolve_parameters(maestro, connected, parameters)
    pipeline_id = str(incoming.get("pipeline_id") or uuid4())
    predecessor_id = predecessor_task_id_from_parameters(incoming)
    if connected and predecessor_id:
        wait_predecessor_fn(maestro, predecessor_id)

    desktop_collection = dict(incoming.get("desktop_collection") or {})
    web_collection = dict(incoming.get("web_collection") or {})
    desktop_available = desktop_collection.get("status") == "sucesso"
    web_available = web_collection.get("status") == "sucesso"
    inventory_records = list(desktop_collection.get("records") or [])
    inventory_by_lot = {
        str(record.get("lote_id")): record
        for record in inventory_records
        if not _is_empty(record.get("lote_id"))
    }

    item_pairs = _get_orders_and_items(
        maestro,
        connected,
        task_id,
        list(web_collection.get("records") or []),
    )
    dead_letter_store = dead_letter_store or DeadLetterStore(DEAD_LETTER_FILE)
    results = []
    dead_letter_count = 0
    for order, datapool_item in item_pairs:
        result = consolidar_item(
            order,
            inventory_by_lot=inventory_by_lot,
            desktop_available=desktop_available,
            web_available=web_available,
            pipeline_id=pipeline_id,
        )
        results.append(result)
        if result["erro_dado"]:
            dead_letter_count += 1
            dead_letter_store.register(
                pipeline_id=pipeline_id,
                item=order,
                reason="; ".join(result["regras_violadas"]),
            )
            if datapool_item is not None and hasattr(datapool_item, "report_error"):
                datapool_item.report_error(
                    error_type=ErrorType.BUSINESS,
                    finish_message="Item enviado para dead letter por erro de dado.",
                )
        elif datapool_item is not None and hasattr(datapool_item, "report_done"):
            datapool_item.report_done(finish_message=result["status_decisao"])

    summary = _summarize(results, dead_letter_count, desktop_available, web_available)
    evidence_path = write_evidence(
        LOGS_DIR,
        pipeline_id,
        "consolidacao",
        {"pipeline_id": pipeline_id, "summary": summary, "results": results},
    )
    next_parameters = append_chain(
        incoming,
        activity_label=PIPELINE_BOT_CONSOLIDACAO_LABEL,
        task_id=task_id,
        result="CONSOLIDACAO_CONCLUIDA",
    )
    next_parameters.update(
        {
            "pipeline_id": pipeline_id,
            "consolidation_results": results,
            "consolidation_summary": summary,
            "consolidation_evidence_path": str(evidence_path),
            "predecessor_task_id": str(task_id) if task_id else None,
            "predecessor_activity_label": PIPELINE_BOT_CONSOLIDACAO_LABEL,
            "predecessor_result": "CONSOLIDACAO_CONCLUIDA",
        }
    )

    next_task = None
    if connected:
        next_task = maestro.create_task(
            activity_label=PIPELINE_BOT_ML_LABEL,
            parameters=next_parameters,
            test=PIPELINE_TEST_MODE,
            priority=PIPELINE_ML_PRIORITY,
        )
        if task_id:
            maestro.post_artifact(
                task_id=task_id,
                artifact_name=evidence_path.name,
                filepath=str(evidence_path),
            )
            degraded = not desktop_available or not web_available
            maestro.finish_task(
                task_id=task_id,
                status=(
                    AutomationTaskFinishStatus.PARTIALLY_COMPLETED
                    if degraded or dead_letter_count
                    else AutomationTaskFinishStatus.SUCCESS
                ),
                message=(
                    f"Consolidacao concluiu {len(results)} itens; "
                    f"dead_letter={dead_letter_count}."
                ),
                total_items=len(results),
                processed_items=len(results) - dead_letter_count,
                failed_items=dead_letter_count,
            )

    return {
        "pipeline_id": pipeline_id,
        "results": results,
        "summary": summary,
        "evidence_path": str(evidence_path),
        "next_task_id": getattr(next_task, "id", None),
        "next_task_parameters": next_parameters,
    }


def _get_orders_and_items(maestro, connected, task_id, fallback_orders):
    if connected and hasattr(maestro, "get_datapool"):
        datapool = maestro.get_datapool(DATAPOOL_LABEL)
        pairs = []
        while datapool.has_next():
            item = datapool.next(task_id=task_id)
            if item is None:
                break
            pairs.append((_item_to_dict(item), item))
        if pairs:
            return pairs
    return [(dict(order), None) for order in fallback_orders]


def _item_to_dict(item):
    values = getattr(item, "values", None)
    if isinstance(values, dict):
        return dict(values)
    keys = (*COLUNAS_OBRIGATORIAS, "observacao", "quantidade_pedido")
    return {key: item.get_value(key) for key in keys}


def _summarize(results, dead_letter_count, desktop_available, web_available):
    return {
        "total": len(results),
        "validos": sum(r["status_decisao"] == "VALIDO" for r in results),
        "divergencias": sum(r["status_decisao"] == "DIVERGENCIA" for r in results),
        "pendentes_revisao": sum(
            r["status_decisao"] == "PENDENTE_REVISAO" for r in results
        ),
        "dead_letter": dead_letter_count,
        "desktop_disponivel": desktop_available,
        "web_disponivel": web_available,
        "pipeline_degradado": not desktop_available or not web_available,
    }


def _clean(value):
    return None if _is_empty(value) else str(value).strip()


def _is_empty(value):
    if value is None:
        return True
    try:
        if value != value:
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def main():
    result = executar_bot_consolidacao()
    print(
        f"Consolidacao: pipeline_id={result['pipeline_id']} "
        f"total={result['summary']['total']} "
        f"divergencias={result['summary']['divergencias']}"
    )


if __name__ == "__main__":
    main()
