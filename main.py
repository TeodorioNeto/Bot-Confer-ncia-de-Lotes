"""
main.py - orquestra o Auditor de Lotes v1.0.

Fail fast: se dados_entrada/ não existir, alerta no Maestro e encerra
sem tentar processar nada.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from botcity.maestro import BotMaestroSDK, AutomationTaskFinishStatus, AlertType

from config import (
    MAESTRO_ENABLED,
    VAULT_ENABLED,
    DADOS_ENTRADA_DIR,
    DATAPOOL_LABEL,
    LOGS_DIR,
)
from vault_client import obter_credencial_erp
from bot import processar_item
from src.base_referencia import carregar_base_referencia

LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "execucao.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def main():
    maestro = BotMaestroSDK.from_sys_args()
    maestro.RAISE_NOT_CONNECTED = not MAESTRO_ENABLED

    execution = maestro.get_execution()
    task_id = execution.task_id if execution else None

    logger.info("Iniciando auditoria de acessos.")
    if task_id:
        maestro.new_log_entry  # placeholder de ponto de extensão, se quiserem log estruturado depois

    # Fail Fast: pasta de entrada precisa existir
    if not DADOS_ENTRADA_DIR.exists():
        mensagem = f"Pasta {DADOS_ENTRADA_DIR} não encontrada. Encerrando."
        logger.error(mensagem)
        if task_id:
            maestro.generate_alert(
                task_id=task_id,
                title="Pasta de entrada ausente",
                message=mensagem,
                alert_type=AlertType.ERROR,
            )
            maestro.finish_task(
                task_id=task_id,
                status=AutomationTaskFinishStatus.FAILED,
                message=mensagem,
            )
        return

    # Credencial (não loga a senha)
    if VAULT_ENABLED:
        obter_credencial_erp(maestro)

    base_referencia = carregar_base_referencia()
    datapool = maestro.get_datapool(DATAPOOL_LABEL)

    total = processados = falhados = 0
    resumo_divergencias = []

    while datapool.has_next():
        item = datapool.next(task_id=task_id)
        if item is None:
            break

        total += 1
        try:
            resultado = processar_item(item, base_referencia)
            resumo_divergencias.append(resultado)
            item.report_done()
            processados += 1
            logger.info("Item %s processado.", resultado["lote_id"])
        except ValueError as erro:
            item.report_error(message=str(erro), error_type="ValidationError")
            falhados += 1
            logger.warning("Item com erro de validação: %s", erro)

    # Relatório final em JSON, postado como artefato
    resumo = {
        "data_execucao": datetime.now().isoformat(),
        "total_itens": total,
        "processados": processados,
        "falhados": falhados,
        "divergencias": resumo_divergencias,
    }
    caminho_resumo = LOGS_DIR / "resumo_execucao.json"
    caminho_resumo.write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")

    if task_id:
        maestro.post_artifact(
            task_id=task_id,
            artifact_name="resumo_execucao.json",
            filepath=str(caminho_resumo),
        )
        maestro.finish_task(
            task_id=task_id,
            status=AutomationTaskFinishStatus.SUCCESS,
            message="Auditoria de lotes concluída.",
            total_items=total,
            processed_items=processados,
            failed_items=falhados,
        )

    logger.info("Auditoria concluída: %d processados, %d falhados de %d total.", processados, falhados, total)


if __name__ == "__main__":
    main()