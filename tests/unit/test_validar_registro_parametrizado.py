from unittest.mock import MagicMock

import pytest

from gerar_relatorio import validar_registro


def registro_base(**sobrescritas):
    registro = {
        "aba_origem": "Insp_01_08_2026",
        "linha_planilha": 4,
        "data_referencia": "2026-08-01",
        "lote_id": "LG-2026-00001",
        "produto": "AC12-SPLIT",
        "linha": "L1",
        "turno": "MANHA",
        "status": "APROVADO",
        "responsavel": "Analista Teste",
        "data": "01/08/2026",
        "observacao": "Inspecao sem divergencia",
    }
    registro.update(sobrescritas)
    return registro


@pytest.mark.unit
@pytest.mark.parametrize(
    ("sobrescritas", "ocorrencia", "classificacao", "regra"),
    [
        pytest.param({}, 1, "Válido", "-", id="registro-valido"),
        pytest.param(
            {"lote_id": "LG-2026-99999"},
            1,
            "Divergência",
            "RN05",
            id="lote-fora-base-referencia",
        ),
        pytest.param(
            {"status": "APROVADO PARCIAL"},
            1,
            "Ambíguo",
            "RN09",
            id="status-ambiguo",
        ),
        pytest.param(
            {"status": "REPROVADO", "observacao": ""},
            1,
            "Divergência",
            "RN10",
            marks=pytest.mark.regression,
            id="reprovado-sem-observacao",
        ),
        pytest.param(
            {},
            2,
            "Divergência",
            "RN11",
            id="lote-duplicado-no-dia",
        ),
        pytest.param(
            {"data": "31/02/2026"},
            1,
            "Erro de Entrada",
            "RN12",
            id="data-invalida",
        ),
    ],
)
def test_validar_registro_parametrizado(
    sobrescritas,
    ocorrencia,
    classificacao,
    regra,
):
    carregar_base_referencia = MagicMock(return_value={"LG-2026-00001"})

    resultado = validar_registro(
        registro_base(**sobrescritas),
        ocorrencia,
        carregar_base_referencia(),
    )

    carregar_base_referencia.assert_called_once()
    assert resultado.classificacao == classificacao
    assert resultado.regra_violada == regra
