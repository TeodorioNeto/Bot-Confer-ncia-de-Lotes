"""
bot.py - Performer do Auditor de Lotes.

Recebe um item por vez (vindo do DataPool no Maestro, ou de um objeto
compatível localmente) e aplica RN02, RN03, RN04, RN05 e RN07. RN01
(estrutura da planilha inteira) é validada uma vez só, no dispatcher,
"""

import logging

from src.base_referencia import carregar_base_referencia, verificar_lote_na_base
from src.validacao import (
    COLUNAS_OBRIGATORIAS,
    STATUS_REPROVADO,
    ERRO_RN07,
    normalizar_status,
    valida_status,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def processar_item(item, base_referencia):
    """
    Aplica as regras de negócio a um único item (uma linha da planilha).

    Args:
        item: objeto com .get_value(chave) - DataPoolEntry real no
              Maestro, ou um fake compatível nos testes locais.
        base_referencia: set de lote_id cadastrados (vem de
                          carregar_base_referencia()).

    Returns:
        dict com lote_id e a lista de divergências encontradas.

    Raises:
        ValueError: se lote_id estiver vazio - erro de item (o
                    Performer deve marcar como erro no DataPool e
                    seguir pro próximo).
    """
    lote_id = item.get_value("lote_id")

    if not lote_id or not str(lote_id).strip():
        raise ValueError("lote_id vazio (RN02)")

    divergencias = []

    # RN02: demais campos obrigatórios
    campos_vazios = [
        coluna
        for coluna in COLUNAS_OBRIGATORIAS
        if coluna != "lote_id" and _valor_vazio(item.get_value(coluna))
    ]
    if campos_vazios:
        divergencias.append(f"RN02: campos vazios: {', '.join(campos_vazios)}")

    # RN03: lote existe na base de referência
    if not verificar_lote_na_base(lote_id, base_referencia):
        divergencias.append("RN03: lote_id não existe na base de referência")

    # RN04/RN05: status válido e normalizado
    status = item.get_value("status")
    try:
        if not valida_status(status):
            divergencias.append(
                f"RN04/RN05: status '{status}' não reconhecível (normalizado: '{normalizar_status(status)}')"
            )
    except ValueError:
        pass  # já reportado como campo vazio na RN02, se "status" estiver na lista

    # RN07: observação obrigatória quando reprovado
    status_original = str(status).strip().upper() if status else ""
    observacao = item.get_value("observacao")
    if status_original in STATUS_REPROVADO and _valor_vazio(observacao):
        divergencias.append(f"RN07: {ERRO_RN07}")

    return {"lote_id": lote_id, "divergencias": divergencias}


def _valor_vazio(valor):
    return valor is None or str(valor).strip() == ""