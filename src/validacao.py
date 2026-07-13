import logging

import pandas as pd

colunas_obrigatorias = ['lote_id', 'produto', 'linha', 'turno', 'status', 'responsavel', 'data']


def valida_estrutura(caminho_arquivo='dados.csv'):
    df = pd.read_csv(caminho_arquivo, nrows=0)
    file_cols = set(df.columns)

    if len(file_cols)==8:
        logging.info("Todas as colunas obrigatórias estão presentes.")
        return True

    missing = set(colunas_obrigatorias) - file_cols
    logging.error(f"As seguintes colunas obrigatórias estão ausentes: {missing}")
    return False


def valida_campos_obrigatorios(caminho_arquivo='dados.csv'):
    df = pd.read_csv(caminho_arquivo)

    for coluna in colunas_obrigatorias:
        if coluna not in df.columns:
            logging.error(f"A coluna obrigatória não foi encontrada: {coluna}")
            return False

        valores = df[coluna]
        vazios = valores.isna() | valores.astype(str).str.strip().eq('')

        if vazios.any():
            logging.error(f"Existem registros com campos obrigatórios ausentes na coluna: {coluna}")
            return False

    logging.info("Todos os campos obrigatórios estão preenchidos.")
    return True
