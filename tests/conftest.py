from pathlib import Path

import pytest

from src.pages.form_page import FormPagePlaywright


@pytest.fixture
def pagina_lotes_url():
    """URL local da tela simulada usada nos testes E2E."""
    caminho = Path(__file__).resolve().parent.parent / "doc.html"
    if not caminho.exists():
        pytest.skip("doc.html nao encontrado para execucao E2E.")
    return caminho.resolve().as_uri()


@pytest.fixture
def formulario_page(page, pagina_lotes_url):
    """Abre o formulario e retorna o Page Object."""
    page.goto(pagina_lotes_url)
    return FormPagePlaywright(page)
