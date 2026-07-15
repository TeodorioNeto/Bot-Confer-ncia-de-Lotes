import pytest
import openpyxl
from src.base_referencia import verificar_lote_na_base, carregar_base_referencia
from src.validacao import normalizar_status, valida_status

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


def test_carregar_base_referencia_com_arquivo_temporario(tmp_path):
    """
    Testa carregar_base_referencia() com um xlsx fictício criado no teste,
    sem depender da planilha real (que não é versionada no Git).
    """
    

    caminho = tmp_path / "base_teste.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Base_Referencia"
    ws.append(["BASE DE REFERÊNCIA DE LOTES (título)"])  # linha de título, ignorada
    ws.append(["lote_id", "codigo_produto", "descricao_produto", "status_cadastro"])
    ws.append(["LG-2026-00101", "COD01", "Setupbox modelo A", "ativo"])
    ws.append(["LG-2026-00102", "COD02", "Setupbox modelo B", "ativo"])
    wb.save(caminho)

    base = carregar_base_referencia(caminho=str(caminho), aba="Base_Referencia")

    assert "LG-2026-00101" in base
    assert "LG-2026-00103" not in base


def test_normaliza_ok_para_aprovado():
    assert normalizar_status("OK") == "APROVADO"


def test_normaliza_nok_para_reprovado():
    assert normalizar_status("NOK") == "REPROVADO"


def test_normaliza_ignora_case_e_espacos():
    assert normalizar_status("  ok  ") == "APROVADO"


def test_normaliza_mantem_status_ja_oficial():
    assert normalizar_status("APROVADO") == "APROVADO"
    assert normalizar_status("PENDENTE") == "PENDENTE"


def test_valida_status_aceita_valores_oficiais():
    assert valida_status("APROVADO") is True
    assert valida_status("REPROVADO") is True
    assert valida_status("PENDENTE") is True


def test_valida_status_aceita_sinonimos_normalizados():
    assert valida_status("OK") is True
    assert valida_status("NOK") is True


def test_valida_status_rejeita_valor_nao_reconhecido():
    # Casos reais do gabarito: "REPROV." e "APROVADO PARCIAL" (RN06)
    assert valida_status("REPROV.") is False
    assert valida_status("APROVADO PARCIAL") is False


def test_valida_status_vazio_gera_erro():
    with pytest.raises(ValueError):
        valida_status("")

    with pytest.raises(ValueError):
        valida_status(None)