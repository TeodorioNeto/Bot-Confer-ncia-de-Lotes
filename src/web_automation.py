import os

from dotenv import load_dotenv


load_dotenv()


def preencher_formulario():
    driver = os.getenv("WEB_AUTOMATION_DRIVER", "playwright").lower()

    if driver == "selenium":
        from src.web_automation_selenium import preencher_formulario as preencher_selenium

        return preencher_selenium()

    if driver == "playwright":
        from src.web_automation_playwright import preencher_formulario as preencher_playwright

        return preencher_playwright()

    raise ValueError(
        "WEB_AUTOMATION_DRIVER deve ser 'playwright' ou 'selenium'. "
        f"Valor recebido: {driver}"
    )


if __name__ == "__main__":
    preencher_formulario()
