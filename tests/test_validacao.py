import pytest
from src.base_referencia import verificar_lote_na_base, carregar_base_referencia


@pytest.fixture
def base_exemplo():
    return {"LG-2026-00101", "LG-2026-00102", "LG-2026-00104", "LG-2026-00105"}


def test_lote_existente_na_base(base_exemplo):
    assert verificar_lote_na_base("LG-2026-00101", base_exemplo) is True


def test_lote_inexistente_na_base(base_exemplo):
    # Caso do gabarito: LG-2026-00103 não existe na Base_Referencia (RN03)
    assert verificar_lote_na_base("LG-2026-00103", base_exemplo) is False


def test_lote_id_vazio_gera_erro(base_exemplo):
    with pytest.raises(ValueError):
        verificar_lote_na_base("", base_exemplo)


def test_carregar_base_referencia_arquivo_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        carregar_base_referencia(str(tmp_path / "nao_existe.xlsx"))


def test_carregar_base_referencia_real():
    """Teste de integração: carrega o xlsx real e confere o gabarito conhecido."""
    base = carregar_base_referencia()
    assert "LG-2026-00101" in base
    assert "LG-2026-00103" not in base  # esse é o caso de divergência do gabarito