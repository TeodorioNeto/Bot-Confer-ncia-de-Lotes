"""
main.py - orquestra o Auditor de Lotes v1.0.

Fail fast: se dados_entrada/ não existir, alerta no Maestro e encerra
sem tentar processar nada.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from botcity.maestro import BotMaestroSDK, AutomationTaskFinishStatus, AlertType, ErrorType
from config import (
    MAESTRO_ENABLED,
    MAESTRO_KEY,
    MAESTRO_LOGIN,
    MAESTRO_SERVER,
    VAULT_ENABLED,
    DADOS_ENTRADA_DIR,
    ARQUIVO_INSPECAO,
    DATAPOOL_LABEL,
    LOGS_DIR,
    WEB_AUTOMATION_DRIVER,
    WEB_AUTOMATION_ENABLED,
)
from src.logging_config import configurar_logging
from vault_client import obter_credencial_erp
from bot import processar_item
from dispatcher import popular_fila
from src.analise_formulario import analisar_e_preencher_formulario
from src.base_referencia import carregar_base_referencia
from src.web_automation import montar_dados_lote, preencher_formulario

configurar_logging(LOGS_DIR)
logger = logging.getLogger(__name__)



def main():
    maestro = None
    task_id = None
    credencial_erp = None
    total = processados = falhados = 0
    try:
        maestro = BotMaestroSDK.from_sys_args()
        task_id = getattr(maestro, "task_id", None)
        if task_id:
            print(f"Rodando via Maestro. Task ID: {task_id}")
        else:
            if MAESTRO_ENABLED:
                maestro.login(
                    server=MAESTRO_SERVER,
                    login=MAESTRO_LOGIN,
                    key=MAESTRO_KEY,
                )
            maestro.RAISE_NOT_CONNECTED = False
            print("Rodando localmente (sem Runner).")

        conectado_maestro = bool(task_id or MAESTRO_ENABLED)
        logger.info("Iniciando auditoria de lotes.")
        if task_id:
            maestro.alert(
                task_id=task_id,
                title="Início da execução",
                message="Iniciando auditoria de lotes.",
                alert_type=AlertType.INFO,
            )

        if not DADOS_ENTRADA_DIR.exists() or not ARQUIVO_INSPECAO.exists():
            raise FileNotFoundError(
                f"Planilha de entrada não encontrada em: {ARQUIVO_INSPECAO}"
            )

        if VAULT_ENABLED and conectado_maestro:
            credencial_erp = obter_credencial_erp(maestro)

        # O Dispatcher sempre precede o Performer quando há conexão com o Maestro.
        if conectado_maestro:
            logger.info("Executando Dispatcher antes do Performer.")
            popular_fila(maestro)

        caminho_planilha_analisada = LOGS_DIR / "inspecao_lotes_dia_analisado.xlsx"
        _, resultados_planilha, resumo_analise = analisar_e_preencher_formulario(
            ARQUIVO_INSPECAO,
            caminho_planilha_analisada,
        )

        resumo_divergencias = []
        if conectado_maestro:
            base_referencia = carregar_base_referencia(ARQUIVO_INSPECAO)
            datapool = maestro.get_datapool(DATAPOOL_LABEL)

            while datapool.has_next():
                item = datapool.next(task_id=task_id)
                if item is None:
                    break

                total += 1
                resultado = processar_item(item, base_referencia)
                resumo_divergencias.append(resultado)

                if WEB_AUTOMATION_ENABLED:
                    try:
                        logger.info(
                            "Executando automacao web via %s para o lote %s.",
                            WEB_AUTOMATION_DRIVER,
                            resultado["lote_id"],
                        )
                        caminho_screenshot = item.get_value("screenshot") or None
                        evidencia_web = preencher_formulario(
                            dados_lote=montar_dados_lote(item),
                            credencial=credencial_erp,
                            screenshot_path=caminho_screenshot,
                            analises=resultado["analises"],
                            linha_planilha=item.get_value("linha_planilha"),
                        )
                        resultado["web_automation"] = evidencia_web
                        resultado["screenshot"] = evidencia_web.get("screenshot")
                    except Exception as erro_web:
                        resultado["web_automation_error"] = str(erro_web)
                        if not resultado["divergencias"]:
                            item.report_error(
                                error_type=ErrorType.SYSTEM,
                                finish_message=f"Falha na automacao web: {erro_web}",
                            )
                            falhados += 1
                            logger.exception(
                                "Falha na automacao web do lote %s: %s",
                                resultado["lote_id"],
                                erro_web,
                            )
                            continue

                        logger.exception(
                            "Falha ao gerar evidencia web do lote divergente %s: %s",
                            resultado["lote_id"],
                            erro_web,
                        )

                if resultado["divergencias"]:
                    item.report_error(
                        error_type=ErrorType.BUSINESS,
                        finish_message=" | ".join(resultado["divergencias"]),
                    )
                    falhados += 1
                    logger.warning(
                        "Item %s barrado: %s",
                        resultado["lote_id"],
                        " | ".join(resultado["divergencias"]),
                    )
                else:
                    item.report_done()
                    processados += 1
                    logger.info("Item %s processado.", resultado["lote_id"])
        else:
            if WEB_AUTOMATION_ENABLED:
                logger.warning(
                    "Automacao web habilitada, mas o modo local por planilha nao "
                    "executa a tela por item. Use o fluxo com DataPool para acionar "
                    "Playwright ou Selenium por lote."
                )
            total = resumo_analise["total_registros"]
            falhados = resumo_analise["registros_com_divergencia"]
            processados = total - falhados
            resumo_divergencias = resultados_planilha

        resumo = {
            "data_execucao": datetime.now().isoformat(),
            "total_itens": total,
            "processados": processados,
            "falhados": falhados,
            "analise_planilha": resumo_analise,
            "divergencias": resumo_divergencias,
        }
        caminho_resumo = LOGS_DIR / "resumo_execucao.json"
        caminho_resumo.write_text(
            json.dumps(resumo, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        if task_id:
            maestro.post_artifact(
                task_id=task_id,
                artifact_name="resumo_execucao.json",
                filepath=str(caminho_resumo),
            )
            maestro.post_artifact(
                task_id=task_id,
                artifact_name="inspecao_lotes_dia_analisado.xlsx",
                filepath=str(caminho_planilha_analisada),
            )
            _publicar_screenshots(maestro, task_id, resumo_divergencias)
            maestro.finish_task(
                task_id=task_id,
                status=AutomationTaskFinishStatus.SUCCESS,
                message="Auditoria concluída e formulário de análise preenchido.",
                total_items=total,
                processed_items=processados,
                failed_items=falhados,
            )

        logger.info(
            "Auditoria concluída: %d processados, %d falhados de %d total.",
            processados,
            falhados,
            total,
        )
    except Exception as erro:
        logger.exception("Falha na auditoria: %s", erro)
        if maestro is not None and task_id:
            try:
                maestro.alert(
                    task_id=task_id,
                    title="Falha na execução",
                    message=str(erro),
                    alert_type=AlertType.ERROR,
                )
            except Exception:
                logger.exception("Não foi possível gerar o alerta de falha.")

            try:
                falhados_reportados = max(falhados, total - processados)
                maestro.finish_task(
                    task_id=task_id,
                    status=AutomationTaskFinishStatus.FAILED,
                    message=f"Auditoria interrompida: {erro}",
                    total_items=total,
                    processed_items=processados,
                    failed_items=falhados_reportados,
                )
            except Exception:
                logger.exception("Não foi possível reportar a falha ao Maestro.")
        raise


def _publicar_screenshots(maestro, task_id, resultados):
    for indice, resultado in enumerate(resultados, start=1):
        caminho = resultado.get("screenshot")
        if not caminho:
            continue

        arquivo = Path(caminho)
        if not arquivo.exists():
            logger.warning("Screenshot registrado nao encontrado: %s", arquivo)
            continue

        maestro.post_artifact(
            task_id=task_id,
            artifact_name=f"screenshot_lote_{indice}.png",
            filepath=str(arquivo),
        )


if __name__ == "__main__":
    main()
