import logging
import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from src.validacao import normalizar_status
from src.web_evidencias import montar_caminho_screenshot, obter_url_automacao


load_dotenv()
logger = logging.getLogger(__name__)


def preencher_formulario(
    dados_lote=None,
    credencial=None,
    screenshot_path=None,
    analises=None,
    linha_planilha=None,
):
    """Executa o preenchimento da tela simulada de inspecao usando Playwright."""
    url = obter_url_automacao()
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
            logger.info(
                "Iniciando automacao Playwright para lote %s.",
                dados_lote.get("lote_id"),
            )
            page.goto(url)
            page.locator("#lote_id").fill(str(dados_lote.get("lote_id") or ""))
            page.locator("#produto").fill(str(dados_lote.get("produto") or ""))
            page.locator("#linha").fill(str(dados_lote.get("linha") or ""))
            page.locator("#turno").fill(str(dados_lote.get("turno") or ""))
            page.locator("#status").select_option(
                _status_formulario(dados_lote.get("status"))
            )
            page.locator("#responsavel").fill(
                str(dados_lote.get("responsavel") or "")
            )
            page.locator("#data").fill(str(dados_lote.get("data") or ""))
            page.locator("#observacao").fill(str(dados_lote.get("observacao") or ""))
            page.locator("#btn-processar").click()
            page.locator("#resultado").wait_for(state="visible", timeout=10000)
            _registrar_analises(page, dados_lote, analises or [], linha_planilha)
            page.screenshot(path=str(caminho_screenshot), full_page=True)
            logger.info("Screenshot Playwright gerado em %s.", caminho_screenshot)
            return {
                "driver": "playwright",
                "screenshot": str(caminho_screenshot),
                "analises_registradas": len(analises or []),
            }
        finally:
            browser.close()


def _status_formulario(status):
    status_normalizado = normalizar_status(status)
    if status_normalizado in {"APROVADO", "REPROVADO", "PENDENTE"}:
        return status_normalizado
    return "PENDENTE"


def _registrar_analises(page, dados_lote, analises, linha_planilha):
    for analise in analises:
        page.locator("#linha_planilha").fill(str(linha_planilha or ""))
        page.locator("#analise_lote_id").fill(str(dados_lote.get("lote_id") or "(vazio)"))
        page.locator("#regra").fill(str(analise.get("regra") or ""))
        page.locator("#problema").fill(str(analise.get("problema") or ""))
        page.locator("#acao_recomendada").fill(str(analise.get("acao") or ""))
        revisao = (
            "Sim (aviso)"
            if analise.get("categoria") == "aviso"
            else "Sim (divergencia)"
        )
        page.locator("#revisao").select_option(revisao)
        page.locator("#btn-adicionar-analise").click()


if __name__ == "__main__":
    preencher_formulario()
