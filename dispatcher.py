import sys
import os
import logging
import re
from dotenv import load_dotenv
from botcity.maestro import BotMaestroSDK, DataPoolEntry
from config import ARQUIVO_INSPECAO, DATAPOOL_LABEL
from src.validacao import valida_estrutura

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

LOTE_ID_PATTERN = re.compile(r"^LG-\d{4}-\d{5}$")


def conectar_maestro():
    """
    Lógica inteligente de conexão: Local x Runner
    """
    maestro = BotMaestroSDK.from_sys_args()
    
    # O Runner injeta pelo menos 8 argumentos (-server, -login, -key, -task_id).
    # Se tiver menos que isso (geralmente só 1), estamos rodando manualmente no VS Code.
    if len(sys.argv) < 2:
        logger.info("Execução Local: Carregando credenciais do arquivo .env...")
        load_dotenv()
        maestro.login(
            server=os.getenv("MAESTRO_SERVER"),
            login=os.getenv("MAESTRO_LOGIN"),
            key=os.getenv("MAESTRO_KEY")
        )
    else:
        logger.info("Execução via Runner: Credenciais injetadas automaticamente.")
        
    return maestro


def popular_fila(maestro=None):
    """Valida a planilha e publica os registros quando a fila está vazia."""
    import openpyxl

    maestro = maestro or conectar_maestro()
    datapool = maestro.get_datapool(DATAPOOL_LABEL)
    if datapool.has_next():
        logger.info(
            "Fila %s já possui itens pendentes; nenhuma linha será republicada.",
            DATAPOOL_LABEL,
        )
        return {"enviados": 0, "ignorados": 0, "fila_ja_populada": True}

    if not valida_estrutura(ARQUIVO_INSPECAO):
        raise ValueError("Estrutura da planilha inválida (RN01).")

    wb = openpyxl.load_workbook(ARQUIVO_INSPECAO, read_only=True, data_only=True)
    try:
        ws = wb["Inspecao_14_06_2026"]
        linhas = ws.iter_rows(values_only=True)
        next(linhas)  # título
        next(linhas)  # metadados
        cabecalho = next(linhas)
        enviados = ignorados = 0

        for linha in linhas:
            if linha is None or all(valor is None for valor in linha):
                break

            item = dict(zip(cabecalho, linha))
            lote_id_bruto = item.get("lote_id")
            if lote_id_bruto and not LOTE_ID_PATTERN.match(
                str(lote_id_bruto).strip()
            ):
                ignorados += 1
                continue

            datapool.create_entry(DataPoolEntry(values=item))
            enviados += 1
    finally:
        wb.close()

    logger.info(
        "Fila %s populada com %d itens (%d linhas de rodapé/legenda ignoradas).",
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
