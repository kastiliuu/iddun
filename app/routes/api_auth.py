"""Autenticação JSON do aplicativo, separada da sessão web."""

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import csrf, db
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.api_auth import (
    get_user_by_access_token,
    issue_session,
    revoke_session,
    rotate_refresh_token,
)


api_auth_bp = Blueprint(
    "api_auth",
    __name__,
    url_prefix="/api/auth",
)

MAX_AUTH_BODY_BYTES = 16_384


def _json_response(payload, status=200):
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response


def _error(code, message, status):
    return _json_response(
        {
            "message": message,
            "error": {
                "code": code,
                "message": message,
            },
        },
        status,
    )


def _json_body():
    if (
        request.content_length is not None
        and request.content_length > MAX_AUTH_BODY_BYTES
    ):
        return None, _error(
            "request_too_large",
            "A solicitação é muito grande.",
            413,
        )

    if not request.is_json:
        return None, _error(
            "json_required",
            "Envie os dados em formato JSON.",
            415,
        )

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return None, _error(
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


@api_auth_bp.post("/login")
@csrf.exempt
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
        return _error(
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
        return _error(
            "invalid_credentials",
            "E-mail ou senha incorretos.",
            401,
        )

    tokens = issue_session(user)

    return _json_response(
        {
            "user": _user_payload(user),
            **_tokens_payload(tokens),
        }
    )


@api_auth_bp.post("/register")
@csrf.exempt
def register():
    payload, error = _json_body()

    if error is not None:
        return error

    name_value = payload.get("name")
    name = name_value.strip() if isinstance(name_value, str) else ""
    email = _normalized_email(payload.get("email"))
    password = payload.get("password")

    if payload.get("role", UserRole.CLIENT) != UserRole.CLIENT:
        return _error(
            "invalid_role",
            "O cadastro pelo aplicativo está disponível para clientes.",
            400,
        )

    if not 2 <= len(name) <= 120:
        return _error(
            "invalid_name",
            "Informe um nome entre 2 e 120 caracteres.",
            400,
        )

    if email is None:
        return _error(
            "invalid_email",
            "Informe um e-mail válido.",
            400,
        )

    if (
        not isinstance(password, str)
        or not 8 <= len(password) <= 128
    ):
        return _error(
            "invalid_password",
            "A senha deve ter entre 8 e 128 caracteres.",
            400,
        )

    existing_user = db.session.scalar(
        select(User).where(User.email == email)
    )

    if existing_user is not None:
        return _error(
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
        return _error(
            "email_in_use",
            "Já existe uma conta cadastrada com este e-mail.",
            409,
        )

    return _json_response(
        {
            "user": _user_payload(user),
            **_tokens_payload(tokens),
        },
        201,
    )


@api_auth_bp.post("/refresh")
@csrf.exempt
def refresh():
    payload, error = _json_body()

    if error is not None:
        return error

    tokens = rotate_refresh_token(payload.get("refreshToken"))

    if tokens is None:
        return _error(
            "invalid_refresh_token",
            "Sua sessão expirou. Entre novamente.",
            401,
        )

    return _json_response(_tokens_payload(tokens))


@api_auth_bp.get("/me")
def me():
    token = _bearer_token()
    user = get_user_by_access_token(token)

    if user is None:
        return _error(
            "authentication_required",
            "Entre na sua conta para continuar.",
            401,
        )

    return _json_response(_user_payload(user))


@api_auth_bp.post("/logout")
@csrf.exempt
def logout():
    token = _bearer_token()

    if token is None:
        return _error(
            "authentication_required",
            "Entre na sua conta para continuar.",
            401,
        )

    # Logout é idempotente: o app pode limpar seus dados locais mesmo
    # se o token já estiver expirado ou revogado.
    revoke_session(token)

    return "", 204, {"Cache-Control": "no-store"}