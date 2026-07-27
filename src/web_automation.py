import os

from dotenv import load_dotenv

from src.validacao import COLUNAS_ESTRUTURA


load_dotenv()


def montar_dados_lote(item):
    """Converte um item do DataPool para o formato usado pela automacao web."""
    return {campo: item.get_value(campo) for campo in COLUNAS_ESTRUTURA}


def preencher_formulario(dados_lote=None, credencial=None, driver=None):
    driver = (driver or os.getenv("WEB_AUTOMATION_DRIVER", "playwright")).lower()
    dados_lote = dados_lote or _dados_lote_demo()

    if driver == "selenium":
        from src.web_automation_selenium import preencher_formulario as preencher_selenium

        return preencher_selenium(dados_lote=dados_lote, credencial=credencial)

    if driver == "playwright":
        from src.web_automation_playwright import preencher_formulario as preencher_playwright

        return preencher_playwright(dados_lote=dados_lote, credencial=credencial)

    raise ValueError(
        "WEB_AUTOMATION_DRIVER deve ser 'playwright' ou 'selenium'. "
        f"Valor recebido: {driver}"
    )


def _dados_lote_demo():
    return {
        "lote_id": "LOTE-2026-0001",
        "produto": "Placa Mae V1",
        "linha": "A",
        "turno": "MANHA",
        "status": "APROVADO",
        "responsavel": "Usuario Teste",
        "data": "2026-07-27",
        "observacao": "",
    }


if __name__ == "__main__":
    preencher_formulario()
