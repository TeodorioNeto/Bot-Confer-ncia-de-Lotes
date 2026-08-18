"""
bot.py - Performer do Auditor de Lotes.

Recebe um item por vez (vindo do DataPool no Maestro, ou de um objeto
compatível localmente) e aplica RN02, RN03, RN04, RN05 e RN07. RN01
(estrutura da planilha inteira) é validada uma vez só, no dispatcher,
"""


from src.base_referencia import carregar_base_referencia, verificar_lote_na_base
from src.validacao import (
    COLUNAS_OBRIGATORIAS,
    ERRO_RN07,
    SINONIMOS_STATUS,
    STATUS_REPROVADO,
    normalizar_status,
    status_ambiguo,
    valida_status,
)


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
    divergencias = []
    avisos = []
    analises = []

    def registrar(regra, problema, acao, categoria="divergencia"):
        analises.append(
            {
                "regra": regra,
                "problema": problema,
                "acao": acao,
                "categoria": categoria,
            }
        )
        texto = f"{regra}: {problema}"
        if categoria == "aviso":
            avisos.append(texto)
        else:
            divergencias.append(texto)

    # RN02: todos os campos obrigatórios.
    campos_vazios = [
        coluna
        for coluna in COLUNAS_OBRIGATORIAS
        if _valor_vazio(item.get_value(coluna))
    ]
    if campos_vazios:
        registrar(
            "RN02",
            f"Campos obrigatórios vazios: {', '.join(campos_vazios)}",
            f"Preencher os campos obrigatórios: {', '.join(campos_vazios)}",
        )

    # RN03: lote existe na base de referência
    if not _valor_vazio(lote_id) and not verificar_lote_na_base(
        str(lote_id), base_referencia
    ):
        registrar(
            "RN03",
            "lote_id não existe na base de referência",
            "Corrigir o lote_id ou cadastrar o lote na base de referência",
        )

    # RN04/RN05: status válido e normalizado
    status = item.get_value("status")
    if not _valor_vazio(status):
        status_original = str(status).strip().upper()
        status_normalizado = normalizar_status(status)
        if status_original in SINONIMOS_STATUS:
            registrar(
                "RN05",
                f"Status '{status}' não padronizado",
                f"Normalizar o status para '{status_normalizado}'",
                categoria="aviso",
            )
        if not valida_status(status):
            registrar(
                "RN04",
                f"Status '{status}' não pertence ao domínio permitido",
                "Corrigir para APROVADO, REPROVADO ou PENDENTE",
            )
        if status_ambiguo(status):
            registrar(
                "RN06",
                f"Status '{status}' não reconhecível nem normalizável",
                "Encaminhar o registro para revisão humana",
            )

    # RN07: observação obrigatória quando reprovado.
    observacao = item.get_value("observacao")
    status_normalizado = normalizar_status(status)
    status_original = str(status).strip().upper() if status else ""
    if (
        status_original in STATUS_REPROVADO
        or status_normalizado == "REPROVADO"
    ) and _valor_vazio(observacao):
        registrar(
            "RN07",
            ERRO_RN07,
            "Preencher a observação com a justificativa da reprovação",
        )

    return {
        "lote_id": lote_id,
        "screenshot": item.get_value("screenshot"),
        "divergencias": divergencias,
        "avisos": avisos,
        "analises": analises,
    }


def _valor_vazio(valor):
    return valor is None or str(valor).strip() == ""


if __name__ == "__main__":
    # Ponto de entrada exigido pelo BotCity Runner.
    from main import main

    main()
