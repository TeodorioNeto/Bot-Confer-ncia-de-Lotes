import main
from main import _processar_evidencia_web_do_item, _registrar_evidencia_no_item


class ItemDataPoolFake:
    def __init__(self):
        self.values = {"screenshot": ""}


def test_registra_caminho_da_evidencia_no_item_datapool():
    item = ItemDataPoolFake()
    resultado = {"lote_id": "LG-2026-00101", "screenshot": ""}
    evidencias = {
        "LG-2026-00101": {
            "lote_id": "LG-2026-00101",
            "screenshot": "logs/screenshots/playwright/LG-2026-00101.png",
            "driver": "playwright",
        }
    }

    _registrar_evidencia_no_item(item, resultado, evidencias)

    assert item.values["screenshot"] == "logs/screenshots/playwright/LG-2026-00101.png"
    assert resultado["screenshot"] == "logs/screenshots/playwright/LG-2026-00101.png"


def test_mantem_item_sem_alteracao_quando_nao_ha_evidencia():
    item = ItemDataPoolFake()
    resultado = {"lote_id": "LG-2026-99999", "screenshot": ""}

    _registrar_evidencia_no_item(item, resultado, {})

    assert item.values["screenshot"] == ""
    assert resultado["screenshot"] == ""


def test_processa_evidencia_web_do_item_datapool(monkeypatch):
    item = ItemDataPoolFake()
    resultado = {"lote_id": "LG-2026-00101", "screenshot": ""}
    resumo_web = {
        "driver": "playwright",
        "modo": "item_datapool",
        "itens_processados": 0,
        "evidencias": [],
        "erros": [],
    }

    monkeypatch.setattr(
        main,
        "processar_item_web",
        lambda item, driver: {
            "lote_id": "LG-2026-00101",
            "screenshot": "logs/screenshots/playwright/LG-2026-00101.png",
            "driver": driver,
        },
    )

    _processar_evidencia_web_do_item(item, resultado, resumo_web)

    assert item.values["screenshot"] == "logs/screenshots/playwright/LG-2026-00101.png"
    assert resultado["screenshot"] == "logs/screenshots/playwright/LG-2026-00101.png"
    assert resumo_web["itens_processados"] == 1
    assert resumo_web["evidencias"][0]["lote_id"] == "LG-2026-00101"
