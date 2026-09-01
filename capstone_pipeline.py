"""Executa localmente os seis papeis do pipeline Capstone."""

from __future__ import annotations

import json

from bot_classificador_ml import executar_bot_classificador_ml
from bot_coleta_desktop import executar_bot_coleta_desktop
from bot_coleta_web import executar_bot_coleta_web
from bot_consolidacao import executar_bot_consolidacao
from bot_relatorio_alertas import executar_bot_c
from capstone_orchestrator import executar_capstone_orchestrador
from config import CAPSTONE_STATE_DIR, ORCHESTRATOR_MODE
from src.migration_control import MigrationController
from src.pipeline_runtime import LOCAL_EXECUTION


def executar_pipeline_local(*, business_key=None, migration_controller=None) -> dict:
    controller = migration_controller or MigrationController(
        CAPSTONE_STATE_DIR,
        ORCHESTRATOR_MODE,
    )
    stage_a = executar_capstone_orchestrador(
        LOCAL_EXECUTION,
        parameters={},
        migration_controller=controller,
        business_key=business_key,
    )
    if not stage_a["claim"]["allowed"]:
        return {"status": "ignorado", "orchestrator": stage_a}

    stage_desktop = executar_bot_coleta_desktop(
        LOCAL_EXECUTION,
        parameters=stage_a["next_task_parameters"],
        migration_controller=controller,
    )
    stage_web = executar_bot_coleta_web(
        LOCAL_EXECUTION,
        parameters=stage_desktop["next_task_parameters"],
    )
    stage_consolidation = executar_bot_consolidacao(
        LOCAL_EXECUTION,
        parameters=stage_web["next_task_parameters"],
    )
    stage_ml = executar_bot_classificador_ml(
        LOCAL_EXECUTION,
        parameters=stage_consolidation["next_task_parameters"],
    )
    stage_report = executar_bot_c(
        LOCAL_EXECUTION,
        parameters=stage_ml["next_task_parameters"],
    )
    return {
        "status": "concluido",
        "pipeline_id": stage_a["pipeline_id"],
        "orchestrator": stage_a,
        "desktop": stage_desktop,
        "web": stage_web,
        "consolidation": stage_consolidation,
        "ml": stage_ml,
        "report": stage_report,
    }


def main():
    result = executar_pipeline_local()
    printable = {
        "status": result["status"],
        "pipeline_id": result.get("pipeline_id"),
        "summary": result.get("ml", {}).get("summary"),
        "report_path": result.get("report", {}).get("report_path"),
    }
    print(json.dumps(printable, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
