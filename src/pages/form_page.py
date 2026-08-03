"""
src/pages/form_page.py
Page Object do formulario web de inspecao de lotes.
"""

from src.mapeamento_web import mapear_categoria_produto, preparar_status_inspecao


class FormPagePlaywright:
    def __init__(self, page, delay_passo=0):
        self.page = page
        self.delay_passo = delay_passo

        self._lote = "#lote"
        self._produto = "#produto"
        self._codigo_produto = "#codigo_produto"
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
        codigo_produto = str(dados_lote.get("produto") or "").strip()
        categoria_produto = mapear_categoria_produto(codigo_produto)
        status = preparar_status_inspecao(dados_lote.get("status"))

        self.page.locator(self._lote).fill(valor_lote)
        self.page.locator(self._codigo_produto).evaluate(
            """
            (campo, codigo) => {
                campo.value = codigo;
                campo.dispatchEvent(new Event('input', { bubbles: true }));
            }
            """,
            codigo_produto,
        )
        self.page.locator(self._produto).select_option(categoria_produto)
        self.page.evaluate(
            """
            (status) => {
                const form = document.getElementById('formLote');
                const aviso = document.getElementById('statusAviso');
                document.querySelectorAll('input[name="status"]').forEach(
                    (radio) => { radio.checked = false; }
                );

                form.dataset.statusValido = String(status.valido);

                if (!status.valido) {
                    aviso.textContent = `Status recebido: ${status.original || '(vazio)'} — revisao humana necessaria (RN06).`;
                    aviso.hidden = false;
                    return;
                }

                const radio = document.querySelector(
                    `input[name="status"][value="${status.normalizado}"]`
                );
                radio.checked = true;

                if (status.foi_normalizado) {
                    aviso.textContent = `RN05: ${status.original} normalizado para ${status.normalizado}.`;
                    aviso.hidden = false;
                } else {
                    aviso.textContent = '';
                    aviso.hidden = true;
                }
            }
            """,
            status,
        )

    def submeter_e_aguardar(self, timeout=5000):
        """Submete o formulario e aguarda a mensagem de resultado."""
        if self.page.locator("#formLote").get_attribute("data-status-valido") == "false":
            return False

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
        codigo_produto = str(dados_lote.get("produto") or "").strip()
        categoria_produto = mapear_categoria_produto(codigo_produto)
        status = preparar_status_inspecao(dados_lote.get("status"))

        campo_lote = self.wait.until(EC.element_to_be_clickable((By.ID, "lote")))
        campo_lote.clear()
        campo_lote.send_keys(valor_lote)

        campo_codigo = self.wait.until(
            EC.presence_of_element_located((By.ID, "codigo_produto"))
        )
        self.driver.execute_script(
            """
            const campo = arguments[0];
            const codigo = arguments[1];
            campo.value = codigo;
            campo.dispatchEvent(new Event('input', { bubbles: true }));
            """,
            campo_codigo,
            codigo_produto,
        )

        from selenium.webdriver.support.ui import Select

        select_produto = self.wait.until(
            EC.element_to_be_clickable((By.ID, "produto"))
        )
        Select(select_produto).select_by_value(categoria_produto)

        self.driver.execute_script(
            """
            const status = arguments[0];
            const form = document.getElementById('formLote');
            const aviso = document.getElementById('statusAviso');
            document.querySelectorAll('input[name="status"]').forEach(
                (radio) => { radio.checked = false; }
            );

            form.dataset.statusValido = String(status.valido);

            if (!status.valido) {
                aviso.textContent = `Status recebido: ${status.original || '(vazio)'} — revisao humana necessaria (RN06).`;
                aviso.hidden = false;
                return;
            }

            const radio = document.querySelector(
                `input[name="status"][value="${status.normalizado}"]`
            );
            radio.checked = true;

            if (status.foi_normalizado) {
                aviso.textContent = `RN05: ${status.original} normalizado para ${status.normalizado}.`;
                aviso.hidden = false;
            } else {
                aviso.textContent = '';
                aviso.hidden = true;
            }
            """,
            status,
        )

    def submeter_e_aguardar(self, timeout=5):
        """Submete o formulario e aguarda a mensagem de resultado."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC

        form = self.driver.find_element(By.ID, "formLote")
        if form.get_attribute("data-status-valido") == "false":
            return False

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
