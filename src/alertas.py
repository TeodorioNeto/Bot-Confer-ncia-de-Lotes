"""Alertas resilientes: Telegram principal, Email e log como fallback."""

from __future__ import annotations

import json
import smtplib
import ssl
from dataclasses import asdict, dataclass
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ResultadoAlerta:
    severidade: str
    canais_enviados: tuple[str, ...]
    canal_fallback: str | None
    sucesso: bool

    def to_dict(self) -> dict:
        result = asdict(self)
        result["canais_enviados"] = list(self.canais_enviados)
        return result


class SistemaAlertas:
    """Envia alertas sem propagar falhas de canal ao pipeline."""

    def __init__(
        self,
        *,
        telegram_token: str = "",
        telegram_chat_id: str = "",
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_username: str = "",
        smtp_password: str = "",
        smtp_from: str = "",
        email_to: str = "",
        smtp_use_tls: bool = True,
        timeout_seconds: float = 5.0,
        telegram_sender=None,
        email_sender=None,
        logger=None,
    ):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_from = smtp_from or smtp_username
        self.email_to = email_to
        self.smtp_use_tls = smtp_use_tls
        self.timeout_seconds = timeout_seconds
        self.telegram_sender = telegram_sender or self._send_telegram
        self.email_sender = email_sender or self._send_email
        self.logger = logger

    def send(
        self,
        *,
        severity: str,
        title: str,
        message: str,
        attachment=None,
    ) -> ResultadoAlerta:
        severity = str(severity).upper()
        sent_channels = []

        telegram_ok = self._safe_send(
            "telegram",
            lambda: self.telegram_sender(title, message),
        )
        if telegram_ok:
            sent_channels.append("telegram")

        # Eventos graves chegam aos dois canais. Para INFO/AVISO, o Email e
        # usado somente quando o Telegram falha.
        must_send_email = severity in {"ERRO", "ERROR", "CRITICO", "CRITICAL"}
        if must_send_email or not telegram_ok:
            email_ok = self._safe_send(
                "email",
                lambda: self.email_sender(title, message, attachment),
            )
            if email_ok:
                sent_channels.append("email")

        if sent_channels:
            fallback_channel = "email" if not telegram_ok and "email" in sent_channels else None
            return ResultadoAlerta(
                severidade=severity,
                canais_enviados=tuple(sent_channels),
                canal_fallback=fallback_channel,
                sucesso=True,
            )

        self._log_local(severity, title, message)
        return ResultadoAlerta(
            severidade=severity,
            canais_enviados=("log_local",),
            canal_fallback="log_local",
            sucesso=True,
        )

    def _safe_send(self, channel: str, operation) -> bool:
        try:
            return bool(operation())
        except Exception as error:
            if self.logger is not None:
                self.logger.error(
                    "Canal de alerta %s indisponivel: %s",
                    channel,
                    error,
                )
            return False

    def _send_telegram(self, title: str, message: str) -> bool:
        if not self.telegram_token or not self.telegram_chat_id:
            return False
        endpoint = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        body = urlencode(
            {
                "chat_id": self.telegram_chat_id,
                "text": f"{title}\n\n{message}",
            }
        ).encode("utf-8")
        request = Request(endpoint, data=body, method="POST")
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status < 400 and bool(payload.get("ok"))

    def _send_email(self, title: str, message: str, attachment=None) -> bool:
        if not self.smtp_host or not self.smtp_from or not self.email_to:
            return False

        email = EmailMessage()
        email["Subject"] = title
        email["From"] = self.smtp_from
        email["To"] = self.email_to
        email.set_content(message)

        if attachment:
            attachment_path = Path(attachment)
            if attachment_path.exists():
                email.add_attachment(
                    attachment_path.read_bytes(),
                    maintype="application",
                    subtype="octet-stream",
                    filename=attachment_path.name,
                )

        with smtplib.SMTP(
            self.smtp_host,
            self.smtp_port,
            timeout=self.timeout_seconds,
        ) as smtp:
            if self.smtp_use_tls:
                smtp.starttls(context=ssl.create_default_context())
            if self.smtp_username:
                smtp.login(self.smtp_username, self.smtp_password)
            smtp.send_message(email)
        return True

    def _log_local(self, severity: str, title: str, message: str) -> None:
        if self.logger is None:
            return
        log_method = (
            self.logger.critical
            if severity in {"CRITICO", "CRITICAL"}
            else self.logger.error
            if severity in {"ERRO", "ERROR"}
            else self.logger.warning
        )
        log_method("ALERTA_LOCAL | %s | %s", title, message)
