"""
src/web_automation_selenium.py
Orquestrador Selenium com iteração dinâmica sobre o DataPool.
"""

import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from src.pages.form_page import FormPageSelenium
from src.pages.login_page import LoginPageSelenium
from src.web_automation_playwright import carregar_datapool_tratado
from src.web_evidencias import montar_caminho_screenshot, obter_url_automacao

load_dotenv()
logger = logging.getLogger(__name__)


def criar_driver():
    """Inicializa o navegador Chrome usando Selenium WebDriver."""
    options = webdriver.ChromeOptions()

    if os.getenv("SELENIUM_HEADLESS", "false").lower() == "true":
        options.add_argument("--headless=new")

    options.add_argument("--start-maximized")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    return driver


def processar_datapool_selenium(delay_passo=0.2):
    """Lê a planilha de inspeção e processa cada lote sequencialmente via Selenium."""
    url = obter_url_automacao()
    lotes = carregar_datapool_tratado()
    logger.info("Carregados %d lotes para processamento Selenium.", len(lotes))

    driver = criar_driver()
    wait = WebDriverWait(driver, 10)

    try:
        driver.get(url)

        login_page = LoginPageSelenium(driver, wait, delay_passo=delay_passo)
        form_page = FormPageSelenium(driver, wait, delay_passo=delay_passo)

        login_page.fazer_login()

        processados = 0
        for idx, item in enumerate(lotes, start=1):
            logger.info(
                "[%d/%d] [Selenium] Preenchendo lote %s | Produto: %s | Status: %s",
                idx,
                len(lotes),
                item["lote_id"],
                item["produto"],
                item["status"],
            )

            # 1. Recarrega a página para garantir estado limpo a cada item
            driver.refresh()

            # 2. Preenche os novos dados da iteração
            form_page.preencher_lote(item)

            # 3. Submete o formulário
            sucesso = form_page.submeter_e_aguardar()

            # 4. Salva a evidência usando o método nativo estável do Selenium
            driver.execute_script(
                "window.prepararEvidenciaVisual && window.prepararEvidenciaVisual()"
            )
            caminho_screenshot = montar_caminho_screenshot(item, "selenium")
            caminho_screenshot.parent.mkdir(parents=True, exist_ok=True)
            
            # Captura segura sem crashar o renderizador do Chrome
            driver.save_screenshot(str(caminho_screenshot))

            if sucesso:
                logger.info("✓ [Selenium] Lote %s submetido com Sucesso!", item["lote_id"])

            processados += 1

        time.sleep(2)
        return processados

    except Exception as e:
        logger.error("Erro durante a execução no Selenium: %s", e)
        raise e
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    qtd = processar_datapool_selenium(delay_passo=0.1)
    print(
        f"\n==================================================\n"
        f" [SUCESSO] Processamento do DataPool (Selenium) concluído!\n"
        f" Total de lotes processados e fotografados: {qtd}\n"
        f"==================================================\n"
    )