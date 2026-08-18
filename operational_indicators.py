"""Camada pura de indicadores operacionais da Aula 24."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable


REGRA_NOMES = {
    "RN01-RN04": "Campos obrigatorios ou estrutura de entrada",
    "RN01": "Estrutura da planilha",
    "RN02": "Campos obrigatorios",
    "RN03": "Lote na base de referencia",
    "RN04": "Status valido",
    "RN05": "Lote não encontrado na base autorizada",
    "RN06": "Status ambiguo para revisao humana",
    "RN07": "Observacao obrigatoria em reprovado",
    "RN08": "Registro consistente",
    "RN09": "Status nao reconhecido",
    "RN10": "Reprovado sem observacao",
    "RN11": "Lote duplicado no mesmo dia",
    "RN12": "Data invalida",
}


@dataclass(frozen=True)
class RuleRanking:
    regra: str
    nome: str
    quantidade: int
    percentual_total: float


@dataclass(frozen=True)
class OperationalIndicators:
    total_registros: int
    registros_validos: int
    percentual_validos: float
    divergencias: int
    percentual_divergencias: float
    ambiguos: int
    percentual_ambiguos: float
    erros_entrada: int
    percentual_erros_entrada: float
    regra_mais_acionada: str
    regra_mais_acionada_nome: str
    regra_mais_acionada_quantidade: int
    taxa_qualidade_entrada: float
    taxa_revisao_humana: float
    taxa_retrabalho: float
    tempo_manual_minutos_por_registro: float
    tempo_automatizado_minutos_por_registro: float
    ganho_estimado_minutos: float
    ranking_regras: tuple[RuleRanking, ...]

    @property
    def ganho_estimado_horas(self) -> float:
        return self.ganho_estimado_minutos / 60


def _percentual(parte: int | float, total: int | float) -> float:
    """Retorna percentual com protecao contra divisao por zero."""
    if total == 0:
        return 0.0
    return (parte / total) * 100


def consolidar_indicadores(
    registros: Iterable[Any],
    *,
    tempo_manual_minutos_por_registro: float = 5,
    tempo_automatizado_minutos_por_registro: float = 1,
) -> OperationalIndicators:
    registros = list(registros)
    total = len(registros)
    classificacoes = Counter(_campo(registro, "classificacao") for registro in registros)
    regras = Counter(
        regra
        for registro in registros
        for regra in [_campo(registro, "regra_violada")]
        if regra and regra != "-"
    )

    validos = classificacoes.get("Válido", 0)
    divergencias = classificacoes.get("Divergência", 0)
    ambiguos = classificacoes.get("Ambíguo", 0)
    erros_entrada = classificacoes.get("Erro de Entrada", 0)
    regra, quantidade = regras.most_common(1)[0] if regras else ("-", 0)

    ranking = tuple(
        RuleRanking(
            regra=regra_item,
            nome=REGRA_NOMES.get(regra_item, "Regra nao catalogada"),
            quantidade=qtd,
            percentual_total=_percentual(qtd, total),
        )
        for regra_item, qtd in regras.most_common()
    )

    ganho_estimado = total * (
        tempo_manual_minutos_por_registro - tempo_automatizado_minutos_por_registro
    )

    return OperationalIndicators(
        total_registros=total,
        registros_validos=validos,
        percentual_validos=_percentual(validos, total),
        divergencias=divergencias,
        percentual_divergencias=_percentual(divergencias, total),
        ambiguos=ambiguos,
        percentual_ambiguos=_percentual(ambiguos, total),
        erros_entrada=erros_entrada,
        percentual_erros_entrada=_percentual(erros_entrada, total),
        regra_mais_acionada=regra,
        regra_mais_acionada_nome=REGRA_NOMES.get(regra, "Sem regras acionadas"),
        regra_mais_acionada_quantidade=quantidade,
        taxa_qualidade_entrada=_percentual(total - erros_entrada, total),
        taxa_revisao_humana=_percentual(ambiguos, total),
        taxa_retrabalho=_percentual(divergencias, total),
        tempo_manual_minutos_por_registro=tempo_manual_minutos_por_registro,
        tempo_automatizado_minutos_por_registro=tempo_automatizado_minutos_por_registro,
        ganho_estimado_minutos=ganho_estimado,
        ranking_regras=ranking,
    )


def _campo(registro: Any, nome: str) -> Any:
    if isinstance(registro, dict):
        return registro.get(nome)
    return getattr(registro, nome)
