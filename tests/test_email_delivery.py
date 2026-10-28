"""Contrato de envio transacional sem acesso real à rede."""
import smtplib

import pytest

from app.services.email_delivery import send_transactional_email


def _send(**kwargs):
    data = {
        "to_email": "cliente@example.com",
        "subject": "Agendamento IDDUN",
        "text_body": "Reserva confirmada",
    }
    data.update(kwargs)
    return send_transactional_email(**data)


class RecordingSMTP:
    instances = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.events = []
        self.message = None
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def starttls(self):
        self.events.append("tls")

    def login(self, username, password):
        self.events.append(("login", username, password))

    def send_message(self, message):
        self.events.append("send")
        self.message = message


def test_disabled_email_does_not_contact_provider(app, monkeypatch, caplog):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("SMTP must not be opened in disabled mode")

    monkeypatch.setattr(smtplib, "SMTP", fail_if_called)
    with app.app_context():
        app.config["EMAIL_BACKEND"] = "disabled"
        assert _send() is False
        assert "Transactional email disabled" in caplog.text


def test_console_email_does_not_contact_provider(app, monkeypatch, caplog):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Console mode must not open SMTP")

    monkeypatch.setattr(smtplib, "SMTP", fail_if_called)
    with app.app_context():
        app.config["EMAIL_BACKEND"] = "console"
        with caplog.at_level("INFO"):
            assert _send() is True
        assert "Reserva confirmada" in caplog.text


def test_smtp_with_tls_auth_and_html_sends_expected_message(app, monkeypatch):
    RecordingSMTP.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", RecordingSMTP)
    with app.app_context():
        app.config.update(
            EMAIL_BACKEND="smtp",
            EMAIL_FROM="noreply@iddun.example",
            SMTP_HOST="smtp.example",
            SMTP_PORT=2525,
            SMTP_USERNAME="mail-user",
            SMTP_PASSWORD="dummy-password",
            SMTP_USE_TLS=True,
        )
        assert _send(html_body="<p>Reserva confirmada</p>") is True

    smtp = RecordingSMTP.instances[-1]
    assert (smtp.host, smtp.port, smtp.timeout) == ("smtp.example", 2525, 15)
    assert smtp.events == ["tls", ("login", "mail-user", "dummy-password"), "send"]
    assert smtp.message["From"] == "noreply@iddun.example"
    assert smtp.message["To"] == "cliente@example.com"
    assert smtp.message["Subject"] == "Agendamento IDDUN"
    assert smtp.message.get_body(preferencelist=("plain",)).get_content().strip() == (
        "Reserva confirmada"
    )
    assert smtp.message.get_body(preferencelist=("html",)).get_content().strip() == (
        "<p>Reserva confirmada</p>"
    )


@pytest.mark.parametrize("tls_option", [False, "false", "0", "no"])
def test_smtp_without_tls_or_username_skips_auth(app, monkeypatch, tls_option):
    RecordingSMTP.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", RecordingSMTP)
    with app.app_context():
        app.config.update(
            EMAIL_BACKEND="smtp",
            EMAIL_FROM="noreply@iddun.example",
            SMTP_HOST="smtp.example",
            SMTP_USE_TLS=tls_option,
            SMTP_USERNAME=None,
            SMTP_PASSWORD=None,
        )
        assert _send() is True
    assert RecordingSMTP.instances[-1].events == ["send"]


def test_missing_smtp_configuration_returns_false_without_network(app, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("No connection expected for incomplete configuration")

    monkeypatch.setattr(smtplib, "SMTP", fail_if_called)
    with app.app_context():
        app.config.update(
            EMAIL_BACKEND="smtp",
            SMTP_HOST=None,
            EMAIL_FROM=None,
        )
        assert _send() is False


@pytest.mark.parametrize("error", [OSError("no route"), smtplib.SMTPException("server down")])
def test_smtp_transport_errors_are_contained(app, monkeypatch, error):
    class FailedSMTP:
        def __init__(self, *args, **kwargs):
            raise error

    monkeypatch.setattr(smtplib, "SMTP", FailedSMTP)
    with app.app_context():
        app.config.update(
            EMAIL_BACKEND="smtp",
            EMAIL_FROM="noreply@iddun.example",
            SMTP_HOST="smtp.example",
        )
        assert _send() is False


def test_unknown_email_backend_fails_explicitly(app):
    with app.app_context():
        app.config["EMAIL_BACKEND"] = "unknown-backend"
        with pytest.raises(RuntimeError, match="EMAIL_BACKEND inválido"):
            _send()
