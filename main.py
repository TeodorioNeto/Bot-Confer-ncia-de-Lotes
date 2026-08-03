"""
main.py - orquestra o Auditor de Lotes v1.0.

Fail fast: se dados_entrada/ não existir, alerta no Maestro e encerra
sem tentar processar nada.
"""

import json
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
from src.logger import setup_logger
from vault_client import obter_credencial_erp
from bot import processar_item
from dispatcher import popular_fila
from src.analise_formulario import analisar_e_preencher_formulario
from src.base_referencia import carregar_base_referencia
from src.web_automation import (
    processar_datapool as processar_datapool_web,
    processar_item_web,
)

logger = setup_logger(__name__)



def main():
    maestro = None
    task_id = None
    credencial_erp = None
    total = processados = falhados = 0
    resultado_automacao_web = None
    evidencias_web_por_lote = {}
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

        if conectado_maestro:
            logger.info("Executando Dispatcher antes do consumo do DataPool.")
            popular_fila(maestro)

        if WEB_AUTOMATION_ENABLED and conectado_maestro:
            resultado_automacao_web = {
                "driver": WEB_AUTOMATION_DRIVER,
                "modo": "item_datapool",
                "itens_processados": 0,
                "evidencias": [],
                "erros": [],
            }

        caminho_planilha_analisada = LOGS_DIR / "inspecao_lotes_dia_analisado.xlsx"
        _, resultados_planilha, resumo_analise = analisar_e_preencher_formulario(
            ARQUIVO_INSPECAO,
            caminho_planilha_analisada,
        )

        if WEB_AUTOMATION_ENABLED and not conectado_maestro:
            try:
                logger.info(
                    "Executando automacao web consolidada via %s.",
                    WEB_AUTOMATION_DRIVER,
                )
                resultado_web = processar_datapool_web(
                    driver=WEB_AUTOMATION_DRIVER,
                    return_evidencias=True,
                )
                resultado_automacao_web = {
                    "driver": WEB_AUTOMATION_DRIVER,
                    "modo": "planilha",
                    "itens_processados": resultado_web["total"],
                    "evidencias": resultado_web["evidencias"],
                }
                evidencias_web_por_lote = {
                    str(evidencia.get("lote_id")): evidencia
                    for evidencia in resultado_web["evidencias"]
                    if evidencia.get("lote_id")
                }
            except Exception as erro_web:
                resultado_automacao_web = {
                    "driver": WEB_AUTOMATION_DRIVER,
                    "erro": str(erro_web),
                }
                logger.exception("Falha na automacao web consolidada: %s", erro_web)

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
                if WEB_AUTOMATION_ENABLED:
                    _processar_evidencia_web_do_item(
                        item,
                        resultado,
                        resultado_automacao_web,
                    )
                else:
                    _registrar_evidencia_no_item(item, resultado, evidencias_web_por_lote)
                resumo_divergencias.append(resultado)

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
                    "Automacao web habilitada no modo local; o processamento "
                    "consolidado por planilha ja foi executado via %s.",
                    WEB_AUTOMATION_DRIVER,
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
            "web_automation": resultado_automacao_web,
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
            if resultado_automacao_web:
                _publicar_screenshots(
                    maestro,
                    task_id,
                    resultado_automacao_web.get("evidencias", []),
                )
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


def _processar_evidencia_web_do_item(item, resultado, resumo_web):
    try:
        evidencia = processar_item_web(item, driver=WEB_AUTOMATION_DRIVER)
    except Exception as erro_web:
        if resumo_web is not None:
            resumo_web.setdefault("erros", []).append(
                {
                    "lote_id": resultado.get("lote_id"),
                    "erro": str(erro_web),
                }
            )
        logger.exception(
            "Falha ao gerar evidencia web do item %s: %s",
            resultado.get("lote_id"),
            erro_web,
        )
        return

    if not evidencia:
        return

    _registrar_evidencia_no_item(
        item,
        resultado,
        {str(evidencia.get("lote_id")): evidencia},
    )

    if resumo_web is not None:
        resumo_web["itens_processados"] = resumo_web.get("itens_processados", 0) + 1
        resumo_web.setdefault("evidencias", []).append(evidencia)


def _registrar_evidencia_no_item(item, resultado, evidencias_por_lote):
    lote_id = resultado.get("lote_id")
    evidencia = evidencias_por_lote.get(str(lote_id)) if lote_id is not None else None
    if not evidencia:
        return

    caminho = evidencia.get("screenshot")
    if not caminho:
        return

    if hasattr(item, "values") and isinstance(item.values, dict):
        item.values["screenshot"] = caminho
    else:
        item["screenshot"] = caminho

    resultado["screenshot"] = caminho


if __name__ == "__main__":
    main()
