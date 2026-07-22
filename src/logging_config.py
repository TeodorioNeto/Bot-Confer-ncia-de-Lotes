"""Configuracao centralizada de logs estruturados."""

import logging
import os
import sys
from pathlib import Path

from pythonjsonlogger.json import JsonFormatter


def configurar_logging(logs_dir):
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    execution_id = os.getenv("EXECUTION_ID", "local")
    bot_id = os.getenv("BOT_ID", "auditor-lotes")

    formatter = JsonFormatter(
        "%(levelname)s %(name)s %(message)s",
        rename_fields={
            "levelname": "level",
            "name": "logger",
        },
        static_fields={
            "execution_id": execution_id,
            "bot_id": bot_id,
        },
        timestamp=True,
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        logs_dir / "execucao.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)