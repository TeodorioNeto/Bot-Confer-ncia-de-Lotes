from src.alertas import SistemaAlertas


class FakeLogger:
    def __init__(self):
        self.records = []

    def error(self, message, *args):
        self.records.append(("error", message % args))

    def warning(self, message, *args):
        self.records.append(("warning", message % args))

    def critical(self, message, *args):
        self.records.append(("critical", message % args))


def test_telegram_e_canal_principal_para_aviso():
    email_calls = []
    system = SistemaAlertas(
        telegram_sender=lambda title, message: True,
        email_sender=lambda title, message, attachment: email_calls.append(title),
    )

    result = system.send(severity="AVISO", title="Teste", message="Mensagem")

    assert result.canais_enviados == ("telegram",)
    assert email_calls == []


def test_email_recebe_alerta_quando_telegram_falha():
    system = SistemaAlertas(
        telegram_sender=lambda title, message: False,
        email_sender=lambda title, message, attachment: True,
    )

    result = system.send(severity="AVISO", title="Teste", message="Mensagem")

    assert result.canais_enviados == ("email",)
    assert result.canal_fallback == "email"


def test_evento_critico_e_enviado_a_telegram_e_email():
    system = SistemaAlertas(
        telegram_sender=lambda title, message: True,
        email_sender=lambda title, message, attachment: True,
    )

    result = system.send(severity="CRITICO", title="Teste", message="Mensagem")

    assert result.canais_enviados == ("telegram", "email")


def test_log_local_e_ultimo_fallback_de_canal():
    logger = FakeLogger()
    system = SistemaAlertas(
        telegram_sender=lambda title, message: False,
        email_sender=lambda title, message, attachment: False,
        logger=logger,
    )

    result = system.send(severity="ERRO", title="Teste", message="Mensagem")

    assert result.canais_enviados == ("log_local",)
    assert result.canal_fallback == "log_local"
    assert any("ALERTA_LOCAL" in message for _, message in logger.records)
