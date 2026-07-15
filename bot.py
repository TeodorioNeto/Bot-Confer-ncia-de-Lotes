"""
bot.py - Entry point do Bot de Conferência de Lotes.

Executa a validação de registros de inspeção aplicando as regras de
negócio RN01-RN07, usando a planilha oficial de inspeção como entrada
e a base de referência para checagem de lotes.
"""

import logging
import re
from pathlib import Path

import openpyxl

from src.base_referencia import carregar_base_referencia, verificar_lote_na_base
from src.validacao import normalizar_status, valida_status
from src.config import ARQUIVO_INSPECAO, ABA_INSPECAO

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

LOTE_ID_PATTERN = re.compile(r"^LG-\d{4}-\d{5}$")


def processar_inspecao(caminho_arquivo=None):
    """
    Processa a planilha de inspeção, aplicando as regras de negócio
    disponíveis, e retorna a lista de divergências encontradas.
    """
    caminho_arquivo = Path(caminho_arquivo or ARQUIVO_INSPECAO)

    base_referencia = carregar_base_referencia()

    wb = openpyxl.load_workbook(caminho_arquivo, read_only=True, data_only=True)
    ws = wb[ABA_INSPECAO]

    linhas = ws.iter_rows(values_only=True)
    next(linhas)  # linha de título
    next(linhas)  # linha de metadados (arquivo, sistema, registros)
    cabecalho = next(linhas)
    idx_lote = cabecalho.index("lote_id")
    idx_status = cabecalho.index("status")

    divergencias = []

    for numero_linha, linha in enumerate(linhas, start=4):
        # Linha totalmente vazia = fim real dos dados (resto é formatação sobrando)
        if linha is None or all(valor is None for valor in linha):
            break

        lote_id = linha[idx_lote] if idx_lote < len(linha) else None
        status = linha[idx_status] if idx_status < len(linha) else None

        # Ignora linhas de rodapé/legenda/exemplo (não são registros reais)
        if lote_id and not LOTE_ID_PATTERN.match(str(lote_id).strip()):
            continue

        # RN02: lote_id obrigatório
        if not lote_id:
            divergencias.append(
                {"linha": numero_linha, "lote_id": None, "regra": "RN02", "problema": "lote_id vazio"}
            )
            continue

        # RN03: lote precisa existir na base de referência
        if not verificar_lote_na_base(lote_id, base_referencia):
            divergencias.append(
                {
                    "linha": numero_linha,
                    "lote_id": lote_id,
                    "regra": "RN03",
                    "problema": "lote_id não existe na base de referência",
                }
            )

        # RN04/RN05: status precisa ser válido (após normalização de sinônimos)
        try:
            status_ok = valida_status(status)
            if not status_ok:
                divergencias.append(
                    {
                        "linha": numero_linha,
                        "lote_id": lote_id,
                        "regra": "RN04/RN05",
                        "problema": f"status '{status}' não reconhecível (normalizado: '{normalizar_status(status)}')",
                    }
                )
        except ValueError:
            divergencias.append(
                {"linha": numero_linha, "lote_id": lote_id, "regra": "RN02", "problema": "status vazio"}
            )

      
    wb.close()
    logging.info("Processamento concluído: %d divergência(s) encontrada(s).", len(divergencias))
    return divergencias


if __name__ == "__main__":
    resultado = processar_inspecao()
    for d in resultado:
        print(d)