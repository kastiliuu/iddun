"""E-mails de segurança da conta."""

from flask import url_for

from app.models.account_token import (
    AccountTokenPurpose,
)
from app.services.account_security import (
    issue_account_token,
)
from app.services.email_delivery import (
    send_transactional_email,
)


def send_password_reset_email(
    user,
):
    issued = issue_account_token(
        user,
        AccountTokenPurpose.PASSWORD_RESET,
    )

    reset_url = url_for(
        "auth.reset_password",
        token=issued.token,
        _external=True,
    )

    return send_transactional_email(
        to_email=user.email,
        subject="Redefina sua senha do IDDUN",
        text_body=(
            f"Olá, {user.name}.\n\n"
            "Recebemos uma solicitação para redefinir "
            "a senha da sua conta IDDUN.\n\n"
            f"Acesse: {reset_url}\n\n"
            "Este link expira em 1 hora e só pode ser usado uma vez. "
            "Se você não solicitou a troca, ignore esta mensagem."
        ),
    )


def send_email_verification(
    user,
):
    if user.is_email_verified:
        return True

    issued = issue_account_token(
        user,
        AccountTokenPurpose.EMAIL_VERIFICATION,
    )

    verification_url = url_for(
        "auth.verify_email",
        token=issued.token,
        _external=True,
    )

    return send_transactional_email(
        to_email=user.email,
        subject="Confirme seu e-mail no IDDUN",
        text_body=(
            f"Olá, {user.name}.\n\n"
            "Confirme o e-mail da sua conta IDDUN acessando:\n\n"
            f"{verification_url}\n\n"
            "Este link expira em 24 horas e só pode ser usado uma vez."
        ),
    )
