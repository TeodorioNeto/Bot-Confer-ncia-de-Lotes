import pytest
import openpyxl
from src.base_referencia import verificar_lote_na_base, carregar_base_referencia
from src.relatorio import gerar_relatorio_divergencias

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


def test_gera_relatorio_com_divergencias(tmp_path):
    divergencias = [
        {"linha": 6, "lote_id": "LG-2026-00103", "regra": "RN03", "problema": "lote_id não existe na base de referência"},
        {"linha": 27, "lote_id": None, "regra": "RN02", "problema": "lote_id vazio"},
    ]
    caminho_saida = tmp_path / "relatorio_teste.xlsx"

    resultado = gerar_relatorio_divergencias(divergencias, caminho_saida=caminho_saida)

    assert resultado.exists()

    wb = openpyxl.load_workbook(resultado)
    ws = wb.active
    assert ws["A1"].value == "Linha"
    assert ws["B1"].value == "Lote ID"
    assert ws["A2"].value == 6
    assert ws["B2"].value == "LG-2026-00103"
    assert ws["A3"].value == 27


def test_gera_relatorio_vazio_sem_divergencias(tmp_path):
    caminho_saida = tmp_path / "relatorio_vazio.xlsx"

    resultado = gerar_relatorio_divergencias([], caminho_saida=caminho_saida)

    assert resultado.exists()
    wb = openpyxl.load_workbook(resultado)
    ws = wb.active
    assert ws["A1"].value == "Linha"
    assert ws.max_row == 1  # só o cabeçalho, nenhuma divergência


def test_gera_relatorio_cria_pasta_data_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    resultado = gerar_relatorio_divergencias([])

    assert resultado.exists()
    assert "data" in str(resultado)
    assert "output" in str(resultado)