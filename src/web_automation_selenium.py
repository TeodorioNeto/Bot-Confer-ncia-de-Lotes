"""
src/web_automation_selenium.py
Orquestrador Selenium com suporte a sincronização de Tema (Dark/Light) e iteração dinâmica sobre o DataPool.
"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from src.logger import setup_logger
from src.pages.form_page import FormPageSelenium
from src.pages.login_page import LoginPageSelenium
from src.web_automation_playwright import carregar_datapool_tratado
from src.web_evidencias import montar_caminho_screenshot, obter_url_automacao

load_dotenv()

logger = setup_logger("SeleniumEngine")


def emitir_log_selenium(mensagem, tipo="info", callback_log=None):
    """Registra o log no terminal do VS Code e dispara a atualização via SSE para o HTML principal."""
    if tipo == "info":
        logger.info(mensagem)
    elif tipo == "warn":
        logger.warning(mensagem)
    elif tipo == "error":
        logger.error(mensagem)
    elif tipo == "success":
        logger.info(mensagem)

    if callback_log:
        try:
            callback_log(mensagem, tipo)
        except Exception:
            pass


def criar_driver():
    """Inicializa o navegador Microsoft Edge usando Selenium WebDriver com as opções corretas."""
    options = webdriver.EdgeOptions()

    if os.getenv("SELENIUM_HEADLESS", "false").lower() == "true":
        options.add_argument("--headless=new")

    options.add_argument("--start-maximized")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    service = EdgeService(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=options)
    driver.maximize_window()
    return driver


def processar_datapool_selenium(delay_passo=0.2, callback_log=None, theme="dark"):
    """Lê a planilha de inspeção e processa cada lote sequencialmente via Selenium com suporte a temas."""
    url = obter_url_automacao()
    lotes = carregar_datapool_tratado()

    if not lotes:
        emitir_log_selenium("DataPool está vazio ou a planilha não foi localizada.", "warn", callback_log)
        return 0

    emitir_log_selenium(f"Iniciando execução Selenium | Total de lotes: {len(lotes)} | Tema: {theme.upper()}", "info", callback_log)

    driver = criar_driver()
    wait = WebDriverWait(driver, 10)

    try:
        emitir_log_selenium(f"Acessando a URL do formulário: {url}", "info", callback_log)
        driver.get(url)

        # Aplica o tema correto na nova janela do Selenium via JavaScript
        if theme == "light":
            driver.execute_script("""
                document.documentElement.setAttribute('data-theme', 'light');
                const toggle = document.getElementById('themeToggle');
                if (toggle) toggle.checked = true;
            """)

        login_page = LoginPageSelenium(driver, wait, delay_passo=delay_passo)
        form_page = FormPageSelenium(driver, wait, delay_passo=delay_passo)

        emitir_log_selenium("Realizando autenticação na plataforma...", "info", callback_log)
        login_page.fazer_login()

        processados = 0
        for idx, item in enumerate(lotes, start=1):
            msg_lote = f"[{idx:02d}/{len(lotes):02d}] Lote: {item['lote_id']} | Produto: {item['produto']} | Status: {item['status']}"
            emitir_log_selenium(msg_lote, "info", callback_log)

            driver.execute_script("document.getElementById('formLote').reset();")

            form_page.preencher_lote(item)
            sucesso = form_page.submeter_e_aguardar()

            driver.execute_script("window.prepararEvidenciaVisual && window.prepararEvidenciaVisual()")
            caminho_screenshot = montar_caminho_screenshot(item, "selenium")
            caminho_screenshot.parent.mkdir(parents=True, exist_ok=True)
            driver.save_screenshot(str(caminho_screenshot))

            if sucesso:
                emitir_log_selenium(f"Lote {item['lote_id']} gravado com SUCESSO.", "success", callback_log)
            else:
                emitir_log_selenium(f"Lote {item['lote_id']} submetido com ALERTAS.", "warn", callback_log)

            processados += 1

        emitir_log_selenium(f"Processamento finalizado com sucesso! Total: {processados} lotes", "success", callback_log)
        time.sleep(1)
        return processados

    except Exception as e:
        emitir_log_selenium(f"Falha crítica no Selenium: {e}", "error", callback_log)
        raise e
    finally:
        try:
            driver.quit()  # Fechamento automático ao encerrar
        except Exception:
            pass


if __name__ == "__main__":
    processar_datapool_selenium(delay_passo=0.1)