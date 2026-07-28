"""
src/pages/form_page.py
Page Object para o formulário de Cadastro de Lotes de Produção (doc.html).
Aplicações em Playwright e Selenium.
"""

import time


class FormPagePlaywright:

    def __init__(self, page, delay_passo=0.3):
        self.page = page
        self.delay_passo = delay_passo

        # Locators do formulário doc.html
        self._lote = "#lote"
        self._produto = "#produto"
        self._btn_submit = "button.btn-submit"
        self._alert_success = "#alertSuccess"
        self._alert_message = "#alertMessage"

    def preencher_lote(self, dados_lote: dict):
        """Preenche o formulário limpando os campos anteriores."""
        dados_lote = dados_lote or {}

        # 1. Lote (força a limpeza antes de digitar)
        valor_lote = str(dados_lote.get("lote") or dados_lote.get("lote_id") or "LOTE-2026-0001")
        campo_lote = self.page.locator(self._lote)
        campo_lote.fill("")
        campo_lote.fill(valor_lote)
        if self.delay_passo:
            time.sleep(self.delay_passo)

        # 2. Produto (Select)
        valor_produto = str(dados_lote.get("produto") or "Placa Mãe V1")
        self.page.locator(self._produto).select_option(label=valor_produto)
        if self.delay_passo:
            time.sleep(self.delay_passo)

        # 3. Status (Radio Button)
        valor_status = str(dados_lote.get("status") or "Pendente")
        radio_locator = f'input[name="status"][value="{valor_status}"]'
        self.page.locator(radio_locator).check()
        if self.delay_passo:
            time.sleep(self.delay_passo)

    def submeter_e_aguardar(self, timeout=5000) -> bool:
        """Clica no botão Processar Lote e aguarda a caixa de sucesso."""
        self.page.locator(self._btn_submit).click()
        try:
            self.page.locator(self._alert_success).wait_for(state="visible", timeout=timeout)
            if self.delay_passo:
                time.sleep(self.delay_passo)
            return True
        except Exception:
            return False

    def is_sucesso(self) -> bool:
        return self.page.locator(self._alert_success).is_visible()

    def registrar_analises(self, analises: list, dados_lote: dict, linha_planilha=None):
        pass


class FormPageSelenium:

    def __init__(self, driver, wait, delay_passo=0.3):
        self.driver = driver
        self.wait = wait
        self.delay_passo = delay_passo

    def preencher_lote(self, dados_lote: dict):
        """Preenche o formulário no Chrome utilizando Selenium WebDriver."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import Select

        dados_lote = dados_lote or {}

        # 1. Número do Lote
        valor_lote = str(dados_lote.get("lote") or dados_lote.get("lote_id") or "LOTE-2026-0001")
        campo_lote = self.wait.until(EC.element_to_be_clickable((By.ID, "lote")))
        campo_lote.clear()
        campo_lote.send_keys(valor_lote)
        if self.delay_passo:
            time.sleep(self.delay_passo)

        # 2. Produto (Select)
        valor_produto = str(dados_lote.get("produto") or "Placa Mãe V1")
        select_prod = Select(self.wait.until(EC.element_to_be_clickable((By.ID, "produto"))))
        select_prod.select_by_visible_text(valor_produto)
        if self.delay_passo:
            time.sleep(self.delay_passo)

        # 3. Status (Radio Button)
        valor_status = str(dados_lote.get("status") or "Pendente")
        radio_xpath = f'//input[@name="status"][@value="{valor_status}"]'
        radio_elem = self.wait.until(EC.element_to_be_clickable((By.XPATH, radio_xpath)))
        radio_elem.click()
        if self.delay_passo:
            time.sleep(self.delay_passo)

    def submeter_e_aguardar(self, timeout=5) -> bool:
        """Clica no botão de envio e aguarda a mensagem de sucesso ficar visível."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC

        btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-submit")))
        btn.click()

        try:
            self.wait.until(EC.visibility_of_element_located((By.ID, "alertSuccess")))
            if self.delay_passo:
                time.sleep(self.delay_passo)
            return True
        except Exception:
            return False

    def is_sucesso(self) -> bool:
        from selenium.webdriver.common.by import By
        elementos = self.driver.find_elements(By.ID, "alertSuccess")
        return len(elementos) > 0 and elementos[0].is_displayed()

    def registrar_analises(self, analises: list, dados_lote: dict, linha_planilha=None):
        pass