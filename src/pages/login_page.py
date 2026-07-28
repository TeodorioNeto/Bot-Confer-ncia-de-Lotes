"""
src/pages/login_page.py
Page Object para autenticação na aplicação (Playwright e Selenium).
"""

import time


class LoginPagePlaywright:

    def __init__(self, page, delay_passo=0.5):
        self.page = page
        self.delay_passo = delay_passo

        # Locators
        self._usuario = "#usuario"
        self._senha = "#senha"
        self._btn_login = "#btn-login"

    def fazer_login(self, usuario="admin", senha="123"):
        """Realiza o login caso a tela de autenticação exista na página."""
        if self.page.locator(self._usuario).is_visible():
            self.page.locator(self._usuario).fill(usuario)
            if self.delay_passo:
                time.sleep(self.delay_passo)

            self.page.locator(self._senha).fill(senha)
            if self.delay_passo:
                time.sleep(self.delay_passo)

            self.page.locator(self._btn_login).click()
            if self.delay_passo:
                time.sleep(self.delay_passo)


class LoginPageSelenium:

    def __init__(self, driver, wait, delay_passo=0.5):
        self.driver = driver
        self.wait = wait
        self.delay_passo = delay_passo

    def fazer_login(self, usuario="admin", senha="123"):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC

        elementos = self.driver.find_elements(By.ID, "usuario")
        if elementos and elementos[0].is_displayed():
            elem_usr = self.wait.until(EC.element_to_be_clickable((By.ID, "usuario")))
            elem_usr.clear()
            elem_usr.send_keys(usuario)

            elem_pass = self.wait.until(EC.element_to_be_clickable((By.ID, "senha")))
            elem_pass.clear()
            elem_pass.send_keys(senha)

            self.wait.until(EC.element_to_be_clickable((By.ID, "btn-login"))).click()

def is_sucesso(self) -> bool:
        """Valida se a mensagem final de sucesso está visível na tela."""
        return self.page.locator(self._alert_success).is_visible()