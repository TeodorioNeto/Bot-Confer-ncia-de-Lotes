from unittest.mock import Mock, patch
import src.web_automation_playwright
import src.web_automation_selenium
import openpyxl
import pytest
from src import web_automation, web_evidencias
from src.web_evidencias import montar_caminho_screenshot


class ItemWebTeste:
    def __init__(self, valores):
        self.valores = valores

    def get_value(self, chave):
        return self.valores.get(chave)


def test_monta_dados_lote_a_partir_do_item_datapool():
    item = ItemWebTeste(
        {
            "lote_id": "LG-2026-00101",
            "produto": "TV",
            "linha": "A",
            "turno": "MANHA",
            "status": "APROVADO",
            "responsavel": "Ana",
            "data": "14/06/2026",
            "observacao": "",
        }
    )

    dados = web_automation.montar_dados_lote(item)

    assert dados["lote_id"] == "LG-2026-00101"
    assert dados["produto"] == "TV"
    assert dados["status"] == "APROVADO"
    assert "observacao" in dados


def test_carrega_primeiro_lote_da_planilha_usada_pelo_botcity(tmp_path):
    caminho = tmp_path / "inspecao_lotes_dia.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inspecao_14_06_2026"
    ws.append(["PLANILHA DE INSPECAO"])
    ws.append(["Arquivo", "Sistema", "Registros"])
    ws.append(
        [
            "lote_id",
            "produto",
            "linha",
            "turno",
            "status",
            "responsavel",
            "data",
            "observacao",
        ]
    )
    ws.append(["LG-2026-00101", "TV", "A", "MANHA", "APROVADO", "Ana", "14/06/2026", ""])
    wb.save(caminho)

    dados = web_automation.carregar_primeiro_lote_da_planilha(caminho)

    assert dados["lote_id"] == "LG-2026-00101"
    assert dados["produto"] == "TV"
    assert dados["status"] == "APROVADO"


def test_carrega_primeiro_resultado_com_ocorrencia_para_formulario_analise(tmp_path):
    caminho = tmp_path / "inspecao_lotes_dia.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inspecao_14_06_2026"
    ws.append(["PLANILHA DE INSPECAO"])
    ws.append(["Arquivo", "Sistema", "Registros"])
    ws.append(
        [
            "lote_id",
            "produto",
            "linha",
            "turno",
            "status",
            "responsavel",
            "data",
            "observacao",
        ]
    )
    ws.append(["LG-2026-00101", "TV", "A", "MANHA", "APROVADO", "Ana", "14/06/2026", ""])
    ws.append(["LG-2026-00102", "TV", "A", "MANHA", "NOK", "Bia", "14/06/2026", ""])

    base = wb.create_sheet("Base_Referencia")
    base.append(["BASE DE REFERENCIA"])
    base.append(["lote_id", "codigo_produto", "descricao_produto", "status_cadastro"])
    base.append(["LG-2026-00101", "P001", "TV", "ativo"])
    base.append(["LG-2026-00102", "P002", "TV", "ativo"])
    wb.save(caminho)

    resultado = web_automation.carregar_primeiro_resultado_da_planilha(caminho)

    assert resultado["dados_lote"]["lote_id"] == "LG-2026-00102"
    assert resultado["linha_planilha"] == 5
    assert any(analise["regra"] == "RN07" for analise in resultado["analises"])


def test_carrega_todas_ocorrencias_da_planilha_para_formulario_analise(tmp_path):
    caminho = tmp_path / "inspecao_lotes_dia.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inspecao_14_06_2026"
    ws.append(["PLANILHA DE INSPECAO"])
    ws.append(["Arquivo", "Sistema", "Registros"])
    ws.append(
        [
            "lote_id",
            "produto",
            "linha",
            "turno",
            "status",
            "responsavel",
            "data",
            "observacao",
        ]
    )
    ws.append(["LG-2026-00101", "TV", "A", "MANHA", "APROVADO", "Ana", "14/06/2026", ""])
    ws.append(["LG-2026-00102", "TV", "A", "MANHA", "NOK", "Bia", "14/06/2026", ""])
    ws.append(["LG-2026-00103", "TV", "A", "MANHA", "APROVADO PARCIAL", "Caio", "14/06/2026", ""])

    base = wb.create_sheet("Base_Referencia")
    base.append(["BASE DE REFERENCIA"])
    base.append(["lote_id", "codigo_produto", "descricao_produto", "status_cadastro"])
    base.append(["LG-2026-00101", "P001", "TV", "ativo"])
    base.append(["LG-2026-00102", "P002", "TV", "ativo"])
    base.append(["LG-2026-00103", "P003", "TV", "ativo"])
    wb.save(caminho)

    resultado = web_automation.carregar_resultado_planilha_para_web(caminho)
    regras = [analise["regra"] for analise in resultado["analises"]]
    linhas = [analise["linha_planilha"] for analise in resultado["analises"]]

    assert resultado["dados_lote"]["lote_id"] == "LG-2026-00102"
    assert "RN07" in regras
    assert "RN04" in regras
    assert "RN06" in regras
    assert 5 in linhas
    assert 6 in linhas


def test_processar_datapool_usa_playwright_por_padrao(monkeypatch):
    monkeypatch.delenv("WEB_AUTOMATION_DRIVER", raising=False)
    processar_playwright = Mock(return_value=2)

    with patch(
        "src.web_automation_playwright.processar_datapool_playwright",
        processar_playwright,
    ):
        resultado = web_automation.processar_datapool()

    assert resultado == 2
    processar_playwright.assert_called_once_with(callback_log=None, theme="dark")


def test_processar_datapool_usa_selenium_quando_configurado(monkeypatch):
    monkeypatch.setenv("WEB_AUTOMATION_DRIVER", "selenium")
    processar_selenium = Mock(return_value=3)

    with patch(
        "src.web_automation_selenium.processar_datapool_selenium",
        processar_selenium,
    ):
        resultado = web_automation.processar_datapool()

    assert resultado == 3
    processar_selenium.assert_called_once_with(callback_log=None, theme="dark")


def test_processar_datapool_rejeita_driver_desconhecido():
    with pytest.raises(ValueError):
        web_automation.processar_datapool(driver="desconhecido")


def test_processar_datapool_repassa_opcoes_da_nova_versao(monkeypatch):
    monkeypatch.setenv("WEB_AUTOMATION_DRIVER", "selenium")
    processar_selenium = Mock(return_value=4)
    callback_log = Mock()

    with patch(
        "src.web_automation_selenium.processar_datapool_selenium",
        processar_selenium,
    ):
        resultado = web_automation.processar_datapool(
            delay_passo=0.4,
            callback_log=callback_log,
            theme="light",
        )

    assert resultado == 4
    processar_selenium.assert_called_once_with(
        delay_passo=0.4,
        callback_log=callback_log,
        theme="light",
    )


def test_processar_datapool_repassa_retorno_de_evidencias(monkeypatch):
    monkeypatch.setenv("WEB_AUTOMATION_DRIVER", "playwright")
    retorno = {
        "total": 1,
        "evidencias": [
            {
                "lote_id": "LG-2026-00101",
                "screenshot": "logs/screenshots/playwright/evidencia.png",
                "driver": "playwright",
            }
        ],
    }
    processar_playwright = Mock(return_value=retorno)

    with patch(
        "src.web_automation_playwright.processar_datapool_playwright",
        processar_playwright,
    ):
        resultado = web_automation.processar_datapool(return_evidencias=True)

    assert resultado == retorno
    processar_playwright.assert_called_once_with(
        callback_log=None,
        theme="dark",
        return_evidencias=True,
    )


def test_montar_caminho_screenshot_cria_nome_seguro(monkeypatch, tmp_path):
    monkeypatch.setattr(web_evidencias, "SCREENSHOTS_DIR", tmp_path)

    caminho = montar_caminho_screenshot(
        {"lote_id": "LG/2026 00101"},
        "selenium",
    )

    assert "selenium_LG_2026_00101.png" in caminho.name
    assert caminho.parent.name == "selenium"
    assert caminho.parent.exists()
