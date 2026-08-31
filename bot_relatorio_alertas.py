"""Bot C do S10-B: relatorio final e notificacao Telegram/Email."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from botcity.maestro import AutomationTaskFinishStatus, BotMaestroSDK

from config import (
    ALERT_EMAIL_TO,
    LOGS_DIR,
    MAESTRO_ENABLED,
    MAESTRO_KEY,
    MAESTRO_LOGIN,
    MAESTRO_SERVER,
    PIPELINE_BOT_C_LABEL,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_USE_TLS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from src.alertas import SistemaAlertas
from src.logger import setup_logger
from src.relatorio_pipeline import generate_pipeline_report
from wait_for_predecessor import predecessor_task_id_from_parameters, wait_for_predecessor


logger = setup_logger(__name__)


def executar_bot_c(
    maestro=None,
    *,
    alert_system=None,
    report_generator=generate_pipeline_report,
    wait_predecessor=wait_for_predecessor,
) -> dict:
    maestro, connected = _get_maestro(maestro)
    task_id = getattr(maestro, "task_id", None)
    current_task = maestro.get_task(task_id) if connected and task_id else None
    parameters = dict(getattr(current_task, "parameters", None) or {})
    if not connected and not parameters.get("pipeline_results"):
        parameters.update(_load_latest_bot_b_evidence())
    pipeline_id = str(parameters.get("pipeline_id") or uuid4())

    predecessor_id = predecessor_task_id_from_parameters(parameters)
    if connected and predecessor_id:
        wait_predecessor(maestro, predecessor_id)

    results = list(parameters.get("pipeline_results") or [])
    summary = dict(parameters.get("bot_b_summary") or _summarize(results))
    safe_id = "".join(char if char.isalnum() or char in "-_" else "_" for char in pipeline_id)
    report_path = LOGS_DIR / f"pipeline_{safe_id}_relatorio.xlsx"
    report_generator(results, report_path)

    alert_system = alert_system or _build_alert_system()
    alerts = []
    if summary.get("pipeline_sem_ml"):
        alerts.append(
            alert_system.send(
                severity="AVISO",
                title="Pipeline operando sem ML",
                message=(
                    f"Pipeline {pipeline_id}: 100% das "
                    f"{summary.get('divergencias', 0)} divergencias usaram fallback."
                ),
                attachment=report_path,
            ).to_dict()
        )

    if summary.get("dead_letter", 0) or summary.get("pendentes_revisao", 0):
        alerts.append(
            alert_system.send(
                severity="ERRO",
                title="Pipeline concluido com pendencias",
                message=(
                    f"Pipeline {pipeline_id}: dead_letter={summary.get('dead_letter', 0)}, "
                    f"pendentes_revisao={summary.get('pendentes_revisao', 0)}."
                ),
                attachment=report_path,
            ).to_dict()
        )

    if not alerts:
        alerts.append(
            alert_system.send(
                severity="INFO",
                title="Pipeline concluido",
                message=(
                    f"Pipeline {pipeline_id} processou {summary.get('total', len(results))} "
                    "itens sem pendencias de infraestrutura."
                ),
            ).to_dict()
        )

    final_parameters = _append_chain(parameters, pipeline_id, task_id)
    evidence_json = LOGS_DIR / f"pipeline_{safe_id}_bot_c.json"
    evidence_json.write_text(
        json.dumps(
            {
                "pipeline_id": pipeline_id,
                "summary": summary,
                "alerts": alerts,
                "report_path": str(report_path),
                "execution_chain": final_parameters["execution_chain"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if connected and task_id:
        maestro.post_artifact(
            task_id=task_id,
            artifact_name=report_path.name,
            filepath=str(report_path),
        )
        maestro.post_artifact(
            task_id=task_id,
            artifact_name=evidence_json.name,
            filepath=str(evidence_json),
        )
        finish_status = (
            AutomationTaskFinishStatus.PARTIALLY_COMPLETED
            if summary.get("dead_letter", 0) or summary.get("pendentes_revisao", 0)
            else AutomationTaskFinishStatus.SUCCESS
        )
        maestro.finish_task(
            task_id=task_id,
            status=finish_status,
            message=f"Pipeline {pipeline_id} finalizado; relatorio e alertas publicados.",
            total_items=summary.get("total", len(results)),
            processed_items=(
                summary.get("total", len(results)) - summary.get("dead_letter", 0)
            ),
            failed_items=summary.get("dead_letter", 0),
        )

    return {
        "pipeline_id": pipeline_id,
        "connected_maestro": connected,
        "summary": summary,
        "alerts": alerts,
        "report_path": str(report_path),
        "evidence_path": str(evidence_json),
        "execution_chain": final_parameters["execution_chain"],
    }


def _build_alert_system():
    return SistemaAlertas(
        telegram_token=TELEGRAM_BOT_TOKEN,
        telegram_chat_id=TELEGRAM_CHAT_ID,
        smtp_host=SMTP_HOST,
        smtp_port=SMTP_PORT,
        smtp_username=SMTP_USERNAME,
        smtp_password=SMTP_PASSWORD,
        smtp_from=SMTP_FROM,
        email_to=ALERT_EMAIL_TO,
        smtp_use_tls=SMTP_USE_TLS,
        logger=logger,
    )


def _summarize(results):
    divergences = [r for r in results if r.get("status_decisao") == "DIVERGENCIA"]
    fallbacks = [r for r in divergences if r.get("origem_decisao") == "fallback"]
    return {
        "total": len(results),
        "validos": sum(r.get("status_decisao") == "VALIDO" for r in results),
        "divergencias": len(divergences),
        "pendentes_revisao": sum(
            r.get("status_decisao") == "PENDENTE_REVISAO" for r in results
        ),
        "fallback_ml": len(fallbacks),
        "dead_letter": sum(bool(r.get("erro_dado")) for r in results),
        "pipeline_sem_ml": bool(divergences and len(fallbacks) == len(divergences)),
    }


def _append_chain(parameters, pipeline_id, task_id):
    chain = list(parameters.get("execution_chain") or [])
    chain.append(
        {
            "activity_label": PIPELINE_BOT_C_LABEL,
            "task_id": str(task_id or "local"),
            "result": "PIPELINE_FINALIZADO",
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    result = dict(parameters)
    result.update({"pipeline_id": pipeline_id, "execution_chain": chain})
    return result


def _load_latest_bot_b_evidence() -> dict:
    candidates = sorted(
        LOGS_DIR.glob("pipeline_*_bot_b.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return {}
    payload = json.loads(candidates[0].read_text(encoding="utf-8"))
    return {
        "pipeline_id": payload.get("pipeline_id"),
        "pipeline_results": payload.get("results", []),
        "bot_b_summary": payload.get("summary", {}),
        "bot_b_evidence_path": str(candidates[0]),
    }


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


def main():
    result = executar_bot_c()
    print(
        f"Bot C concluido: pipeline_id={result['pipeline_id']} "
        f"relatorio={result['report_path']}"
    )


if __name__ == "__main__":
    main()
