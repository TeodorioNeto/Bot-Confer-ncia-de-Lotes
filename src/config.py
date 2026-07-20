"""
config.py - Variaveis de ambiente e caminhos usados pelo bot.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO_INSPECAO = BASE_DIR / "dados_entrada" / "inspecao_lotes_dia.xlsx"
CAMINHO_PLANILHA_PADRAO = ARQUIVO_INSPECAO
ABA_INSPECAO = "Inspecao_14_06_2026"
ABA_BASE_REFERENCIA = "Base_Referencia"
