import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


load_dotenv()


def preencher_formulario():
    """Executa o preenchimento do formulario local usando Playwright."""
    caminho_doc = Path("doc.html").resolve()
    url = caminho_doc.as_uri()
    headless = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1280, "height": 720})

        try:
            page.goto(url)
            page.locator("#lote").fill("LOTE-2026-0001")
            page.locator("#produto").select_option(index=1)
            page.locator("input[name='status']").nth(2).check()
            page.locator("button[type='submit']").click()
            page.locator("#alertSuccess").wait_for(state="visible", timeout=10000)
        finally:
            browser.close()


if __name__ == "__main__":
    preencher_formulario()
