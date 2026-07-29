import openpyxl

import dispatcher


class FakeDataPool:
    def __init__(self, tem_pendente=False):
        self.tem_pendente = tem_pendente
        self.entries = []

    def has_next(self):
        return self.tem_pendente

    def create_entry(self, entry):
        self.entries.append(entry)


class FakeMaestro:
    def __init__(self, datapool):
        self.datapool = datapool

    def get_datapool(self, label):
        self.label = label
        return self.datapool


class FakeDataPoolEntry:
    def __init__(self, values):
        self.values = values


def criar_planilha_inspecao(caminho):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inspecao_14_06_2026"
    ws.append(["PLANILHA DE INSPECAO"])
    ws.append(["Arquivo", "Sistema", "Registros"])
    ws.append(
        [
            "lote_id",
            "produto",
            "linha",
            "turno",
            "status",
            "responsavel",
            "data",
            "observacao",
        ]
    )
    ws.append(["LG-2026-00101", "TV", "A", "MANHA", "APROVADO", "Ana", "14/06/2026", ""])
    ws.append(["Legenda", None, None, None, None, None, None, None])
    wb.save(caminho)


def test_popular_fila_publica_lotes_validos_e_ignora_rodape(monkeypatch, tmp_path):
    caminho = tmp_path / "inspecao_lotes_dia.xlsx"
    criar_planilha_inspecao(caminho)
    datapool = FakeDataPool()

    monkeypatch.setattr(dispatcher, "ARQUIVO_INSPECAO", caminho)
    monkeypatch.setattr(dispatcher, "DataPoolEntry", FakeDataPoolEntry)
    monkeypatch.setattr(dispatcher, "valida_estrutura", lambda _: True)

    resultado = dispatcher.popular_fila(FakeMaestro(datapool))

    assert resultado == {
        "enviados": 1,
        "ignorados": 1,
        "fila_ja_populada": False,
    }
    assert len(datapool.entries) == 1
    assert datapool.entries[0].values["lote_id"] == "LG-2026-00101"
    assert datapool.entries[0].values["linha_planilha"] == 4
    assert datapool.entries[0].values["screenshot"] == ""


def test_popular_fila_nao_republica_quando_ja_tem_item_pendente(monkeypatch, tmp_path):
    caminho = tmp_path / "inspecao_lotes_dia.xlsx"
    criar_planilha_inspecao(caminho)
    datapool = FakeDataPool(tem_pendente=True)

    monkeypatch.setattr(dispatcher, "ARQUIVO_INSPECAO", caminho)

    resultado = dispatcher.popular_fila(FakeMaestro(datapool))

    assert resultado == {
        "enviados": 0,
        "ignorados": 0,
        "fila_ja_populada": True,
    }
    assert datapool.entries == []
