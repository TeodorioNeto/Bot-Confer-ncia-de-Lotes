"""
config.py - carrega as variáveis de ambiente do bot. 
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

MAESTRO_SERVER = os.getenv("MAESTRO_SERVER")
MAESTRO_LOGIN = os.getenv("MAESTRO_LOGIN")
MAESTRO_KEY = os.getenv("MAESTRO_KEY")
MAESTRO_ENABLED = os.getenv("MAESTRO_ENABLED", "false").lower() == "true"
VAULT_ENABLED = os.getenv("VAULT_ENABLED", "false").lower() == "true"

DATAPOOL_LABEL = os.getenv("DATAPOOL_LABEL", "FilaAuditoriaLotes")
CREDENCIAL_LABEL = os.getenv("CREDENCIAL_LABEL", "credencial_erp")
WEB_AUTOMATION_ENABLED = os.getenv("WEB_AUTOMATION_ENABLED", "false").lower() == "true"
WEB_AUTOMATION_DRIVER = os.getenv("WEB_AUTOMATION_DRIVER", "playwright").lower()
WEB_AUTOMATION_URL = os.getenv("WEB_AUTOMATION_URL")

DADOS_ENTRADA_DIR = BASE_DIR / "dados_entrada"
ARQUIVO_INSPECAO = BASE_DIR / os.getenv(
    "ARQUIVO_INSPECAO", "dados_entrada/inspecao_lotes_dia.xlsx"
)
LOGS_DIR = BASE_DIR / "logs"
DATA_OUTPUT_DIR = BASE_DIR / os.getenv("DATA_OUTPUT_DIR", "data/output")
