import unittest

import pytest

from gerar_relatorio import normalizar_status, validar_registro


@pytest.mark.unit
class TestRegrasRelatorioAula23(unittest.TestCase):
    def setUp(self):
        self.base_referencia = {"LG-2026-00001", "LG-2026-00002"}

    def registro_valido(self, **sobrescritas):
        registro = {
            "aba_origem": "Insp_01_08_2026",
            "linha_planilha": 4,
            "data_referencia": "2026-08-01",
            "lote_id": "LG-2026-00001",
            "produto": "AC12-SPLIT",
            "linha": "L1",
            "turno": "MANHA",
            "status": "APROVADO",
            "responsavel": "Analista Teste",
            "data": "01/08/2026",
            "observacao": "Inspecao sem divergencia",
        }
        registro.update(sobrescritas)
        return registro

    def test_normalizacao_de_status_com_subtest(self):
        cenarios = {
            "OK": "APROVADO",
            "NOK": "REPROVADO",
            " aprovado ": "APROVADO",
            "": None,
            None: None,
        }

        for entrada, esperado in cenarios.items():
            with self.subTest(status=entrada):
                self.assertEqual(normalizar_status(entrada), esperado)

    @pytest.mark.regression
    def test_validar_registro_com_subtest_para_regras_de_negocio(self):
        cenarios = [
            (
                "status_ambiguo",
                {"status": "APROVADO PARCIAL"},
                1,
                "Ambíguo",
                "RN09",
            ),
            (
                "reprovado_sem_observacao",
                {"status": "NOK", "observacao": ""},
                1,
                "Divergência",
                "RN10",
            ),
            (
                "duplicado_no_dia",
                {},
                2,
                "Divergência",
                "RN11",
            ),
            (
                "data_invalida",
                {"data": "2026-08-01"},
                1,
                "Erro de Entrada",
                "RN12",
            ),
        ]

        for nome, sobrescritas, ocorrencia, classificacao, regra in cenarios:
            with self.subTest(cenario=nome):
                resultado = validar_registro(
                    self.registro_valido(**sobrescritas),
                    ocorrencia,
                    self.base_referencia,
                )

                self.assertEqual(resultado.classificacao, classificacao)
                self.assertEqual(resultado.regra_violada, regra)
