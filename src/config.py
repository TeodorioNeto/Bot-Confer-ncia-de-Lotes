"""
config.py - Variaveis de ambiente e caminhos usados pelo bot.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO_INSPECAO = BASE_DIR / "Inspecao_lotes_Formulario_Analise-Matriz-Priorização.xlsx"
CAMINHO_PLANILHA_PADRAO = ARQUIVO_INSPECAO
ABA_INSPECAO = "Inspecao_14_06_2026"
ABA_BASE_REFERENCIA = "Base_Referencia"
