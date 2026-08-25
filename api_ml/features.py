"""Codificacao compartilhada entre treino e API de predicao."""

from __future__ import annotations


STATUS_MAP = {
    "APROVADO": 0,
    "OK": 0,
    "PENDENTE": 1,
    "EM ANALISE": 2,
    "AJUSTE LINHA": 3,
    "ESPECIFICACAO EM REVISAO": 4,
    "REPROVADO": 5,
    "NOK": 5,
}

TURNO_MAP = {
    "MANHA": 0,
    "TARDE": 1,
    "NOITE": 2,
}

CLASSES = ("válido_automático", "revisar", "recusar_automático")


def codificar_status(status_raw: str) -> int:
    chave = _normalizar(status_raw)
    return STATUS_MAP.get(chave, 6)


def codificar_turno(turno: str) -> int:
    chave = _normalizar(turno)
    if chave not in TURNO_MAP:
        raise ValueError("turno inválido")
    return TURNO_MAP[chave]


def codificar_features(status_raw: str, turno: str, tem_obs: bool) -> list[int]:
    return [
        codificar_status(status_raw),
        codificar_turno(turno),
        int(bool(tem_obs)),
    ]


def _normalizar(valor: str) -> str:
    return str(valor or "").strip().upper()
