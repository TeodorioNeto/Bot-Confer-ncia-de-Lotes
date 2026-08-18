import pytest

from gerar_relatorio import data_valida


@pytest.mark.unit
@pytest.mark.skip(reason="RN13 futura de SLA ainda nao foi definida no PDD da atividade.")
def test_rn13_sla_futuro_skip():
    assert False


@pytest.mark.unit
@pytest.mark.xfail(
    reason="Integracao legada ainda envia data ISO; a regra atual aceita apenas DD/MM/AAAA."
)
def test_data_iso_legada_xfail():
    assert data_valida("2026-08-01")
