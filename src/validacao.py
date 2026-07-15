"""
RN04 - Valida se o campo status possui um valor dentro do domínio
       conhecido (PDD seção 12).
RN05 - Normaliza sinônimos de status para os valores oficiais
       (OK -> APROVADO, NOK -> REPROVADO) (PDD seção 12).
"""

STATUS_VALIDOS = {"APROVADO", "REPROVADO", "PENDENTE"}
SINONIMOS_STATUS = {"OK": "APROVADO", "NOK": "REPROVADO"}


def normalizar_status(status):
    """
    RN05: normaliza sinônimos conhecidos de status para o valor oficial.

    Retorna o status normalizado (maiúsculas, sinônimos mapeados). Não
    lança erro para valores não reconhecidos — quem decide se é válido
    é a valida_status().
    """
    if status is None:
        return status
    s = str(status).strip().upper()
    return SINONIMOS_STATUS.get(s, s)


def valida_status(status):
    """
    RN04: valida se o status (após normalização pela RN05) pertence ao
    domínio conhecido de valores (APROVADO, REPROVADO, PENDENTE).

    Returns:
        True se o status normalizado é reconhecido.
        False se não é reconhecido (divergência que exige intervenção
        humana - ex: "REPROV." ou "APROVADO PARCIAL").

    Raises:
        ValueError: se status estiver vazio (RN02).
    """
    if not status or not str(status).strip():
        raise ValueError("status é obrigatório (RN02/RN04)")

    normalizado = normalizar_status(status)
    return normalizado in STATUS_VALIDOS