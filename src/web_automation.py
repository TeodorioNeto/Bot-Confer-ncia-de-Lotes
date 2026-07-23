import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

def preencher_formulario():
    # Caminho para o arquivo local doc.html
    caminho_doc = os.path.abspath("doc.html")
    url = f"file://{caminho_doc}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)

        # Usando locators semânticos
        page.get_by_label("Nome").fill("Usuário Teste")
        page.get_by_label("E-mail").fill("teste@email.com")
        page.get_by_role("button", name="Enviar").click()

        page.wait_for_timeout(3000)
        browser.close()

if __name__ == "__main__":
    preencher_formulario()