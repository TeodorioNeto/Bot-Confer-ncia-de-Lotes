"""Utilitarios comuns aos bots independentes do pipeline Capstone."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from botcity.maestro import BotMaestroSDK

from config import MAESTRO_ENABLED, MAESTRO_KEY, MAESTRO_LOGIN, MAESTRO_SERVER


LOCAL_EXECUTION = object()


class LocalMaestro:
    """Objeto minimo para execucao explicitamente desconectada."""

    task_id = None
    RAISE_NOT_CONNECTED = False


def get_maestro(maestro=None):
    """Retorna SDK e indica se a execucao esta conectada ao Maestro."""
    if maestro is LOCAL_EXECUTION:
        return LocalMaestro(), False
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


def resolve_parameters(maestro, connected: bool, explicit_parameters=None) -> dict:
    """Le parametros da task ou usa os parametros fornecidos no modo local."""
    if explicit_parameters is not None:
        return dict(explicit_parameters)
    task_id = getattr(maestro, "task_id", None)
    if not connected or not task_id:
        return {}
    task = maestro.get_task(task_id)
    return dict(getattr(task, "parameters", None) or {})


def append_chain(
    parameters: dict,
    *,
    activity_label: str,
    task_id,
    result: str,
) -> dict:
    """Acrescenta uma etapa auditavel sem sobrescrever a cadeia recebida."""
    updated = dict(parameters)
    chain = list(updated.get("execution_chain") or [])
    chain.append(
        {
            "activity_label": activity_label,
            "task_id": str(task_id or "local"),
            "result": result,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    updated["execution_chain"] = chain
    return updated


def write_evidence(logs_dir, pipeline_id: str, suffix: str, payload: dict) -> Path:
    """Grava evidencia JSON usando nome seguro e conteudo UTF-8."""
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(
        char if char.isalnum() or char in "-_" else "_" for char in pipeline_id
    )
    path = logs_dir / f"pipeline_{safe_id}_{suffix}.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return path


def read_json(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
