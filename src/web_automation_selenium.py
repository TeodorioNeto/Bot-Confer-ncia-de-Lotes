import logging
import os

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from src.validacao import normalizar_status
from src.web_evidencias import montar_caminho_screenshot, obter_url_automacao


load_dotenv()
logger = logging.getLogger(__name__)


def criar_driver():
    """Inicializa o navegador Chrome usando Selenium WebDriver."""
    options = webdriver.ChromeOptions()

    if os.getenv("SELENIUM_HEADLESS", "false").lower() == "true":
        options.add_argument("--headless=new")

    options.add_argument("--window-size=1280,720")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def preencher_formulario(
    dados_lote=None,
    credencial=None,
    screenshot_path=None,
    analises=None,
    linha_planilha=None,
):
    """Executa o preenchimento da tela simulada de inspecao usando Selenium."""
    url = obter_url_automacao()
    dados_lote = dados_lote or {}
    caminho_screenshot = montar_caminho_screenshot(
        dados_lote,
        "selenium",
        screenshot_path=screenshot_path,
    )

    driver = criar_driver()
    wait = WebDriverWait(driver, 10)

    try:
        logger.info(
            "Iniciando automacao Selenium para lote %s.",
            dados_lote.get("lote_id"),
        )
        driver.get(url)

        _preencher(wait, "lote_id", dados_lote.get("lote_id"))
        _preencher(wait, "produto", dados_lote.get("produto"))
        _preencher(wait, "linha", dados_lote.get("linha"))
        _preencher(wait, "turno", dados_lote.get("turno"))
        Select(wait.until(EC.element_to_be_clickable((By.ID, "status")))).select_by_value(
            _status_formulario(dados_lote.get("status"))
        )
        _preencher(wait, "responsavel", dados_lote.get("responsavel"))
        _preencher(wait, "data", dados_lote.get("data"))
        _preencher(wait, "observacao", dados_lote.get("observacao"))

        wait.until(EC.element_to_be_clickable((By.ID, "btn-processar"))).click()
        wait.until(EC.visibility_of_element_located((By.ID, "resultado")))
        _registrar_analises(wait, dados_lote, analises or [], linha_planilha)
        driver.save_screenshot(str(caminho_screenshot))
        logger.info("Screenshot Selenium gerado em %s.", caminho_screenshot)
        return {
            "driver": "selenium",
            "screenshot": str(caminho_screenshot),
            "analises_registradas": len(analises or []),
        }
    finally:
        driver.quit()


def _preencher(wait, campo_id, valor):
    campo = wait.until(EC.element_to_be_clickable((By.ID, campo_id)))
    campo.clear()
    campo.send_keys(str(valor or ""))


def _status_formulario(status):
    status_normalizado = normalizar_status(status)
    if status_normalizado in {"APROVADO", "REPROVADO", "PENDENTE"}:
        return status_normalizado
    return "PENDENTE"


def _registrar_analises(wait, dados_lote, analises, linha_planilha):
    for analise in analises:
        _preencher(wait, "linha_planilha", linha_planilha)
        _preencher(wait, "analise_lote_id", dados_lote.get("lote_id") or "(vazio)")
        _preencher(wait, "regra", analise.get("regra"))
        _preencher(wait, "problema", analise.get("problema"))
        _preencher(wait, "acao_recomendada", analise.get("acao"))
        revisao = (
            "Sim (aviso)"
            if analise.get("categoria") == "aviso"
            else "Sim (divergencia)"
        )
        Select(wait.until(EC.element_to_be_clickable((By.ID, "revisao")))).select_by_value(
            revisao
        )
        wait.until(EC.element_to_be_clickable((By.ID, "btn-adicionar-analise"))).click()


if __name__ == "__main__":
    preencher_formulario()
