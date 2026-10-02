"""Entrega de e-mails transacionais sem acoplamento a fornecedor."""

import smtplib
from email.message import EmailMessage

from flask import current_app


def _bool_config(
    name,
    default=False,
):
    value = current_app.config.get(
        name,
        default,
    )

    if isinstance(
        value,
        bool,
    ):
        return value

    return str(
        value
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def send_transactional_email(
    *,
    to_email,
    subject,
    text_body,
    html_body=None,
):
    backend = (
        current_app.config.get(
            "EMAIL_BACKEND",
            "disabled",
        )
        or "disabled"
    ).strip().lower()

    if backend == "console":
        current_app.logger.info(
            (
                "Transactional email "
                "to=%s subject=%s\n%s"
            ),
            to_email,
            subject,
            text_body,
        )
        return True

    if backend == "disabled":
        current_app.logger.warning(
            (
                "Transactional email disabled "
                "to=%s subject=%s"
            ),
            to_email,
            subject,
        )
        return False

    if backend != "smtp":
        raise RuntimeError(
            (
                "EMAIL_BACKEND inválido: "
                f"{backend}"
            )
        )

    host = current_app.config.get(
        "SMTP_HOST"
    )
    from_email = (
        current_app.config.get(
            "EMAIL_FROM"
        )
    )

    if (
        not host
        or not from_email
    ):
        current_app.logger.error(
            (
                "SMTP não configurado: "
                "SMTP_HOST e EMAIL_FROM "
                "são obrigatórios."
            )
        )
        return False

    port = int(
        current_app.config.get(
            "SMTP_PORT",
            587,
        )
    )

    username = (
        current_app.config.get(
            "SMTP_USERNAME"
        )
    )
    password = (
        current_app.config.get(
            "SMTP_PASSWORD"
        )
    )

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(
        text_body
    )

    if html_body:
        message.add_alternative(
            html_body,
            subtype="html",
        )

    try:
        with smtplib.SMTP(
            host,
            port,
            timeout=15,
        ) as smtp:
            if _bool_config(
                "SMTP_USE_TLS",
                True,
            ):
                smtp.starttls()

            if username:
                smtp.login(
                    username,
                    password or "",
                )

            smtp.send_message(
                message
            )

        return True
    except (
        OSError,
        smtplib.SMTPException,
    ):
        current_app.logger.exception(
            (
                "Falha no envio de e-mail "
                "transacional para %s."
            ),
            to_email,
        )
        return False
