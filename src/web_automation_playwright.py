import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from src.validacao import normalizar_status
from src.web_evidencias import montar_caminho_screenshot


load_dotenv()
logger = logging.getLogger(__name__)


def preencher_formulario(dados_lote=None, credencial=None, screenshot_path=None):
    """Executa o preenchimento do formulario local usando Playwright."""
    caminho_doc = Path("doc.html").resolve()
    url = caminho_doc.as_uri()
    headless = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
    dados_lote = dados_lote or {}
    caminho_screenshot = montar_caminho_screenshot(
        dados_lote,
        "playwright",
        screenshot_path=screenshot_path,
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1280, "height": 720})

        try:
            logger.info("Iniciando automacao Playwright para lote %s.", dados_lote.get("lote_id"))
            page.goto(url)
            page.locator("#lote").fill(str(dados_lote.get("lote_id") or ""))
            _selecionar_produto(page, dados_lote.get("produto"))
            page.locator(
                f"input[name='status'][value='{_status_formulario(dados_lote.get('status'))}']"
            ).check()
            page.locator("button[type='submit']").click()
            page.locator("#alertSuccess").wait_for(state="visible", timeout=10000)
            page.screenshot(path=str(caminho_screenshot), full_page=True)
            logger.info("Screenshot Playwright gerado em %s.", caminho_screenshot)
            return {"driver": "playwright", "screenshot": str(caminho_screenshot)}
        finally:
            browser.close()


def _selecionar_produto(page, produto):
    opcoes = page.locator("#produto option").evaluate_all(
        "(options) => options.map((option) => option.value)"
    )
    produto = str(produto or "").strip()
    if produto in opcoes:
        page.locator("#produto").select_option(value=produto)
    else:
        page.locator("#produto").select_option(index=1)


def _status_formulario(status):
    status_normalizado = normalizar_status(status)
    if status_normalizado == "PENDENTE":
        return "Pendente"
    if status_normalizado == "APROVADO":
        return "Concluído"
    return "Em Processamento"


if __name__ == "__main__":
    preencher_formulario()
