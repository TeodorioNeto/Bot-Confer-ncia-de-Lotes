import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.validacao import valida_observacao_reprovado


class TestValidacaoRN07(unittest.TestCase):
    def criar_planilha(self, linhas, cabecalho=None):
        temp_dir = tempfile.TemporaryDirectory()
        caminho = Path(temp_dir.name) / "lotes.xlsx"
        self.addCleanup(temp_dir.cleanup)

        cabecalho = cabecalho or ["lote_id", "status", "observacao"]
        pd.DataFrame(linhas, columns=cabecalho).to_excel(caminho, index=False)
        return caminho

    def test_valida_reprovado_com_observacao_preenchida(self):
        caminho = self.criar_planilha(
            [["LG-2026-00101", "REPROVADO", "Defeito na tela"]]
        )

        self.assertTrue(valida_observacao_reprovado(caminho))

    def test_reprova_reprovado_sem_observacao(self):
        caminho = self.criar_planilha([["LG-2026-00102", "REPROVADO", ""]])

        self.assertFalse(valida_observacao_reprovado(caminho))

    def test_reprova_nok_sem_observacao(self):
        caminho = self.criar_planilha([["LG-2026-00103", "NOK", ""]])

        self.assertFalse(valida_observacao_reprovado(caminho))

    def test_nao_exige_observacao_para_aprovado(self):
        caminho = self.criar_planilha([["LG-2026-00104", "APROVADO", ""]])

        self.assertTrue(valida_observacao_reprovado(caminho))

    def test_reprova_quando_coluna_observacao_falta(self):
        caminho = self.criar_planilha(
            [["LG-2026-00105", "REPROVADO"]],
            cabecalho=["lote_id", "status"],
        )

        self.assertFalse(valida_observacao_reprovado(caminho))

    def test_valida_planilha_com_linhas_descritivas_antes_do_cabecalho(self):
        temp_dir = tempfile.TemporaryDirectory()
        caminho = Path(temp_dir.name) / "lotes.xlsx"
        self.addCleanup(temp_dir.cleanup)

        linhas = [
            ["PLANILHA DE INSPECAO DE LOTES", "", ""],
            ["Arquivo gerado pelo sistema", "", ""],
            ["lote_id", "status", "observacao"],
            ["LG-2026-00106", "REPROVADO", "Falha no painel"],
        ]
        pd.DataFrame(linhas).to_excel(caminho, index=False, header=False)

        self.assertTrue(valida_observacao_reprovado(caminho))


if __name__ == "__main__":
    unittest.main()
