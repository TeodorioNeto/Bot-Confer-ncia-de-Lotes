"""
src/web_automation_selenium.py
Orquestrador Selenium para a tela web simulada de inspecao de lotes.
"""

import os

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from config import ARQUIVO_INSPECAO
from src.base_referencia import carregar_base_referencia
from src.logger import setup_logger
from src.pages.form_page import FormPageSelenium
from src.pages.login_page import LoginPageSelenium
from src.web_automation import analisar_dados_lote
from src.web_automation_playwright import carregar_datapool_tratado
from src.web_evidencias import montar_caminho_screenshot, obter_url_automacao

load_dotenv()

logger = setup_logger("SeleniumEngine")


def emitir_log_selenium(mensagem, tipo="info", callback_log=None):
    if tipo == "warn":
        logger.warning(mensagem)
    elif tipo == "error":
        logger.error(mensagem)
    else:
        logger.info(mensagem)

    if callback_log:
        try:
            callback_log(mensagem, tipo)
        except Exception:
            pass


def criar_driver():
    """Inicializa o navegador Microsoft Edge usando Selenium WebDriver."""
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


def processar_item_selenium(dados_lote, delay_passo=0, callback_log=None, theme="dark"):
    """Processa diretamente um item do DataPool na tela web simulada."""
    resultado = processar_lotes_selenium(
        [dados_lote],
        delay_passo=delay_passo,
        callback_log=callback_log,
        theme=theme,
        return_evidencias=True,
    )
    return resultado["evidencias"][0] if resultado["evidencias"] else None


def processar_datapool_selenium(
    delay_passo=0,
    callback_log=None,
    theme="dark",
    return_evidencias=False,
):
    """Processa em lote a planilha local, usado por demo e execucao isolada."""
    lotes = carregar_datapool_tratado()

    if not lotes:
        emitir_log_selenium("DataPool esta vazio ou a planilha nao foi localizada.", "warn", callback_log)
        return {"total": 0, "evidencias": []} if return_evidencias else 0

    return processar_lotes_selenium(
        lotes,
        delay_passo=delay_passo,
        callback_log=callback_log,
        theme=theme,
        return_evidencias=return_evidencias,
    )


def processar_lotes_selenium(
    lotes,
    delay_passo=0,
    callback_log=None,
    theme="dark",
    return_evidencias=False,
):
    url = obter_url_automacao()
    base_referencia = carregar_base_referencia(ARQUIVO_INSPECAO)

    emitir_log_selenium(
        f"Iniciando execucao Selenium | Total de lotes: {len(lotes)} | Tema: {theme.upper()}",
        "info",
        callback_log,
    )

    driver = criar_driver()
    wait = WebDriverWait(driver, 10)

    try:
        emitir_log_selenium(f"Acessando a URL do formulario: {url}", "info", callback_log)
        driver.get(url)

        login_page = LoginPageSelenium(driver, wait, delay_passo=delay_passo)
        form_page = FormPageSelenium(driver, wait, delay_passo=delay_passo)
        form_page.aplicar_tema(theme)

        emitir_log_selenium("Realizando autenticacao na plataforma...", "info", callback_log)
        login_page.fazer_login()

        processados = 0
        evidencias = []
        for idx, item in enumerate(lotes, start=1):
            msg_lote = (
                f"[{idx:02d}/{len(lotes):02d}] Lote: {item['lote_id']} | "
                f"Produto: {item['produto']} | Status: {item['status']}"
            )
            emitir_log_selenium(msg_lote, "info", callback_log)

            form_page.resetar_formulario()
            form_page.preencher_lote(item)
            sucesso = form_page.submeter_e_aguardar()
            resultado_item = analisar_dados_lote(item, base_referencia)
            form_page.registrar_analises(
                resultado_item["analises"],
                item,
                resultado_item.get("linha_planilha"),
            )

            form_page.preparar_evidencia_visual()
            caminho_screenshot = montar_caminho_screenshot(item, "selenium")
            driver.save_screenshot(str(caminho_screenshot))
            item["screenshot"] = str(caminho_screenshot)
            evidencias.append(
                {
                    "lote_id": item.get("lote_id"),
                    "screenshot": str(caminho_screenshot),
                    "driver": "selenium",
                    "linha_planilha": resultado_item.get("linha_planilha"),
                    "analises": resultado_item["analises"],
                    "divergencias": resultado_item["divergencias"],
                    "avisos": resultado_item["avisos"],
                }
            )

            if sucesso:
                emitir_log_selenium(f"Lote {item['lote_id']} gravado com SUCESSO.", "success", callback_log)
            else:
                emitir_log_selenium(f"Lote {item['lote_id']} submetido com ALERTAS.", "warn", callback_log)

            processados += 1

        emitir_log_selenium(
            f"Processamento finalizado com sucesso! Total: {processados} lotes",
            "success",
            callback_log,
        )
        if return_evidencias:
            return {"total": processados, "evidencias": evidencias}
        return processados

    except Exception as erro:
        emitir_log_selenium(f"Falha critica no Selenium: {erro}", "error", callback_log)
        raise
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    processar_datapool_selenium()
