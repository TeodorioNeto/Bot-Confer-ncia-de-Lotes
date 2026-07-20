"""
Validacoes das regras de negocio do PDD.

RN01 - Estrutura da planilha.
RN02 - Campos obrigatorios.
RN04 - Dominio do status.
RN05 - Normalizacao de status.
RN07 - Observacao obrigatoria para lote reprovado.
"""

import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from src.config import CAMINHO_PLANILHA_PADRAO


STATUS_VALIDOS = {"APROVADO", "REPROVADO", "PENDENTE"}
# Adicionado o 'REPROV.' aqui:
SINONIMOS_STATUS = {"OK": "APROVADO", "NOK": "REPROVADO"}
STATUS_REPROVADO = {"REPROVADO", "NOK", "REPROV."}
ERRO_RN07 = "Reprovacao sem Justificativa Obrigatoria"

COLUNAS_ESTRUTURA = [
    "lote_id",
    "produto",
    "linha",
    "turno",
    "status",
    "responsavel",
    "data",
    "observacao",
]

COLUNAS_OBRIGATORIAS = COLUNAS_ESTRUTURA[:-1]
MINIMO_CAMPOS_REGISTRO = 4


def normalizar_status(status):
    """RN05: normaliza sinonimos conhecidos de status para o valor oficial."""
    if status is None:
        return status

    s = str(status).strip().upper()
    return SINONIMOS_STATUS.get(s, s)


def valida_status(status):
    """RN04: valida se o status normalizado pertence ao dominio conhecido."""
    if not status or not str(status).strip():
        raise ValueError("status e obrigatorio (RN02/RN04)")

    normalizado = normalizar_status(status)
    return normalizado in STATUS_VALIDOS


def valida_data(valor):
    """RN06: aceita datas reais ou texto estritamente no formato DD/MM/AAAA."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        raise ValueError("data e obrigatoria (RN02/RN06)")

    if isinstance(valor, (datetime, date)):
        return True

    texto = str(valor).strip()
    try:
        datetime.strptime(texto, "%d/%m/%Y")
    except ValueError:
        return False
    return True


def carregar_planilha(caminho_arquivo):
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
    colunas_estrutura = set(COLUNAS_ESTRUTURA)

    for indice, linha in df.iterrows():
        valores = {str(valor).strip() for valor in linha.dropna()}

        if colunas_estrutura.issubset(valores):
            return indice

    return None


def filtrar_linhas_de_registro(df):
    colunas_existentes = [coluna for coluna in COLUNAS_ESTRUTURA if coluna in df.columns]

    if not colunas_existentes:
        return df

    preenchidos = df[colunas_existentes].notna() & ~df[colunas_existentes].astype(str).apply(
        lambda coluna: coluna.str.strip().eq("")
    )
    # Heuristica para ignorar rodapes/legendas mantendo linhas reais parcialmente preenchidas.
    minimo_campos = min(MINIMO_CAMPOS_REGISTRO, len(colunas_existentes))
    return df.loc[preenchidos.sum(axis=1) >= minimo_campos]


def valida_estrutura(caminho_arquivo=CAMINHO_PLANILHA_PADRAO, df=None):
    """RN01: valida se o arquivo .xlsx possui exatamente as 8 colunas do PDD."""
    df = df if df is not None else carregar_planilha(caminho_arquivo)
    faltantes = obter_colunas_faltantes(df)
    extras = obter_colunas_extras(df)

    if faltantes:
        logging.error("Colunas obrigatorias ausentes: %s", sorted(faltantes))
        return False

    if extras:
        logging.error("Colunas nao previstas no layout RN01: %s", sorted(extras))
        return False

    if list(df.columns) != COLUNAS_ESTRUTURA:
        logging.error("Ordem das colunas invalida para o layout RN01.")
        return False

    logging.info("As 8 colunas obrigatorias do layout RN01 estao presentes.")
    return True


def valida_campos_obrigatorios(caminho_arquivo=CAMINHO_PLANILHA_PADRAO, df=None):
    """RN02: valida campos obrigatorios e aponta registros com dados ausentes."""
    df = df if df is not None else carregar_planilha(caminho_arquivo)
    faltantes = obter_colunas_faltantes(df)

    if faltantes:
        logging.error("Colunas obrigatorias ausentes: %s", sorted(faltantes))
        return False

    erros = encontrar_erros_rn02(df)
    valido = not erros

    for erro in erros:
        logging.error(
            "Campos obrigatorios vazios na linha %s: %s",
            erro["linha"],
            ", ".join(erro["campos"]),
        )

    if valido:
        logging.info("Todos os campos obrigatorios estao preenchidos.")

    return valido


def valida_observacao_reprovado(caminho_arquivo=CAMINHO_PLANILHA_PADRAO, df=None):
    """RN07: exige observacao quando o status final for REPROVADO ou NOK."""
    df = df if df is not None else carregar_planilha(caminho_arquivo)
    faltantes = {"status", "observacao"} - set(df.columns)

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


def encontrar_erros_rn02(df):
    erros = []

    for indice, registro in df.iterrows():
        campos_vazios = []

        for coluna in COLUNAS_OBRIGATORIAS:
            valor = registro[coluna]

            if pd.isna(valor) or str(valor).strip() == "":
                campos_vazios.append(coluna)

        if campos_vazios:
            erros.append(
                {
                    "linha": int(indice) + 1,
                    "lote_id": "" if pd.isna(registro["lote_id"]) else registro["lote_id"],
                    "campos": campos_vazios,
                }
            )

    return erros


def encontrar_erros_rn07(df):
    erros = []

    for indice, registro in df.iterrows():
        status_original = normalizar_status_original(registro["status"])
        status_final = normalizar_status(registro["status"])

        if status_original in STATUS_REPROVADO and observacao_vazia(registro["observacao"]):
            erros.append(
                {
                    "linha": int(indice) + 1,
                    "status": status_final,
                    "erro": ERRO_RN07,
                }
            )

    return erros


def normalizar_status_original(valor):
    if pd.isna(valor):
        return ""

    return str(valor).strip().upper()


def observacao_vazia(valor):
    return pd.isna(valor) or str(valor).strip() == ""


def obter_colunas_faltantes(df):
    return set(COLUNAS_ESTRUTURA) - set(df.columns)


def obter_colunas_extras(df):
    return set(df.columns) - set(COLUNAS_ESTRUTURA)
