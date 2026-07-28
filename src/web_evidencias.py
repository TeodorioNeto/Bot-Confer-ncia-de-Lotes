import re
from datetime import datetime
from pathlib import Path

from config import BASE_DIR, LOGS_DIR, WEB_AUTOMATION_URL


SCREENSHOTS_DIR = LOGS_DIR / "screenshots"


def montar_caminho_screenshot(dados_lote, driver, screenshot_path=None):
    """Monta um caminho padronizado para a evidencia visual do item."""
    if screenshot_path:
        caminho = Path(screenshot_path)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        return caminho

    pasta_driver = SCREENSHOTS_DIR / _nome_seguro(driver)
    pasta_driver.mkdir(parents=True, exist_ok=True)
    lote_id = _nome_seguro(dados_lote.get("lote_id") or "lote-sem-id")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return pasta_driver / f"{timestamp}_{driver}_{lote_id}.png"


def _nome_seguro(valor):
    texto = str(valor).strip()
    texto = re.sub(r"[^A-Za-z0-9_.-]+", "_", texto)
    return texto[:80] or "lote-sem-id"


def obter_url_automacao():
    """Retorna a URL da tela web; usa o simulador apenas como fallback local."""
    if WEB_AUTOMATION_URL:
        return WEB_AUTOMATION_URL

    return (BASE_DIR / "simulador_inspecao_lotes.html").resolve().as_uri()
