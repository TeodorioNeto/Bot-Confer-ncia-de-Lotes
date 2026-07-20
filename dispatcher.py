"""
dispatcher.py - le a planilha de inspecao e envia cada linha como item
pro DataPool. 
"""
import logging
import re
from botcity.maestro import BotMaestroSDK, DataPoolEntry
from config import ARQUIVO_INSPECAO, DATAPOOL_LABEL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

LOTE_ID_PATTERN = re.compile(r"^LG-\d{4}-\d{5}$")


def popular_fila():
    import openpyxl

    maestro = BotMaestroSDK.from_sys_args()
    datapool = maestro.get_datapool(DATAPOOL_LABEL)

    wb = openpyxl.load_workbook(ARQUIVO_INSPECAO, read_only=True, data_only=True)
    ws = wb["Inspecao_14_06_2026"]

    linhas = ws.iter_rows(values_only=True)
    next(linhas)  # titulo
    next(linhas)  # metadados
    cabecalho = next(linhas)

    enviados = ignorados = 0

    for linha in linhas:
        # Linha totalmente vazia = fim real dos dados
        if linha is None or all(valor is None for valor in linha):
            break

        item = dict(zip(cabecalho, linha))
        lote_id_bruto = item.get("lote_id")

        # Ignora linhas de rodape/legenda/exemplo (nao sao registros reais)
        if lote_id_bruto and not LOTE_ID_PATTERN.match(str(lote_id_bruto).strip()):
            ignorados += 1
            continue

        datapool.create_entry(DataPoolEntry(values=item))
        enviados += 1

    wb.close()
    logger.info(
        "Fila %s populada com %d itens (%d linhas de rodape/legenda ignoradas).",
        DATAPOOL_LABEL,
        enviados,
        ignorados,
    )


if __name__ == "__main__":
    popular_fila()