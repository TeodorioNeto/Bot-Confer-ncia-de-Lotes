"""
dispatcher.py - valida a planilha e publica os lotes no DataPool.
"""

import os
import re
import sys

import openpyxl
from botcity.maestro import BotMaestroSDK, DataPoolEntry
from dotenv import load_dotenv

from config import ARQUIVO_INSPECAO, DATAPOOL_LABEL
from src.config import ABA_INSPECAO
from src.logger import setup_logger
from src.validacao import valida_estrutura


logger = setup_logger(__name__)

LOTE_ID_PATTERN = re.compile(r"^LG-\d{4}-\d{5}$")


def conectar_maestro():
    """Conecta no Maestro usando argumentos do Runner ou credenciais do .env."""
    maestro = BotMaestroSDK.from_sys_args()

    if len(sys.argv) < 8:
        logger.info("Execucao local: carregando credenciais do arquivo .env.")
        load_dotenv()
        maestro.login(
            server=os.getenv("MAESTRO_SERVER"),
            login=os.getenv("MAESTRO_LOGIN"),
            key=os.getenv("MAESTRO_KEY"),
        )
    else:
        logger.info("Execucao via Runner: credenciais injetadas automaticamente.")

    return maestro


def popular_fila(maestro=None):
    """Valida a planilha e publica os registros quando a fila esta vazia."""
    maestro = maestro or conectar_maestro()
    datapool = maestro.get_datapool(DATAPOOL_LABEL)

    if datapool.has_next():
        logger.info(
            "Fila %s ja possui itens pendentes; nenhuma linha sera republicada.",
            DATAPOOL_LABEL,
        )
        return {"enviados": 0, "ignorados": 0, "fila_ja_populada": True}

    if not valida_estrutura(ARQUIVO_INSPECAO):
        raise ValueError("Estrutura da planilha invalida (RN01).")

    wb = openpyxl.load_workbook(ARQUIVO_INSPECAO, read_only=True, data_only=True)
    try:
        ws = wb[ABA_INSPECAO]
        linhas = ws.iter_rows(values_only=True)
        next(linhas)  # titulo
        next(linhas)  # metadados
        cabecalho = next(linhas)
        enviados = ignorados = 0

        for numero_linha, linha in enumerate(linhas, start=4):
            if linha is None or all(valor is None for valor in linha):
                break

            item = dict(zip(cabecalho, linha))
            item["screenshot"] = ""
            item["linha_planilha"] = numero_linha

            lote_id_bruto = item.get("lote_id")
            if lote_id_bruto and not LOTE_ID_PATTERN.match(str(lote_id_bruto).strip()):
                ignorados += 1
                continue

            datapool.create_entry(DataPoolEntry(values=item))
            enviados += 1
    finally:
        wb.close()

    logger.info(
        "Fila %s populada com %d itens (%d linhas de rodape/legenda ignoradas).",
        DATAPOOL_LABEL,
        enviados,
        ignorados,
    )
    return {
        "enviados": enviados,
        "ignorados": ignorados,
        "fila_ja_populada": False,
    }


if __name__ == "__main__":
    popular_fila()
