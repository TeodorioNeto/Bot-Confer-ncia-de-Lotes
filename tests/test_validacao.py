import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.validacao import valida_campos_obrigatorios, valida_estrutura


COLUNAS_VALIDAS = {
    "lote_id": ["L001", "L002"],
    "produto": ["TV", "Monitor"],
    "linha": ["A", "B"],
    "turno": ["Manha", "Tarde"],
    "status": ["OK", "NOK"],
    "responsavel": ["Ana", "Bruno"],
    "data": ["2026-07-14", "2026-07-14"],
    "observacao": ["", "Falha encontrada"],
}


class TestValidacaoRN01RN02(unittest.TestCase):
    def criar_planilha(self, dados):
        temp_dir = tempfile.TemporaryDirectory()
        caminho = Path(temp_dir.name) / "lotes.xlsx"
        pd.DataFrame(dados).to_excel(caminho, index=False)
        self.addCleanup(temp_dir.cleanup)
        return caminho

    def test_valida_estrutura_quando_colunas_obrigatorias_existem(self):
        caminho = self.criar_planilha(COLUNAS_VALIDAS)

        self.assertTrue(valida_estrutura(caminho))

    def test_reprova_estrutura_quando_coluna_obrigatoria_falta(self):
        dados = dict(COLUNAS_VALIDAS)
        dados.pop("status")
        caminho = self.criar_planilha(dados)

        self.assertFalse(valida_estrutura(caminho))

    def test_reprova_estrutura_quando_existe_coluna_extra(self):
        dados = dict(COLUNAS_VALIDAS)
        dados["coluna_extra"] = ["x", "y"]
        caminho = self.criar_planilha(dados)

        self.assertFalse(valida_estrutura(caminho))

    def test_reprova_estrutura_quando_colunas_estao_fora_de_ordem(self):
        dados = {
            "produto": ["TV"],
            "lote_id": ["L001"],
            "linha": ["A"],
            "turno": ["Manha"],
            "status": ["OK"],
            "responsavel": ["Ana"],
            "data": ["2026-07-14"],
            "observacao": [""],
        }
        caminho = self.criar_planilha(dados)

        self.assertFalse(valida_estrutura(caminho))

    def test_valida_campos_obrigatorios_quando_todos_estao_preenchidos(self):
        caminho = self.criar_planilha(COLUNAS_VALIDAS)

        self.assertTrue(valida_campos_obrigatorios(caminho))

    def test_reprova_campos_obrigatorios_quando_existe_vazio(self):
        dados = dict(COLUNAS_VALIDAS)
        dados["responsavel"] = ["Ana", ""]
        caminho = self.criar_planilha(dados)

        self.assertFalse(valida_campos_obrigatorios(caminho))

    def test_reprova_arquivo_que_nao_e_xlsx(self):
        with self.assertRaises(ValueError):
            valida_estrutura("lotes.csv")

    def test_valida_estrutura_com_linhas_descritivas_antes_do_cabecalho(self):
        temp_dir = tempfile.TemporaryDirectory()
        caminho = Path(temp_dir.name) / "lotes.xlsx"
        self.addCleanup(temp_dir.cleanup)

        linhas = [
            ["PLANILHA DE INSPECAO DE LOTES"],
            ["Arquivo gerado pelo sistema"],
            list(COLUNAS_VALIDAS.keys()),
            ["L001", "TV", "A", "Manha", "OK", "Ana", "2026-07-14", ""],
        ]
        pd.DataFrame(linhas).to_excel(caminho, index=False, header=False)

        self.assertTrue(valida_estrutura(caminho))

    def test_ignora_rodape_apos_linhas_de_registro(self):
        temp_dir = tempfile.TemporaryDirectory()
        caminho = Path(temp_dir.name) / "lotes.xlsx"
        self.addCleanup(temp_dir.cleanup)

        linhas = [
            list(COLUNAS_VALIDAS.keys()),
            ["L001", "TV", "A", "Manha", "OK", "Ana", "2026-07-14", ""],
            ["Total de registros: 1", "", "", "", "Resumo final", "", "", ""],
        ]
        pd.DataFrame(linhas).to_excel(caminho, index=False, header=False)

        self.assertTrue(valida_campos_obrigatorios(caminho))

if __name__ == "__main__":
    unittest.main()
