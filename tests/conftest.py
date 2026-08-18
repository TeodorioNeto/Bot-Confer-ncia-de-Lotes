from pathlib import Path

import pytest

from src.pages.formulario_lotes_page import PlaywrightFormularioLotesPage


@pytest.fixture
def pagina_html():
    """URL da entrada HTML exigida pelo exercicio 19-X."""
    caminho = Path(__file__).resolve().parent.parent / "web" / "lote-teste.html"
    if not caminho.exists():
        pytest.skip("web/lote-teste.html nao encontrado para execucao E2E.")
    return caminho.resolve().as_uri()


@pytest.fixture
def pagina_lotes_url(pagina_html):
    """Alias mantido para compatibilidade com os testes existentes."""
    return pagina_html


@pytest.fixture
def formulario_page(page, pagina_html):
    """Instancia e abre o Page Object solicitado no formulario."""
    po = PlaywrightFormularioLotesPage(page, pagina_html)
    po.abrir()
    return po
