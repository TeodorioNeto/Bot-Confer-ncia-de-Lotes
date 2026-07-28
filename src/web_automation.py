import os
from pathlib import Path

import openpyxl
from dotenv import load_dotenv

from bot import processar_item
from config import ARQUIVO_INSPECAO
from src.base_referencia import carregar_base_referencia
from src.validacao import COLUNAS_ESTRUTURA
from src.web_evidencias import obter_url_automacao


load_dotenv()


def montar_dados_lote(item):
    """Converte um item do DataPool para o formato usado pela automacao web."""
    return {campo: item.get_value(campo) for campo in COLUNAS_ESTRUTURA}


def preencher_formulario(
    dados_lote=None,
    credencial=None,
    driver=None,
    screenshot_path=None,
    analises=None,
    linha_planilha=None,
):
    driver = (driver or os.getenv("WEB_AUTOMATION_DRIVER", "playwright")).lower()
    if dados_lote is None:
        resultado_demo = carregar_primeiro_resultado_da_planilha()
        dados_lote = resultado_demo["dados_lote"]
        analises = resultado_demo["analises"]
        linha_planilha = resultado_demo.get("linha_planilha")

    if driver == "selenium":
        from src.web_automation_selenium import preencher_formulario as preencher_selenium

        return preencher_selenium(
            dados_lote=dados_lote,
            credencial=credencial,
            screenshot_path=screenshot_path,
            analises=analises,
            linha_planilha=linha_planilha,
        )

    if driver == "playwright":
        from src.web_automation_playwright import preencher_formulario as preencher_playwright

        return preencher_playwright(
            dados_lote=dados_lote,
            credencial=credencial,
            screenshot_path=screenshot_path,
            analises=analises,
            linha_planilha=linha_planilha,
        )

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


def carregar_primeiro_lote_da_planilha(caminho_planilha=None):
    """
    Carrega um lote da planilha de entrada usada pelo Dispatcher/BotCity.

    Essa funcao existe para que a execucao isolada de `python -m src.web_automation`
    use dados reais da planilha local, sem depender de um item do DataPool.
    """
    caminho = Path(caminho_planilha or ARQUIVO_INSPECAO)
    if not caminho.exists():
        return _dados_lote_demo()

    workbook = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    try:
        for ws in workbook.worksheets:
            linha_cabecalho = _encontrar_linha_cabecalho(ws)
            if linha_cabecalho is None:
                continue

            for linha in ws.iter_rows(
                min_row=linha_cabecalho + 1,
                max_col=len(COLUNAS_ESTRUTURA),
                values_only=True,
            ):
                if linha is None or all(valor is None for valor in linha):
                    break

                preenchidos = sum(
                    valor is not None and bool(str(valor).strip()) for valor in linha
                )
                if preenchidos >= 4:
                    return dict(zip(COLUNAS_ESTRUTURA, linha))
    finally:
        workbook.close()

    return _dados_lote_demo()


def carregar_primeiro_resultado_da_planilha(caminho_planilha=None):
    """Carrega da planilha o primeiro lote com ocorrencia; se nao houver, usa o primeiro lote."""
    caminho = Path(caminho_planilha or ARQUIVO_INSPECAO)
    if not caminho.exists():
        return {"dados_lote": _dados_lote_demo(), "analises": [], "linha_planilha": ""}

    base_referencia = carregar_base_referencia(caminho)
    primeiro_resultado = None

    workbook = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    try:
        for ws in workbook.worksheets:
            linha_cabecalho = _encontrar_linha_cabecalho(ws)
            if linha_cabecalho is None:
                continue

            for numero_linha in range(linha_cabecalho + 1, ws.max_row + 1):
                valores_linha = [
                    ws.cell(numero_linha, coluna).value
                    for coluna in range(1, len(COLUNAS_ESTRUTURA) + 1)
                ]
                if valores_linha is None or all(valor is None for valor in valores_linha):
                    break

                preenchidos = sum(
                    valor is not None and bool(str(valor).strip())
                    for valor in valores_linha
                )
                if preenchidos < 4:
                    continue

                dados_lote = dict(zip(COLUNAS_ESTRUTURA, valores_linha))
                resultado = processar_item(ItemPlanilhaWeb(dados_lote), base_referencia)
                retorno = {
                    "dados_lote": dados_lote,
                    "analises": resultado["analises"],
                    "linha_planilha": numero_linha,
                }

                if primeiro_resultado is None:
                    primeiro_resultado = retorno
                if resultado["analises"]:
                    return retorno
    finally:
        workbook.close()

    return primeiro_resultado or {
        "dados_lote": _dados_lote_demo(),
        "analises": [],
        "linha_planilha": "",
    }


def _encontrar_linha_cabecalho(ws):
    for numero_linha in range(1, ws.max_row + 1):
        valores = [
            ws.cell(numero_linha, coluna).value
            for coluna in range(1, len(COLUNAS_ESTRUTURA) + 1)
        ]
        if valores == COLUNAS_ESTRUTURA:
            return numero_linha
    return None


class ItemPlanilhaWeb:
    def __init__(self, valores):
        self.valores = valores

    def get_value(self, chave):
        return self.valores.get(chave)


if __name__ == "__main__":
    preencher_formulario()
