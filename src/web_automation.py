import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

def preencher_formulario():
    url = os.getenv("URL_TESTE_LOCAL")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)

        # Preenchimento inicial usando seletores diretos
        page.fill("#nome", "Usuário Teste")
        page.fill("#email", "teste@email.com")
        page.select_option("#categoria", value="opcao_1")
        page.click("#btn_enviar")

        page.wait_for_timeout(3000)
        browser.close()

if __name__ == "__main__":
    preencher_formulario()