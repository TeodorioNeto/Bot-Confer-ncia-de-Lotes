"""Ponte entre o bot de lotes e a camada de Machine Learning."""

from __future__ import annotations

import json
import logging
from typing import Any


REVISAO_ML_OFFLINE = "REVISAO_ML_OFFLINE"


def classificar_ambiguo_com_ml(
    item: Any,
    ml_client,
    *,
    logger: logging.Logger | None = None,
) -> dict:
    payload = {
        "lote_id": _valor(item, "lote_id"),
        "status_raw": _valor(item, "status"),
        "turno": _valor(item, "turno"),
        "tem_obs": bool(str(_valor(item, "observacao") or "").strip()),
    }
    predicao = ml_client.classificar(payload) if ml_client is not None else None
    if predicao is None:
        decisao = {
            "lote_id": payload["lote_id"],
            "classe": REVISAO_ML_OFFLINE,
            "probabilidade": 0.0,
            "nivel_confianca": "offline",
            "acao": "revisar",
            "latencia_ms": 0.0,
            "fallback": True,
        }
    else:
        decisao = {
            "lote_id": predicao.lote_id,
            "classe": predicao.classe,
            "probabilidade": predicao.probabilidade,
            "nivel_confianca": predicao.nivel_confianca,
            "acao": predicao.acao,
            "latencia_ms": predicao.latencia_ms,
            "fallback": False,
        }

    if logger is not None:
        logger.info(
            "ml_decision=%s",
            json.dumps(decisao, ensure_ascii=False, sort_keys=True),
        )
    return decisao


def _valor(item: Any, chave: str):
    if hasattr(item, "get_value"):
        return item.get_value(chave)
    if isinstance(item, dict):
        return item.get(chave)
    return getattr(item, chave, None)
