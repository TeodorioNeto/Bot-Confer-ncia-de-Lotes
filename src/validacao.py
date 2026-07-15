import logging
from pathlib import Path

import pandas as pd


COLUNAS_RN07 = ["status", "observacao"]
STATUS_REPROVADO = {"REPROVADO", "NOK"}
ERRO_RN07 = "Reprovacao sem Justificativa Obrigatoria"


def carregar_planilha_rn07(caminho_arquivo):
    caminho = Path(caminho_arquivo)

    if caminho.suffix.lower() != ".xlsx":
        raise ValueError("O arquivo de entrada deve estar no formato .xlsx")

    df_bruto = pd.read_excel(caminho, header=None)
    linha_cabecalho = encontrar_linha_cabecalho(df_bruto)

    if linha_cabecalho is None:
        return pd.DataFrame()

    colunas = df_bruto.iloc[linha_cabecalho].astype(str).str.strip()
    df = df_bruto.iloc[linha_cabecalho + 1 :].copy()
    df.columns = colunas
    df = df.loc[:, ~df.columns.isin(["", "nan", "NaN"])]
    df = df.dropna(how="all")
    return filtrar_linhas_de_registro(df)


def encontrar_linha_cabecalho(df):
    colunas_rn07 = set(COLUNAS_RN07)

    for indice, linha in df.iterrows():
        valores = {str(valor).strip() for valor in linha.dropna()}

        if valores & colunas_rn07:
            return indice

    return None


def filtrar_linhas_de_registro(df):
    if "status" not in df.columns:
        return df

    status = df["status"]
    preenchido = status.notna() & ~status.astype(str).str.strip().eq("")
    return df.loc[preenchido]


def valida_observacao_reprovado(caminho_arquivo="dados.xlsx"):
    """RN07: exige observacao quando o status final for REPROVADO ou NOK."""
    df = carregar_planilha_rn07(caminho_arquivo)
    faltantes = obter_colunas_faltantes(df)

    if faltantes:
        logging.error("Colunas obrigatorias da RN07 ausentes: %s", sorted(faltantes))
        return False

    erros = encontrar_erros_rn07(df)

    for erro in erros:
        logging.error(
            "%s na linha %s: status=%s",
            ERRO_RN07,
            erro["linha"],
            erro["status"],
        )

    if not erros:
        logging.info("Todos os lotes reprovados possuem observacao.")

    return not erros


def encontrar_erros_rn07(df):
    erros = []

    for indice, registro in df.iterrows():
        status = normalizar_status(registro["status"])

        if status in STATUS_REPROVADO and observacao_vazia(registro["observacao"]):
            erros.append(
                {
                    "linha": int(indice) + 1,
                    "status": status,
                    "erro": ERRO_RN07,
                }
            )

    return erros


def normalizar_status(valor):
    if pd.isna(valor):
        return ""

    return str(valor).strip().upper()


def observacao_vazia(valor):
    return pd.isna(valor) or str(valor).strip() == ""


def obter_colunas_faltantes(df):
    return set(COLUNAS_RN07) - set(df.columns)
