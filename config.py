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
ML_ENABLED = os.getenv("ML_ENABLED", "false").lower() == "true"
ML_API_URL = os.getenv("ML_API_URL", "http://127.0.0.1:8000")
ML_TIMEOUT_SECONDS = float(os.getenv("ML_TIMEOUT_SECONDS", "2"))
ML_MAX_FAILURES = int(os.getenv("ML_MAX_FAILURES", "5"))
ML_CONFIANCA_MINIMA = float(os.getenv("ML_CONFIANCA_MINIMA", "0.85"))
ML_DIVERGENCIA_URL = os.getenv("ML_DIVERGENCIA_URL", "").strip()
ML_DIVERGENCIA_TIMEOUT_SECONDS = float(
    os.getenv("ML_DIVERGENCIA_TIMEOUT_SECONDS", "2")
)
ML_DIVERGENCIA_MOCK_DELAY_SECONDS = float(
    os.getenv("ML_DIVERGENCIA_MOCK_DELAY_SECONDS", "0")
)
ML_DIVERGENCIA_FORCE_CONFIDENCE = os.getenv(
    "ML_DIVERGENCIA_FORCE_CONFIDENCE", ""
).strip()
ML_DIVERGENCIA_FORCE_ERROR = os.getenv(
    "ML_DIVERGENCIA_FORCE_ERROR", "false"
).lower() == "true"

# Pipeline corporativo S10-B. Os labels devem corresponder aos bots
# registrados no BotCity Maestro e podem ser alterados sem modificar o codigo.
PIPELINE_BOT_A_LABEL = os.getenv(
    "PIPELINE_BOT_A_LABEL", "teodorio-orquestrador-v1"
)
PIPELINE_BOT_B_LABEL = os.getenv(
    "PIPELINE_BOT_B_LABEL", "teodorio-conferencia-ml-v1"
)
PIPELINE_BOT_C_LABEL = os.getenv(
    "PIPELINE_BOT_C_LABEL", "teodorio-relatorio-alertas-v1"
)
PIPELINE_PRIORITY = int(os.getenv("PIPELINE_PRIORITY", "5"))
PIPELINE_TEST_MODE = os.getenv("PIPELINE_TEST_MODE", "false").lower() == "true"
PIPELINE_WAIT_TIMEOUT_SECONDS = float(
    os.getenv("PIPELINE_WAIT_TIMEOUT_SECONDS", "300")
)
PIPELINE_POLL_INTERVAL_SECONDS = float(
    os.getenv("PIPELINE_POLL_INTERVAL_SECONDS", "5")
)
BASE_RETRY_MAX_ATTEMPTS = int(os.getenv("BASE_RETRY_MAX_ATTEMPTS", "3"))
BASE_RETRY_DELAY_SECONDS = float(os.getenv("BASE_RETRY_DELAY_SECONDS", "1"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME)
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

DADOS_ENTRADA_DIR = BASE_DIR / "dados_entrada"
ARQUIVO_INSPECAO = BASE_DIR / os.getenv(
    "ARQUIVO_INSPECAO", "dados_entrada/inspecao_lotes_dia.xlsx"
)
ARQUIVO_BASE_REFERENCIA = BASE_DIR / os.getenv(
    "ARQUIVO_BASE_REFERENCIA", str(ARQUIVO_INSPECAO)
)
LOGS_DIR = BASE_DIR / "logs"
DEAD_LETTER_FILE = BASE_DIR / os.getenv(
    "DEAD_LETTER_FILE", "logs/dead_letter_pipeline.jsonl"
)
DATA_OUTPUT_DIR = BASE_DIR / os.getenv("DATA_OUTPUT_DIR", "data/output")

# Pipeline Capstone. Mantem o fluxo S10-B disponivel e habilita a cadeia
# expandida apenas quando solicitado explicitamente.
CAPSTONE_ENABLED = os.getenv("CAPSTONE_ENABLED", "false").lower() == "true"
ORCHESTRATOR_MODE = os.getenv("ORCHESTRATOR_MODE", "shadow").strip().lower()
CAPSTONE_BUSINESS_KEY = os.getenv("CAPSTONE_BUSINESS_KEY", "").strip()
CAPSTONE_STATE_DIR = BASE_DIR / os.getenv(
    "CAPSTONE_STATE_DIR", "data/capstone_state"
)
CAPSTONE_DESKTOP_MODE = os.getenv(
    "CAPSTONE_DESKTOP_MODE", "simulated"
).strip().lower()
CAPSTONE_WEB_MODE = os.getenv("CAPSTONE_WEB_MODE", "simulated").strip().lower()
CAPSTONE_DESKTOP_RETRY_ATTEMPTS = int(
    os.getenv("CAPSTONE_DESKTOP_RETRY_ATTEMPTS", "3")
)
CAPSTONE_WEB_RETRY_ATTEMPTS = int(
    os.getenv("CAPSTONE_WEB_RETRY_ATTEMPTS", "3")
)
CAPSTONE_RETRY_DELAY_SECONDS = float(
    os.getenv("CAPSTONE_RETRY_DELAY_SECONDS", "1")
)
CAPSTONE_DESKTOP_STARTUP_SECONDS = float(
    os.getenv("CAPSTONE_DESKTOP_STARTUP_SECONDS", "2")
)
CAPSTONE_DESKTOP_EXPORT_TIMEOUT_SECONDS = float(
    os.getenv("CAPSTONE_DESKTOP_EXPORT_TIMEOUT_SECONDS", "20")
)

PIPELINE_BOT_DESKTOP_LABEL = os.getenv(
    "PIPELINE_BOT_DESKTOP_LABEL", "teodorio-coleta-desktop-v1"
)
PIPELINE_BOT_CAPSTONE_LABEL = os.getenv(
    "PIPELINE_BOT_CAPSTONE_LABEL", "teodorio-orquestrador-capstone-v1"
)
PIPELINE_BOT_WEB_LABEL = os.getenv(
    "PIPELINE_BOT_WEB_LABEL", "teodorio-coleta-web-v1"
)
PIPELINE_BOT_CONSOLIDACAO_LABEL = os.getenv(
    "PIPELINE_BOT_CONSOLIDACAO_LABEL", "teodorio-consolidacao-v1"
)
PIPELINE_BOT_ML_LABEL = os.getenv(
    "PIPELINE_BOT_ML_LABEL", "teodorio-classificador-ml-v1"
)
PIPELINE_BOT_RELATORIO_LABEL = os.getenv(
    "PIPELINE_BOT_RELATORIO_LABEL", PIPELINE_BOT_C_LABEL
)

PIPELINE_DESKTOP_PRIORITY = int(os.getenv("PIPELINE_DESKTOP_PRIORITY", "9"))
PIPELINE_WEB_PRIORITY = int(os.getenv("PIPELINE_WEB_PRIORITY", "7"))
PIPELINE_CONSOLIDACAO_PRIORITY = int(
    os.getenv("PIPELINE_CONSOLIDACAO_PRIORITY", "8")
)
PIPELINE_ML_PRIORITY = int(os.getenv("PIPELINE_ML_PRIORITY", "5"))
PIPELINE_RELATORIO_PRIORITY = int(os.getenv("PIPELINE_RELATORIO_PRIORITY", "6"))
