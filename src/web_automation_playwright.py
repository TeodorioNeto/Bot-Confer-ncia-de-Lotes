import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from src.validacao import normalizar_status


load_dotenv()


def preencher_formulario(dados_lote=None, credencial=None):
    """Executa o preenchimento do formulario local usando Playwright."""
    caminho_doc = Path("doc.html").resolve()
    url = caminho_doc.as_uri()
    headless = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
    dados_lote = dados_lote or {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1280, "height": 720})

        try:
            page.goto(url)
            page.locator("#lote").fill(str(dados_lote.get("lote_id") or ""))
            _selecionar_produto(page, dados_lote.get("produto"))
            page.locator(
                f"input[name='status'][value='{_status_formulario(dados_lote.get('status'))}']"
            ).check()
            page.locator("button[type='submit']").click()
            page.locator("#alertSuccess").wait_for(state="visible", timeout=10000)
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
