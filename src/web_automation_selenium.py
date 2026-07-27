import os
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from src.validacao import normalizar_status


load_dotenv()


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


def preencher_formulario(dados_lote=None, credencial=None):
    """Executa o preenchimento do formulario local usando Selenium."""
    caminho_doc = Path("doc.html").resolve()
    url = caminho_doc.as_uri()
    dados_lote = dados_lote or {}

    driver = criar_driver()
    wait = WebDriverWait(driver, 10)

    try:
        driver.get(url)

        campo_lote = wait.until(EC.element_to_be_clickable((By.ID, "lote")))
        seletor_produto = wait.until(EC.element_to_be_clickable((By.ID, "produto")))
        status_concluido = wait.until(
            EC.element_to_be_clickable((By.XPATH, "(//input[@name='status'])[3]"))
        )
        botao_processar = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )

        campo_lote.send_keys(str(dados_lote.get("lote_id") or ""))
        _selecionar_produto(seletor_produto, dados_lote.get("produto"))
        status_radio = _status_formulario(dados_lote.get("status"))
        if status_radio != "Concluído":
            status_concluido = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, f"input[name='status'][value='{status_radio}']")
                )
            )
        status_concluido.click()
        botao_processar.click()

        wait.until(EC.visibility_of_element_located((By.ID, "alertSuccess")))
    finally:
        driver.quit()


def _selecionar_produto(elemento_select, produto):
    select = Select(elemento_select)
    opcoes = [opcao.get_attribute("value") for opcao in select.options]
    produto = str(produto or "").strip()
    if produto in opcoes:
        select.select_by_value(produto)
    else:
        select.select_by_index(1)


def _status_formulario(status):
    status_normalizado = normalizar_status(status)
    if status_normalizado == "PENDENTE":
        return "Pendente"
    if status_normalizado == "APROVADO":
        return "Concluído"
    return "Em Processamento"


if __name__ == "__main__":
    preencher_formulario()
