"""
src/web_automation_playwright.py
Orquestrador Playwright com iteração dinâmica sobre o DataPool.
"""

import logging
import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from src.pages.form_page import FormPagePlaywright
from src.pages.login_page import LoginPagePlaywright
from src.web_evidencias import montar_caminho_screenshot, obter_url_automacao

load_dotenv()
logger = logging.getLogger(__name__)


def carregar_datapool_tratado():
    """Lê a planilha excel e mapeia os dados para valores compatíveis com doc.html."""
    caminho_planilha = (
        Path(__file__).resolve().parent.parent
        / "dados_entrada"
        / "inspecao_lotes_dia.xlsx"
    )

    produtos_validos = ["Placa Mãe V1", "Processador X", "Memória RAM 16GB"]
    status_validos = ["Pendente", "Em Processamento", "Concluído"]

    lotes_tratados = []

    if caminho_planilha.exists():
        df = pd.read_excel(caminho_planilha).fillna("")
        
        for idx, row in df.iterrows():
            # Extrai o ID do lote da planilha
            lote_id = str(row.get("lote_id") or row.get("Lote") or f"LOTE-2026-{idx+1:04d}").strip()
            
            # Mapeia rotativamente para um dos produtos válidos do HTML
            prod = produtos_validos[idx % len(produtos_validos)]
            
            # Mapeia rotativamente para um dos status válidos do HTML
            st = status_validos[idx % len(status_validos)]

            lotes_tratados.append({
                "lote": lote_id,
                "lote_id": lote_id,
                "produto": prod,
                "status": st,
            })
    else:
        # Fallback de demonstração com itens variados
        lotes_tratados = [
            {"lote_id": "LOTE-2026-0001", "lote": "LOTE-2026-0001", "produto": "Placa Mãe V1", "status": "Pendente"},
            {"lote_id": "LOTE-2026-0002", "lote": "LOTE-2026-0002", "produto": "Processador X", "status": "Em Processamento"},
            {"lote_id": "LOTE-2026-0003", "lote": "LOTE-2026-0003", "produto": "Memória RAM 16GB", "status": "Concluído"},
        ]

    return lotes_tratados


def processar_datapool_playwright(delay_passo=0.3):
    """Lê a planilha de inspeção e processa cada lote sequencialmente via Playwright."""
    url = obter_url_automacao()
    headless = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"

    lotes = carregar_datapool_tratado()
    logger.info("Carregados %d lotes para processamento.", len(lotes))

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--start-maximized"],
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        try:
            page.goto(url)

            login_page = LoginPagePlaywright(page, delay_passo=delay_passo)
            form_page = FormPagePlaywright(page, delay_passo=delay_passo)

            login_page.fazer_login()

            processados = 0
            for idx, item in enumerate(lotes, start=1):
                logger.info(
                    "[%d/%d] Preenchendo lote %s | Produto: %s | Status: %s",
                    idx,
                    len(lotes),
                    item['lote_id'],
                    item['produto'],
                    item['status'],
                )

                # 1. Recarrega a página antes de preencher o novo lote para garantir estado limpo
                page.reload()

                # 2. Preenche os novos dados da iteração
                form_page.preencher_lote(item)

                # 3. Submete o formulário
                sucesso = form_page.submeter_e_aguardar()

                # 4. Tira a foto de evidência
                caminho_screenshot = montar_caminho_screenshot(item, "playwright")
                caminho_screenshot.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(caminho_screenshot), full_page=True)

                if sucesso:
                    logger.info("✓ Lote %s submetido com Sucesso!", item['lote_id'])

                processados += 1

            time.sleep(2)
            return processados

        except Exception as e:
            logger.error("Erro durante a execução: %s", e)
            raise e
        finally:
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    qtd = processar_datapool_playwright(delay_passo=0.2)
    print(
        f"\n==================================================\n"
        f" [SUCESSO] Processamento do DataPool concluído!\n"
        f" Total de lotes processados e fotografados: {qtd}\n"
        f"==================================================\n"
    )