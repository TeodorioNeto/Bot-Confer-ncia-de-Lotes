import pytest

from gerar_relatorio import RegistroValidado
from operational_indicators import _percentual, consolidar_indicadores


def registro(classificacao, regra="-"):
    return RegistroValidado(
        aba_origem="Insp_01_08_2026",
        linha_planilha=4,
        data_referencia="2026-08-01",
        lote_id="LG-2026-00001",
        produto="AC12-SPLIT",
        linha="L1",
        turno="MANHA",
        status_original="APROVADO",
        status_normalizado="APROVADO",
        responsavel="Analista Teste",
        data_inspecao="01/08/2026",
        observacao="Sem divergencia",
        classificacao=classificacao,
        regra_violada=regra,
        motivo="Cenario controlado",
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("parte", "total", "esperado"),
    [
        pytest.param(25, 100, 25.0, id="caso-normal"),
        pytest.param(1, 4, 25.0, id="fracao"),
        pytest.param(10, 0, 0.0, id="divisao-por-zero"),
    ],
)
def test_percentual_com_protecao(parte, total, esperado):
    assert _percentual(parte, total) == esperado


@pytest.mark.unit
@pytest.mark.parametrize(
    ("registros", "esperado"),
    [
        pytest.param(
            [
                registro("Válido"),
                registro("Divergência", "RN05"),
                registro("Divergência", "RN05"),
                registro("Divergência", "RN10"),
                registro("Ambíguo", "RN09"),
                registro("Erro de Entrada", "RN12"),
            ],
            {
                "total": 6,
                "validos": 1,
                "divergencias": 3,
                "ambiguos": 1,
                "erros": 1,
                "regra": "RN05",
                "regra_qtd": 2,
                "qualidade": 83.3333333333,
                "revisao": 16.6666666667,
                "retrabalho": 50.0,
                "ganho": 24,
            },
            id="mix-operacional-com-regra-mais-acionada",
        )
    ],
)
def test_consolidar_dez_indicadores_operacionais(registros, esperado):
    indicadores = consolidar_indicadores(registros)

    assert indicadores.total_registros == esperado["total"]
    assert indicadores.registros_validos == esperado["validos"]
    assert indicadores.percentual_validos == pytest.approx(16.6666666667)
    assert indicadores.divergencias == esperado["divergencias"]
    assert indicadores.percentual_divergencias == pytest.approx(50.0)
    assert indicadores.ambiguos == esperado["ambiguos"]
    assert indicadores.percentual_ambiguos == pytest.approx(16.6666666667)
    assert indicadores.erros_entrada == esperado["erros"]
    assert indicadores.percentual_erros_entrada == pytest.approx(16.6666666667)
    assert indicadores.regra_mais_acionada == esperado["regra"]
    assert indicadores.regra_mais_acionada_quantidade == esperado["regra_qtd"]
    assert indicadores.taxa_qualidade_entrada == pytest.approx(esperado["qualidade"])
    assert indicadores.taxa_revisao_humana == pytest.approx(esperado["revisao"])
    assert indicadores.taxa_retrabalho == pytest.approx(esperado["retrabalho"])
    assert indicadores.ganho_estimado_minutos == esperado["ganho"]
    assert indicadores.ranking_regras[0].regra == "RN05"
