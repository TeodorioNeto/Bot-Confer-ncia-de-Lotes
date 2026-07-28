from unittest.mock import Mock, patch

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


def test_preencher_formulario_usa_playwright_por_padrao(monkeypatch):
    monkeypatch.delenv("WEB_AUTOMATION_DRIVER", raising=False)
    preencher_playwright = Mock()

    with patch(
        "src.web_automation_playwright.preencher_formulario",
        preencher_playwright,
    ):
        web_automation.preencher_formulario({"lote_id": "LG-2026-00101"})

    preencher_playwright.assert_called_once_with(
        dados_lote={"lote_id": "LG-2026-00101"},
        credencial=None,
        screenshot_path=None,
    )


def test_preencher_formulario_usa_selenium_quando_configurado(monkeypatch):
    monkeypatch.setenv("WEB_AUTOMATION_DRIVER", "selenium")
    preencher_selenium = Mock()

    with patch(
        "src.web_automation_selenium.preencher_formulario",
        preencher_selenium,
    ):
        web_automation.preencher_formulario({"lote_id": "LG-2026-00101"})

    preencher_selenium.assert_called_once_with(
        dados_lote={"lote_id": "LG-2026-00101"},
        credencial=None,
        screenshot_path=None,
    )


def test_preencher_formulario_rejeita_driver_desconhecido():
    with pytest.raises(ValueError):
        web_automation.preencher_formulario(driver="desconhecido")


def test_preencher_formulario_repassa_caminho_screenshot(monkeypatch, tmp_path):
    monkeypatch.setenv("WEB_AUTOMATION_DRIVER", "selenium")
    preencher_selenium = Mock()
    screenshot = tmp_path / "evidencias" / "lote.png"

    with patch(
        "src.web_automation_selenium.preencher_formulario",
        preencher_selenium,
    ):
        web_automation.preencher_formulario(
            {"lote_id": "LG-2026-00101"},
            screenshot_path=screenshot,
        )

    preencher_selenium.assert_called_once_with(
        dados_lote={"lote_id": "LG-2026-00101"},
        credencial=None,
        screenshot_path=screenshot,
    )


def test_montar_caminho_screenshot_cria_nome_seguro(monkeypatch, tmp_path):
    monkeypatch.setattr(web_evidencias, "SCREENSHOTS_DIR", tmp_path)

    caminho = montar_caminho_screenshot(
        {"lote_id": "LG/2026 00101"},
        "selenium",
    )

    assert "selenium_LG_2026_00101.png" in caminho.name
    assert caminho.parent.exists()
