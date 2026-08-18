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
        self.campo_lote = page.get_by_test_id("input-lote")
        self.campo_codigo_produto = page.get_by_test_id("input-codigo-produto")
        self.campo_produto = page.get_by_test_id("select-produto")
        self.campo_linha = page.get_by_test_id("input-linha")
        self.campo_turno = page.get_by_test_id("input-turno")
        self.campo_responsavel = page.get_by_test_id("input-responsavel")
        self.campo_data = page.get_by_test_id("input-data")
        self.campo_observacao = page.get_by_test_id("input-observacao")
        self.botao_validar = page.get_by_test_id("btn-submit")
        self.alerta_sucesso = page.get_by_test_id("alert-success")

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
        if not isinstance(dados_lote, dict):
            self.campo_lote.fill(str(dados_lote or ""))
            return

        dados_lote = dados_lote or {}
        valor_lote = str(dados_lote.get("lote") or dados_lote.get("lote_id") or "")
        codigo_produto = str(dados_lote.get("produto") or "").strip()
        status = preparar_status_inspecao(dados_lote.get("status"))

        self.page.locator(self._lote).fill(valor_lote)
        self.preencher_codigo_produto(codigo_produto)
        self.preencher_campo_texto(self.campo_linha, dados_lote.get("linha"))
        self.preencher_campo_texto(self.campo_turno, dados_lote.get("turno"))
        self.preencher_campo_texto(self.campo_responsavel, dados_lote.get("responsavel"))
        self.preencher_campo_texto(self.campo_data, dados_lote.get("data"))
        self.preencher_campo_texto(self.campo_observacao, dados_lote.get("observacao"))
        try:
            self.page.locator(self._produto).select_option(
                mapear_categoria_produto(codigo_produto)
            )
        except ValueError:
            self.page.locator(self._produto).evaluate(
                """
                (campo) => {
                    campo.value = '';
                    campo.dispatchEvent(new Event('change', { bubbles: true }));
                }
                """
            )
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

    def preencher_codigo_produto(self, codigo_produto):
        """Preenche o codigo original do produto."""
        self.preencher_campo_texto(self.campo_codigo_produto, codigo_produto)

    def preencher_campo_texto(self, campo, valor):
        """Preenche campos de texto usados para espelhar a linha da planilha."""
        campo.fill(str(valor or ""))

    def selecionar_produto(self, produto):
        """Seleciona a categoria do produto no formulario."""
        produto = str(produto or "").strip().upper()
        if produto not in {"TV", "MON", "AC"}:
            categoria = mapear_categoria_produto(produto)
            codigo = produto
        else:
            categoria = produto
            codigo = produto

        if not self.campo_codigo_produto.input_value():
            self.preencher_codigo_produto(codigo)

        self.campo_produto.select_option(categoria)

    def selecionar_status(self, status):
        """Seleciona o status da inspecao e sinaliza RN06 quando vier invalido."""
        status = preparar_status_inspecao(status) if not isinstance(status, dict) else status
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
                    aviso.textContent = `Status recebido: ${status.original || '(vazio)'} - revisao humana necessaria (RN06).`;
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

    def obter_status_selecionado(self):
        """Retorna o status marcado no formulario."""
        return self.page.locator('input[name="status"]:checked').get_attribute("value")

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

    def submeter(self):
        """Aciona o botao de envio sem aguardar regra de sucesso."""
        self.botao_validar.click()

    def mensagem_sucesso_visivel(self):
        """Indica se a mensagem de sucesso esta visivel."""
        return self.alerta_sucesso.is_visible()

    def capturar_evidencia(self, caminho):
        """Captura screenshot full page pelo Page Object."""
        self.preparar_evidencia_visual()
        self.page.screenshot(path=str(caminho), full_page=True)

    def preparar_evidencia_visual(self):
        """Prepara a tela para o screenshot de evidencia, se a pagina suportar."""
        self.page.evaluate("window.prepararEvidenciaVisual && window.prepararEvidenciaVisual()")

    def registrar_analises(self, analises, dados_lote, linha_planilha=None):
        """Registra na tela as ocorrencias geradas pelo bot.py."""
        self.page.evaluate(
            """
            (payload) => {
                window.registrarAnalisesFormulario
                    && window.registrarAnalisesFormulario(payload);
            }
            """,
            _payload_analise(analises, dados_lote, linha_planilha),
        )


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
        valor_lote = str(dados_lote.get("lote") or dados_lote.get("lote_id") or "")
        codigo_produto = str(dados_lote.get("produto") or "").strip()
        status = preparar_status_inspecao(dados_lote.get("status"))

        campo_lote = self.wait.until(EC.element_to_be_clickable((By.ID, "lote")))
        campo_lote.clear()
        campo_lote.send_keys(valor_lote)

        self._preencher_campo_texto("codigo_produto", codigo_produto)
        self._preencher_campo_texto("linha_producao", dados_lote.get("linha"))
        self._preencher_campo_texto("turno", dados_lote.get("turno"))
        self._preencher_campo_texto(
            "responsavel",
            dados_lote.get("responsavel"),
        )
        self._preencher_campo_texto("data_inspecao", dados_lote.get("data"))
        self._preencher_campo_texto("observacao", dados_lote.get("observacao"))

        from selenium.webdriver.support.ui import Select

        select_produto = self.wait.until(EC.element_to_be_clickable((By.ID, "produto")))
        try:
            Select(select_produto).select_by_value(mapear_categoria_produto(codigo_produto))
        except ValueError:
            self.driver.execute_script(
                """
                const campo = arguments[0];
                campo.value = '';
                campo.dispatchEvent(new Event('change', { bubbles: true }));
                """,
                select_produto,
            )

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

    def _preencher_campo_texto(self, campo_id, valor):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC

        campo = self.wait.until(EC.element_to_be_clickable((By.ID, campo_id)))
        campo.clear()
        campo.send_keys(str(valor or ""))

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
        largura, altura = self.driver.execute_script(
            """
            return [
                Math.max(document.body.scrollWidth, document.documentElement.scrollWidth, 1280),
                Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, 900)
            ];
            """
        )
        self.driver.set_window_size(largura, altura)

    def registrar_analises(self, analises, dados_lote, linha_planilha=None):
        """Registra na tela as ocorrencias geradas pelo bot.py."""
        self.driver.execute_script(
            """
            const payload = arguments[0];
            window.registrarAnalisesFormulario
                && window.registrarAnalisesFormulario(payload);
            """,
            _payload_analise(analises, dados_lote, linha_planilha),
        )


def _payload_analise(analises, dados_lote, linha_planilha=None):
    dados_lote = dados_lote or {}
    return {
        "linha_planilha": linha_planilha or dados_lote.get("linha_planilha") or "",
        "lote_id": dados_lote.get("lote_id") or dados_lote.get("lote") or "",
        "analises": analises or [],
    }
