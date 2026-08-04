from src.pages.form_page import FormPagePlaywright
from src.mapeamento_web import mapear_categoria_produto


class PlaywrightFormularioLotesPage(FormPagePlaywright):
    """Compatibilidade entre o formulario de revisao e o fluxo atual."""

    def __init__(self, page, pagina_html, delay_passo=0):
        super().__init__(page, delay_passo=delay_passo)
        self.pagina_html = pagina_html

    def abrir(self):
        """Abre a pagina HTML indicada pela fixture e aguarda o formulario."""
        self.page.goto(self.pagina_html)
        self.page.get_by_test_id("input-lote").wait_for(state="visible")
        return self

    def preencher_lote(self, dados_lote):
        """Preenche o lote usando ``fill`` pela implementacao principal."""
        if isinstance(dados_lote, dict):
            return super().preencher_lote(dados_lote)
        self.campo_lote.fill(str(dados_lote or ""))

    def selecionar_produto(self, produto):
        """Seleciona o ``value`` da opcao pela implementacao principal."""
        produto = str(produto or "").strip().upper()
        categoria = (
            produto
            if produto in {"TV", "MON", "AC"}
            else mapear_categoria_produto(produto)
        )
        if not self.campo_codigo_produto.input_value():
            self.preencher_codigo_produto(produto)
        self.campo_produto.select_option(value=categoria)

    def selecionar_status(self, status):
        """Aplica a normalizacao atual e confirma o radio com ``click``."""
        super().selecionar_status(status)
        radio = self.page.locator('input[name="status"]:checked')
        if radio.count():
            radio.click()

    def mensagem_sucesso_visivel(self):
        """Retorna ``bool`` indicando se a mensagem de sucesso esta visivel."""
        return bool(self.alerta_sucesso.is_visible())

    def capturar_evidencia(self, caminho):
        """Captura a evidencia usando ``page.screenshot``."""
        self.preparar_evidencia_visual()
        self.page.screenshot(path=str(caminho), full_page=True)
