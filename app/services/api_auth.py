"""Emissão e validação das sessões usadas pela API do aplicativo."""

import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from sqlalchemy import select

from app.extensions import db
from app.models.api_session import ApiSession


ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)

# secrets.token_urlsafe(32) produz 43 caracteres sem padding.
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}", re.ASCII)


@dataclass(frozen=True, slots=True)
class SessionTokens:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


def _as_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _now(value=None):
    return _as_utc(value or datetime.now(timezone.utc))


def _token_hash(token):
    if not isinstance(token, str):
        return None

    if _TOKEN_PATTERN.fullmatch(token) is None:
        return None

    return sha256(token.encode("ascii")).hexdigest()


def _new_tokens(now):
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)

    while refresh_token == access_token:
        refresh_token = secrets.token_urlsafe(32)

    return SessionTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=now + ACCESS_TOKEN_TTL,
        refresh_expires_at=now + REFRESH_TOKEN_TTL,
    )


def issue_session(user, *, now=None):
    """Cria uma sessão para um usuário já persistido e ativo.

    Faz o commit antes de devolver os tokens ao chamador. O chamador
    deve enviar os tokens somente na resposta da requisição autenticada.
    """
    if user is None or user.id is None or not user.is_active:
        raise ValueError("Conta indisponível para acesso à API.")

    current_time = _now(now)
    tokens = _new_tokens(current_time)

    db.session.add(
        ApiSession(
            user_id=user.id,
            access_token_hash=_token_hash(tokens.access_token),
            refresh_token_hash=_token_hash(tokens.refresh_token),
            access_expires_at=tokens.access_expires_at,
            refresh_expires_at=tokens.refresh_expires_at,
            created_at=current_time,
        )
    )
    db.session.commit()

    return tokens


def get_user_by_access_token(access_token, *, now=None):
    """Retorna o usuário ativo associado a um token de acesso válido."""
    token_hash = _token_hash(access_token)

    if token_hash is None:
        return None

    api_session = db.session.scalar(
        select(ApiSession).where(
            ApiSession.access_token_hash == token_hash
        )
    )

    if api_session is None or api_session.revoked_at is not None:
        return None

    if _now(now) >= _as_utc(api_session.access_expires_at):
        return None

    user = api_session.user

    if user is None or not user.is_active:
        return None

    return user


def rotate_refresh_token(refresh_token, *, now=None):
    """Renova a sessão e invalida imediatamente os tokens anteriores."""
    token_hash = _token_hash(refresh_token)

    if token_hash is None:
        return None

    # No PostgreSQL, o bloqueio impede duas renovações simultâneas
    # de aceitarem o mesmo token de renovação.
    api_session = db.session.scalar(
        select(ApiSession)
        .where(ApiSession.refresh_token_hash == token_hash)
        .with_for_update()
    )

    if api_session is None or api_session.revoked_at is not None:
        return None

    current_time = _now(now)

    if current_time >= _as_utc(api_session.refresh_expires_at):
        return None

    user = api_session.user

    if user is None or not user.is_active:
        return None

    tokens = _new_tokens(current_time)

    api_session.access_token_hash = _token_hash(tokens.access_token)
    api_session.refresh_token_hash = _token_hash(tokens.refresh_token)
    api_session.access_expires_at = tokens.access_expires_at
    api_session.refresh_expires_at = tokens.refresh_expires_at

    db.session.commit()

    return tokens


def revoke_session(access_token, *, now=None):
    """Revoga a sessão identificada pelo token de acesso, mesmo expirado."""
    token_hash = _token_hash(access_token)

    if token_hash is None:
        return False

    api_session = db.session.scalar(
        select(ApiSession).where(
            ApiSession.access_token_hash == token_hash
        )
    )

    if api_session is None or api_session.revoked_at is not None:
        return False

    api_session.revoked_at = _now(now)
    db.session.commit()

    return True