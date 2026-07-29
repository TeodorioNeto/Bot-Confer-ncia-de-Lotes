"""
testar_local.py - simula o fluxo planilha -> fila -> performer
inteiramente em memoria, sem precisar do Maestro. 
"""
import re
import openpyxl
from bot import processar_item
from src.base_referencia import carregar_base_referencia
from src.config import ARQUIVO_INSPECAO, ABA_INSPECAO

LOTE_ID_PATTERN = re.compile(r"^LG-\d{4}-\d{5}$")


class FakeDataPoolEntry:
    """Substitui DataPoolEntry nos testes, sem precisar do Maestro."""

    def __init__(self, valores):
        self._valores = valores

    def get_value(self, chave):
        return self._valores.get(chave)


def simular():
    base_referencia = carregar_base_referencia()

    wb = openpyxl.load_workbook(ARQUIVO_INSPECAO, read_only=True, data_only=True)
    ws = wb[ABA_INSPECAO]
    linhas = ws.iter_rows(values_only=True)
    next(linhas)  # titulo
    next(linhas)  # metadados
    cabecalho = next(linhas)

    total = processados = falhados = ignorados = 0

    for linha in linhas:
        if linha is None or all(v is None for v in linha):
            break

        item_dict = dict(zip(cabecalho, linha))
        lote_id_bruto = item_dict.get("lote_id")

        # Ignora linhas de rodape/legenda/exemplo (nao sao registros reais)
        if lote_id_bruto and not LOTE_ID_PATTERN.match(str(lote_id_bruto).strip()):
            ignorados += 1
            continue

        item = FakeDataPoolEntry(item_dict)

        total += 1
        try:
            resultado = processar_item(item, base_referencia)
            processados += 1
            if resultado["divergencias"]:
                print(f"[DIVERGÊNCIA] {resultado['lote_id']}: {resultado['divergencias']}")
        except ValueError as erro:
            falhados += 1
            print(f"[ITEM COM ERRO] {erro}")

    wb.close()
    print(
        f"\nResumo: {total} itens, {processados} processados, "
        f"{falhados} com erro, {ignorados} linhas de rodapé/legenda ignoradas."
    )


if __name__ == "__main__":
    simular()
