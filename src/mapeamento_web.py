"""Mapeamentos entre os valores do DataPool e o formulario web."""

from src.validacao import normalizar_status


CATEGORIAS_PRODUTO = {
    "TV": "TV",
    "MON": "MON",
    "AC": "AC",
}

STATUS_INSPECAO_VALIDOS = {"APROVADO", "REPROVADO", "PENDENTE"}


def mapear_categoria_produto(codigo_produto):
    """Converte o codigo do produto em uma das tres categorias da tela."""
    codigo = str(codigo_produto or "").strip().upper()

    for prefixo, categoria in CATEGORIAS_PRODUTO.items():
        if codigo.startswith(prefixo):
            return categoria

    raise ValueError(
        f"Produto '{codigo_produto}' nao pertence as categorias TV, MON ou AC."
    )


def preparar_status_inspecao(status):
    """Normaliza OK/NOK e identifica status que exigem revisao humana."""
    original = str(status or "").strip().upper()
    normalizado = normalizar_status(original)
    valido = normalizado in STATUS_INSPECAO_VALIDOS

    return {
        "original": original,
        "normalizado": normalizado if valido else "",
        "valido": valido,
        "foi_normalizado": valido and original != normalizado,
    }
