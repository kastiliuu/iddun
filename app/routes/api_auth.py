"""Autenticação JSON do aplicativo, separada da sessão web."""

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, current_app, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import csrf, db, limiter
from app.models.profile import ClientProfile
from app.models.account_token import AccountTokenPurpose
from app.models.user import User, UserRole
from app.services.api_auth import (
    get_user_by_access_token,
    issue_session,
    revoke_session,
    rotate_refresh_token,
)
from app.services.api_contract import (
    api_error,
    api_json,
)
from app.services.account_notifications import (
    send_email_verification,
    send_password_reset_email,
)
from app.services.account_security import (
    reset_password_token,
    verify_email_token,
)


api_auth_bp = Blueprint(
    "api_auth",
    __name__,
    url_prefix="/api/auth",
)

MAX_AUTH_BODY_BYTES = 16_384


def _auth_json(payload, status=200):
    response = api_json(
        payload,
        status,
        cache_control="no-store",
    )
    response.headers["Pragma"] = "no-cache"
    return response


def _json_body():
    if (
        request.content_length is not None
        and request.content_length > MAX_AUTH_BODY_BYTES
    ):
        return None, api_error(
            "request_too_large",
            "A solicitação é muito grande.",
            413,
        )

    if not request.is_json:
        return None, api_error(
            "json_required",
            "Envie os dados em formato JSON.",
            415,
        )

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return None, api_error(
            "invalid_json",
            "Não foi possível ler os dados enviados.",
            400,
        )

    return payload, None


def _normalized_email(value):
    if not isinstance(value, str):
        return None

    email = value.strip().lower()

    if not email or len(email) > 255:
        return None

    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        return None

    return email


def _bearer_token():
    authorization = request.headers.get("Authorization", "")
    parts = authorization.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def _user_payload(user):
    professional = user.professional_profile

    payload = {
        "name": user.name,
        "email": user.email,
        "role": "professional" if professional is not None else "client",
        "accountRole": user.role,
        "emailVerified": (
            user.is_email_verified
        ),
    }

    if professional is not None:
        payload["profileId"] = str(professional.id)

        if professional.primary_specialty:
            payload["specialty"] = professional.primary_specialty

        if professional.city:
            payload["city"] = professional.city
    elif user.client_profile is not None:
        payload["profileId"] = str(user.client_profile.id)

    return payload


def _tokens_payload(tokens):
    return {
        "accessToken": tokens.access_token,
        "refreshToken": tokens.refresh_token,
        "accessExpiresAt": tokens.access_expires_at.isoformat(),
        "refreshExpiresAt": tokens.refresh_expires_at.isoformat(),
    }


def _try_send_verification(
    user,
):
    try:
        return send_email_verification(
            user
        )
    except Exception:
        current_app.logger.exception(
            (
                "Falha inesperada ao preparar "
                "verificação de e-mail user_id=%s"
            ),
            user.id,
        )
        return False


def _try_send_password_reset(
    user,
):
    try:
        return send_password_reset_email(
            user
        )
    except Exception:
        current_app.logger.exception(
            (
                "Falha inesperada ao preparar "
                "recuperação de senha user_id=%s"
            ),
            user.id,
        )
        return False


@api_auth_bp.post("/login")
@csrf.exempt
@limiter.limit("10 per minute")
def login():
    payload, error = _json_body()

    if error is not None:
        return error

    email = _normalized_email(payload.get("email"))
    password = payload.get("password")

    if (
        email is None
        or not isinstance(password, str)
        or not password
        or len(password) > 128
    ):
        return api_error(
            "invalid_credentials",
            "E-mail ou senha incorretos.",
            401,
        )

    user = db.session.scalar(
        select(User).where(User.email == email)
    )

    if (
        user is None
        or not user.check_password(password)
        or not user.is_active
    ):
        return api_error(
            "invalid_credentials",
            "E-mail ou senha incorretos.",
            401,
        )

    tokens = issue_session(user)

    return _auth_json(
        {
            "user": _user_payload(user),
            **_tokens_payload(tokens),
        }
    )


@api_auth_bp.post("/register")
@csrf.exempt
@limiter.limit("5 per minute")
def register():
    payload, error = _json_body()

    if error is not None:
        return error

    name_value = payload.get("name")
    name = name_value.strip() if isinstance(name_value, str) else ""
    email = _normalized_email(payload.get("email"))
    password = payload.get("password")

    if payload.get("role", UserRole.CLIENT) != UserRole.CLIENT:
        return api_error(
            "invalid_role",
            "O cadastro pelo aplicativo está disponível para clientes.",
            400,
        )

    if not 2 <= len(name) <= 120:
        return api_error(
            "invalid_name",
            "Informe um nome entre 2 e 120 caracteres.",
            400,
        )

    if email is None:
        return api_error(
            "invalid_email",
            "Informe um e-mail válido.",
            400,
        )

    if (
        not isinstance(password, str)
        or not 8 <= len(password) <= 128
    ):
        return api_error(
            "invalid_password",
            "A senha deve ter entre 8 e 128 caracteres.",
            400,
        )

    existing_user = db.session.scalar(
        select(User).where(User.email == email)
    )

    if existing_user is not None:
        return api_error(
            "email_in_use",
            "Já existe uma conta cadastrada com este e-mail.",
            409,
        )

    user = User(
        name=name,
        email=email,
        role=UserRole.CLIENT,
        is_active_account=True,
    )
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.flush()
        db.session.add(ClientProfile(user=user))

        # O serviço faz um único commit da conta, do perfil e da sessão.
        tokens = issue_session(user)
    except IntegrityError:
        db.session.rollback()
        return api_error(
            "email_in_use",
            "Já existe uma conta cadastrada com este e-mail.",
            409,
        )

    _try_send_verification(
        user
    )

    return _auth_json(
        {
            "user": _user_payload(user),
            **_tokens_payload(tokens),
        },
        201,
    )


@api_auth_bp.post("/refresh")
@csrf.exempt
@limiter.limit("30 per minute")
def refresh():
    payload, error = _json_body()

    if error is not None:
        return error

    tokens = rotate_refresh_token(payload.get("refreshToken"))

    if tokens is None:
        return api_error(
            "invalid_refresh_token",
            "Sua sessão expirou. Entre novamente.",
            401,
        )

    return _auth_json(_tokens_payload(tokens))


@api_auth_bp.get("/me")
def me():
    token = _bearer_token()
    user = get_user_by_access_token(token)

    if user is None:
        return api_error(
            "authentication_required",
            "Entre na sua conta para continuar.",
            401,
        )

    return _auth_json(_user_payload(user))


@api_auth_bp.post("/password/forgot")
@csrf.exempt
@limiter.limit("5 per minute")
def forgot_password():
    payload, error = _json_body()

    if error is not None:
        return error

    email = _normalized_email(
        payload.get("email")
    )

    if email is not None:
        user = db.session.scalar(
            select(User).where(
                User.email == email,
                User.is_active_account.is_(
                    True
                ),
            )
        )

        if user is not None:
            _try_send_password_reset(
                user
            )

    return _auth_json(
        {
            "message": (
                "Se existir uma conta IDDUN "
                "com este e-mail, enviaremos "
                "as instruções de recuperação."
            )
        },
        202,
    )


@api_auth_bp.post("/password/reset")
@csrf.exempt
@limiter.limit("10 per minute")
def reset_password():
    payload, error = _json_body()

    if error is not None:
        return error

    token = payload.get("token")
    password = payload.get(
        "password"
    )

    if (
        not isinstance(
            token,
            str,
        )
        or not isinstance(
            password,
            str,
        )
        or not 8
        <= len(password)
        <= 128
    ):
        return api_error(
            "invalid_reset_request",
            (
                "Token ou nova senha inválidos."
            ),
            400,
        )

    user = reset_password_token(
        token,
        password,
    )

    if user is None:
        return api_error(
            "invalid_or_expired_token",
            (
                "Este link de recuperação "
                "expirou ou já foi utilizado."
            ),
            400,
        )

    return _auth_json(
        {
            "message": (
                "Senha redefinida com sucesso."
            )
        }
    )


@api_auth_bp.post(
    "/email/verification/resend"
)
@csrf.exempt
@limiter.limit("3 per hour")
def resend_verification():
    token = _bearer_token()
    user = get_user_by_access_token(
        token
    )

    if user is None:
        return api_error(
            "authentication_required",
            (
                "Entre na sua conta "
                "para continuar."
            ),
            401,
        )

    if not user.is_email_verified:
        _try_send_verification(
            user
        )

    return _auth_json(
        {
            "message": (
                "Se necessário, um novo link "
                "de confirmação foi enviado."
            ),
            "emailVerified": (
                user.is_email_verified
            ),
        }
    )


@api_auth_bp.post(
    "/email/verification/confirm"
)
@csrf.exempt
@limiter.limit("10 per minute")
def confirm_email_verification():
    payload, error = _json_body()

    if error is not None:
        return error

    token = payload.get(
        "token"
    )

    if not isinstance(
        token,
        str,
    ):
        return api_error(
            "invalid_verification_token",
            (
                "Token de verificação inválido."
            ),
            400,
        )

    user = verify_email_token(
        token
    )

    if user is None:
        return api_error(
            "invalid_or_expired_token",
            (
                "Este link de verificação "
                "expirou ou já foi utilizado."
            ),
            400,
        )

    return _auth_json(
        {
            "message": (
                "E-mail confirmado com sucesso."
            ),
            "user": _user_payload(
                user
            ),
        }
    )


@api_auth_bp.post("/logout")
@csrf.exempt
@limiter.limit("60 per minute")
def logout():
    token = _bearer_token()

    if token is None:
        return api_error(
            "authentication_required",
            "Entre na sua conta para continuar.",
            401,
        )

    # Logout é idempotente: o app pode limpar seus dados locais mesmo
    # se o token já estiver expirado ou revogado.
    revoke_session(token)

    return "", 204, {"Cache-Control": "no-store"}