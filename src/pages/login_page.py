"""
src/pages/login_page.py
Page Object para autenticacao na aplicacao (Playwright e Selenium).
"""

class LoginPagePlaywright:
    def __init__(self, page, delay_passo=0):
        self.page = page
        self.delay_passo = delay_passo

        self._usuario = "#usuario"
        self._senha = "#senha"
        self._btn_login = "#btn-login"

    def fazer_login(self, usuario=None, senha=None):
        """Realiza o login caso a tela de autenticacao exista na pagina."""
        if self.page.locator(self._usuario).is_visible():
            if usuario is None or senha is None:
                raise ValueError("Credenciais de login devem ser informadas.")

            self.page.locator(self._usuario).fill(usuario)
            self.page.locator(self._senha).fill(senha)
            self.page.locator(self._btn_login).click()


class LoginPageSelenium:
    def __init__(self, driver, wait, delay_passo=0):
        self.driver = driver
        self.wait = wait
        self.delay_passo = delay_passo

    def fazer_login(self, usuario=None, senha=None):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC

        elementos = self.driver.find_elements(By.ID, "usuario")
        if elementos and elementos[0].is_displayed():
            if usuario is None or senha is None:
                raise ValueError("Credenciais de login devem ser informadas.")

            elem_usr = self.wait.until(EC.element_to_be_clickable((By.ID, "usuario")))
            elem_usr.clear()
            elem_usr.send_keys(usuario)

            elem_pass = self.wait.until(EC.element_to_be_clickable((By.ID, "senha")))
            elem_pass.clear()
            elem_pass.send_keys(senha)

            self.wait.until(EC.element_to_be_clickable((By.ID, "btn-login"))).click()
