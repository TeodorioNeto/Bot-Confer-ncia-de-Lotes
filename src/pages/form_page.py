"""
src/pages/form_page.py
Page Object do formulario web de inspecao de lotes.
"""


class FormPagePlaywright:
    def __init__(self, page, delay_passo=0):
        self.page = page
        self.delay_passo = delay_passo

        self._lote = "#lote"
        self._produto = "#produto"
        self._btn_submit = "button.btn-submit"
        self._alert_success = "#alertSuccess"

    def aplicar_tema(self, theme):
        """Aplica o tema visual da tela simulada."""
        if theme != "light":
            return

        self.page.evaluate("""
            document.documentElement.setAttribute('data-theme', 'light');
            const toggle = document.getElementById('themeToggle');
            if (toggle) toggle.checked = true;
        """)

    def resetar_formulario(self):
        """Limpa o formulario antes de preencher o proximo lote."""
        self.page.evaluate("document.getElementById('formLote').reset()")

    def preencher_lote(self, dados_lote):
        """Preenche o formulario usando os dados do item atual."""
        dados_lote = dados_lote or {}
        valor_lote = str(dados_lote.get("lote") or dados_lote.get("lote_id") or "LOTE-2026-0001")
        valor_produto = str(dados_lote.get("produto") or "Produto nao informado")
        valor_status = str(dados_lote.get("status") or "PENDENTE")

        self.page.locator(self._lote).fill(valor_lote)
        self.page.evaluate(
            """
            (valorProduto) => {
                const select = document.getElementById('produto');
                let option = Array.from(select.options).find((item) => item.value === valorProduto);
                if (!option) {
                    option = new Option(valorProduto, valorProduto);
                    select.add(option);
                }
                select.value = valorProduto;
                select.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """,
            valor_produto,
        )
        self.page.evaluate(
            """
            (valorStatus) => {
                let radio = Array.from(
                    document.querySelectorAll('input[name="status"]')
                ).find((item) => item.value === valorStatus);
                if (!radio) {
                    radio = document.createElement('input');
                    radio.type = 'radio';
                    radio.name = 'status';
                    radio.value = valorStatus;
                    radio.style.display = 'none';
                    document.getElementById('formLote').appendChild(radio);
                }
                radio.checked = true;
                radio.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """,
            valor_status,
        )

    def submeter_e_aguardar(self, timeout=5000):
        """Submete o formulario e aguarda a mensagem de resultado."""
        self.page.locator(self._btn_submit).click()
        try:
            self.page.locator(self._alert_success).wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    def is_sucesso(self):
        return self.page.locator(self._alert_success).is_visible()

    def preparar_evidencia_visual(self):
        """Prepara a tela para o screenshot de evidencia, se a pagina suportar."""
        self.page.evaluate("window.prepararEvidenciaVisual && window.prepararEvidenciaVisual()")

    def registrar_analises(self, analises, dados_lote, linha_planilha=None):
        pass


class FormPageSelenium:
    def __init__(self, driver, wait, delay_passo=0):
        self.driver = driver
        self.wait = wait
        self.delay_passo = delay_passo

    def aplicar_tema(self, theme):
        """Aplica o tema visual da tela simulada."""
        if theme != "light":
            return

        self.driver.execute_script("""
            document.documentElement.setAttribute('data-theme', 'light');
            const toggle = document.getElementById('themeToggle');
            if (toggle) toggle.checked = true;
        """)

    def resetar_formulario(self):
        """Limpa o formulario antes de preencher o proximo lote."""
        self.driver.execute_script("document.getElementById('formLote').reset();")

    def preencher_lote(self, dados_lote):
        """Preenche o formulario usando os dados do item atual."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC

        dados_lote = dados_lote or {}
        valor_lote = str(dados_lote.get("lote") or dados_lote.get("lote_id") or "LOTE-2026-0001")
        valor_produto = str(dados_lote.get("produto") or "Produto nao informado")
        valor_status = str(dados_lote.get("status") or "PENDENTE")

        campo_lote = self.wait.until(EC.element_to_be_clickable((By.ID, "lote")))
        campo_lote.clear()
        campo_lote.send_keys(valor_lote)

        self.driver.execute_script(
            """
            const valorProduto = arguments[0];
            const select = document.getElementById('produto');
            let option = Array.from(select.options).find((item) => item.value === valorProduto);
            if (!option) {
                option = new Option(valorProduto, valorProduto);
                select.add(option);
            }
            select.value = valorProduto;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            valor_produto,
        )
        self.driver.execute_script(
            """
            const valorStatus = arguments[0];
            let radio = Array.from(
                document.querySelectorAll('input[name="status"]')
            ).find((item) => item.value === valorStatus);
            if (!radio) {
                radio = document.createElement('input');
                radio.type = 'radio';
                radio.name = 'status';
                radio.value = valorStatus;
                radio.style.display = 'none';
                document.getElementById('formLote').appendChild(radio);
            }
            radio.checked = true;
            radio.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            valor_status,
        )

    def submeter_e_aguardar(self, timeout=5):
        """Submete o formulario e aguarda a mensagem de resultado."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC

        btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-submit")))
        btn.click()

        try:
            self.wait.until(EC.visibility_of_element_located((By.ID, "alertSuccess")))
            return True
        except Exception:
            return False

    def is_sucesso(self):
        from selenium.webdriver.common.by import By

        elementos = self.driver.find_elements(By.ID, "alertSuccess")
        return len(elementos) > 0 and elementos[0].is_displayed()

    def preparar_evidencia_visual(self):
        """Prepara a tela para o screenshot de evidencia, se a pagina suportar."""
        self.driver.execute_script("window.prepararEvidenciaVisual && window.prepararEvidenciaVisual()")

    def registrar_analises(self, analises, dados_lote, linha_planilha=None):
        pass
