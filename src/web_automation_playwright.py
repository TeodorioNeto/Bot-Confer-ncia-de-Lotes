"""
src/web_automation_playwright.py
Orquestrador Playwright com suporte a sincronização de Tema (Dark/Light).
"""

import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from src.logger import setup_logger
from src.pages.form_page import FormPagePlaywright
from src.pages.login_page import LoginPagePlaywright
from src.web_evidencias import montar_caminho_screenshot, obter_url_automacao

load_dotenv()

logger = setup_logger("PlaywrightEngine")


def emitir_log(mensagem, tipo="info", callback_log=None):
    if tipo == "info":
        logger.info(mensagem)
    elif tipo == "warn":
        logger.warning(mensagem)
    elif tipo == "error":
        logger.error(mensagem)
    elif tipo == "success":
        logger.info(mensagem)

    if callback_log:
        try:
            callback_log(mensagem, tipo)
        except Exception:
            pass


def carregar_datapool_tratado():
    caminho_planilha = (
        Path(__file__).resolve().parent.parent
        / "dados_entrada"
        / "inspecao_lotes_dia.xlsx"
    )

    produtos_validos = ["Placa Mãe V1", "Processador X", "Memória RAM 16GB"]
    status_validos = ["Pendente", "Em Processamento", "Concluído"]

    lotes_tratados = []

    if caminho_planilha.exists():
        logger.info("Planilha carregada com sucesso: %s", caminho_planilha)
        df = pd.read_excel(caminho_planilha).fillna("")

        for idx, row in df.iterrows():
            lote_id = str(row.get("lote_id") or row.get("Lote") or f"LOTE-2026-{idx+1:04d}").strip()
            prod = produtos_validos[idx % len(produtos_validos)]
            st = status_validos[idx % len(status_validos)]

            lotes_tratados.append({
                "lote": lote_id,
                "lote_id": lote_id,
                "produto": prod,
                "status": st,
            })
    else:
        logger.warning(
            "ATENÇÃO: Planilha de entrada NÃO encontrada em '%s'. Nenhum lote será processado!",
            caminho_planilha,
        )
        return []

    return lotes_tratados


def processar_datapool_playwright(delay_passo=0.3, callback_log=None, theme="dark"):
    url = obter_url_automacao()
    headless = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"

    lotes = carregar_datapool_tratado()

    if not lotes:
        emitir_log("DataPool está vazio ou a planilha não foi localizada.", "warn", callback_log)
        return 0

    emitir_log(f"Iniciando execução Playwright | Total de lotes: {len(lotes)} | Tema: {theme.upper()}", "info", callback_log)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            channel="msedge",
            args=["--start-maximized"],
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        try:
            emitir_log(f"Acessando a URL do formulário: {url}", "info", callback_log)
            page.goto(url)

            # Aplica o tema correto na nova janela do robô
            if theme == "light":
                page.evaluate("""
                    document.documentElement.setAttribute('data-theme', 'light');
                    const toggle = document.getElementById('themeToggle');
                    if (toggle) toggle.checked = true;
                """)

            login_page = LoginPagePlaywright(page, delay_passo=delay_passo)
            form_page = FormPagePlaywright(page, delay_passo=delay_passo)

            emitir_log("Realizando autenticação na plataforma...", "info", callback_log)
            login_page.fazer_login()

            processados = 0
            for idx, item in enumerate(lotes, start=1):
                msg_lote = f"[{idx:02d}/{len(lotes):02d}] Lote: {item['lote_id']} | Produto: {item['produto']} | Status: {item['status']}"
                emitir_log(msg_lote, "info", callback_log)

                page.evaluate("document.getElementById('formLote').reset()")

                form_page.preencher_lote(item)
                sucesso = form_page.submeter_e_aguardar()

                caminho_screenshot = montar_caminho_screenshot(item, "playwright")
                caminho_screenshot.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(caminho_screenshot))

                if sucesso:
                    emitir_log(f"Lote {item['lote_id']} gravado com SUCESSO.", "success", callback_log)
                else:
                    emitir_log(f"Lote {item['lote_id']} submetido com ALERTAS.", "warn", callback_log)

                processados += 1

            emitir_log(f"Processamento finalizado com sucesso! Total: {processados} lotes", "success", callback_log)
            time.sleep(1)
            return processados

        except Exception as e:
            emitir_log(f"Falha crítica no Playwright: {e}", "error", callback_log)
            raise e
        finally:
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    processar_datapool_playwright(delay_passo=0.2)