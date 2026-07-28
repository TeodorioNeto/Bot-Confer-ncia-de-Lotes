"""
src/logger.py
Configuração centralizada de logging estruturado e colorido para o Bot.
"""

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "execucao.log"


class CustomFormatter(logging.Formatter):
    """Formatador para o terminal com suporte a cores e alinhamento visual."""

    grey = "\x1b[38;20m"
    white = "\x1b[37;20m"       # 👈 Altere/adicione essa cor para o branco
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s | %(levelname)-8s | [%(name)s] | %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: white + format_str + reset,    # 👈 Mude de 'blue' para 'white'
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }


def setup_logger(name: str = "BotConferencia") -> logging.Logger:
    """Retorna uma instância configurada e padronizada do Logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        return logger

    # 1. Output no Terminal (Colorido)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(CustomFormatter())

    # 2. Output em Arquivo de Log (Detalhado com linha e arquivo)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | [%(name)s] | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Evita poluição de bibliotecas de terceiros
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    return logger