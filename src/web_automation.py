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


def preencher_formulario():
    caminho_doc = Path("doc.html").resolve()
    url = caminho_doc.as_uri()

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

        campo_lote.send_keys("LOTE-2026-0001")
        Select(seletor_produto).select_by_index(1)
        status_concluido.click()
        botao_processar.click()

        wait.until(EC.visibility_of_element_located((By.ID, "alertSuccess")))
    finally:
        driver.quit()


if __name__ == "__main__":
    preencher_formulario()
