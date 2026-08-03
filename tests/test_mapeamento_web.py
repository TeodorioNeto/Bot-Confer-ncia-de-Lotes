import pytest

from src.mapeamento_web import mapear_categoria_produto, preparar_status_inspecao


@pytest.mark.parametrize(
    ("codigo", "categoria"),
    [
        ("TV55-4K-B", "TV"),
        ("MON27-QHD", "MON"),
        ("AC12-SPLIT", "AC"),
        (" tv43-fhd ", "TV"),
    ],
)
def test_mapeia_codigo_do_datapool_para_categoria(codigo, categoria):
    assert mapear_categoria_produto(codigo) == categoria


def test_rejeita_produto_fora_das_tres_categorias():
    with pytest.raises(ValueError):
        mapear_categoria_produto("CPU-X")


@pytest.mark.parametrize(
    ("status", "normalizado", "foi_normalizado"),
    [
        ("APROVADO", "APROVADO", False),
        ("PENDENTE", "PENDENTE", False),
        ("OK", "APROVADO", True),
        ("NOK", "REPROVADO", True),
    ],
)
def test_prepara_status_valido_para_formulario(status, normalizado, foi_normalizado):
    resultado = preparar_status_inspecao(status)

    assert resultado["valido"] is True
    assert resultado["normalizado"] == normalizado
    assert resultado["foi_normalizado"] is foi_normalizado


@pytest.mark.parametrize("status", ["REPROV.", "APROVADO PARCIAL", ""])
def test_encaminha_status_ambiguo_para_revisao(status):
    resultado = preparar_status_inspecao(status)

    assert resultado["valido"] is False
    assert resultado["normalizado"] == ""
