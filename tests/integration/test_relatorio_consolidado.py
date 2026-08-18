from pathlib import Path

import openpyxl
import pytest

from gerar_relatorio import (
    ARQUIVO_ENTRADA,
    RegistroValidado,
    gerar_relatorio_excel,
    gerar_resumo_executivo,
    resolver_caminho_entrada,
)
from operational_indicators import consolidar_indicadores


ABAS_ESSENCIAIS = {
    "Resumo",
    "Todos",
    "Válidos",
    "Divergências",
    "Ambíguos",
    "Erros de Entrada",
    "Ranking de Regras",
    "Dicionário",
}


def registro(classificacao, regra="-", linha_planilha=4):
    return RegistroValidado(
        aba_origem="Insp_01_08_2026",
        linha_planilha=linha_planilha,
        data_referencia="2026-08-01",
        lote_id=f"LG-2026-{linha_planilha:05d}",
        produto="AC12-SPLIT",
        linha="L1",
        turno="MANHA",
        status_original="APROVADO",
        status_normalizado="APROVADO",
        responsavel="Analista Teste",
        data_inspecao="01/08/2026",
        observacao="Sem divergencia",
        classificacao=classificacao,
        regra_violada=regra,
        motivo="Cenario controlado",
    )


@pytest.mark.integration
def test_relatorio_consolidado_cria_8_abas_essenciais_e_resumo_sincronizado(tmp_path):
    registros = [
        registro("Válido", linha_planilha=4),
        registro("Divergência", "RN05", linha_planilha=5),
        registro("Divergência", "RN05", linha_planilha=6),
        registro("Ambíguo", "RN09", linha_planilha=7),
        registro("Erro de Entrada", "RN12", linha_planilha=8),
    ]
    indicadores = consolidar_indicadores(registros)
    caminho_excel = tmp_path / "relatorio_conferencia_lotes.xlsx"
    caminho_md = tmp_path / "resumo_executivo.md"

    gerar_relatorio_excel(registros, caminho_excel, indicadores)
    gerar_resumo_executivo(indicadores, caminho_md)

    wb = openpyxl.load_workbook(caminho_excel, data_only=True)
    try:
        assert set(wb.sheetnames) == ABAS_ESSENCIAIS
        assert wb["Resumo"]["B2"].value == indicadores.total_registros
        assert wb["Resumo"]["B7"].value.startswith("RN05")
        assert wb["Ranking de Regras"]["A2"].value == "RN05"
        assert wb["Ranking de Regras"]["C2"].value == 2
        assert wb["Dicionário"]["A2"].value == "Válido"
        assert len(wb["Resumo"]._charts) == 2
    finally:
        wb.close()

    resumo = caminho_md.read_text(encoding="utf-8")
    assert f"Foram processados {indicadores.total_registros} registros" in resumo
    assert "RN05" in resumo
    assert f"{indicadores.ganho_estimado_minutos:.0f} minutos" in resumo


@pytest.mark.integration
def test_resolver_entrada_padrao_aceita_arquivo_legado_na_raiz(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    caminho_legado = tmp_path / "inspecao_lotes_10dias.xlsx"
    caminho_legado.touch()

    assert resolver_caminho_entrada(ARQUIVO_ENTRADA) == Path(caminho_legado.name)
