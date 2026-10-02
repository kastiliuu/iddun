"""Ações sensíveis de conta com tokens de uso único."""

import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from sqlalchemy import select, update

from app.extensions import db
from app.models.account_token import (
    AccountToken,
    AccountTokenPurpose,
)
from app.models.api_session import ApiSession


PASSWORD_RESET_TTL = timedelta(hours=1)
EMAIL_VERIFICATION_TTL = timedelta(hours=24)

_TOKEN_PATTERN = re.compile(
    r"[A-Za-z0-9_-]{43}",
    re.ASCII,
)


@dataclass(
    frozen=True,
    slots=True,
)
class IssuedAccountToken:
    token: str
    expires_at: datetime


def _as_utc(value):
    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    )


def _now(value=None):
    return _as_utc(
        value
        or datetime.now(
            timezone.utc
        )
    )


def _token_hash(token):
    if not isinstance(
        token,
        str,
    ):
        return None

    if (
        _TOKEN_PATTERN.fullmatch(
            token
        )
        is None
    ):
        return None

    return sha256(
        token.encode("ascii")
    ).hexdigest()


def _purpose_ttl(purpose):
    if (
        purpose
        == AccountTokenPurpose.PASSWORD_RESET
    ):
        return PASSWORD_RESET_TTL

    if (
        purpose
        == AccountTokenPurpose.EMAIL_VERIFICATION
    ):
        return EMAIL_VERIFICATION_TTL

    raise ValueError(
        "Finalidade de token inválida."
    )


def issue_account_token(
    user,
    purpose,
    *,
    now=None,
):
    if (
        user is None
        or user.id is None
        or not user.is_active
    ):
        raise ValueError(
            "Conta indisponível."
        )

    current_time = _now(now)
    ttl = _purpose_ttl(
        purpose
    )

    db.session.execute(
        update(AccountToken)
        .where(
            AccountToken.user_id
            == user.id,
            AccountToken.purpose
            == purpose,
            AccountToken.consumed_at.is_(
                None
            ),
        )
        .values(
            consumed_at=current_time
        )
    )

    raw_token = secrets.token_urlsafe(
        32
    )

    token = AccountToken(
        user_id=user.id,
        purpose=purpose,
        token_hash=_token_hash(
            raw_token
        ),
        expires_at=(
            current_time
            + ttl
        ),
        created_at=current_time,
    )

    db.session.add(
        token
    )
    db.session.commit()

    return IssuedAccountToken(
        token=raw_token,
        expires_at=token.expires_at,
    )


def get_valid_account_token(
    raw_token,
    purpose,
    *,
    now=None,
    for_update=False,
):
    token_hash = _token_hash(
        raw_token
    )

    if token_hash is None:
        return None

    query = select(
        AccountToken
    ).where(
        AccountToken.token_hash
        == token_hash,
        AccountToken.purpose
        == purpose,
        AccountToken.consumed_at.is_(
            None
        ),
    )

    if for_update:
        query = (
            query.with_for_update()
        )

    token = db.session.scalar(
        query
    )

    if token is None:
        return None

    if (
        _now(now)
        >= _as_utc(
            token.expires_at
        )
    ):
        return None

    if (
        token.user is None
        or not token.user.is_active
    ):
        return None

    return token


def verify_email_token(
    raw_token,
    *,
    now=None,
):
    current_time = _now(now)

    token = get_valid_account_token(
        raw_token,
        AccountTokenPurpose.EMAIL_VERIFICATION,
        now=current_time,
        for_update=True,
    )

    if token is None:
        return None

    user = token.user

    token.consumed_at = (
        current_time
    )

    if (
        user.email_verified_at
        is None
    ):
        user.email_verified_at = (
            current_time
        )

    db.session.commit()

    return user


def reset_password_token(
    raw_token,
    password,
    *,
    now=None,
):
    if (
        not isinstance(
            password,
            str,
        )
        or not 8
        <= len(password)
        <= 128
    ):
        raise ValueError(
            (
                "A senha deve ter "
                "entre 8 e 128 caracteres."
            )
        )

    current_time = _now(now)

    token = get_valid_account_token(
        raw_token,
        AccountTokenPurpose.PASSWORD_RESET,
        now=current_time,
        for_update=True,
    )

    if token is None:
        return None

    user = token.user

    user.set_password(
        password
    )

    token.consumed_at = (
        current_time
    )

    # Receber o link de recuperação comprova posse
    # do endereço utilizado na conta.
    if (
        user.email_verified_at
        is None
    ):
        user.email_verified_at = (
            current_time
        )

    db.session.execute(
        update(ApiSession)
        .where(
            ApiSession.user_id
            == user.id,
            ApiSession.revoked_at.is_(
                None
            ),
        )
        .values(
            revoked_at=current_time
        )
    )

    db.session.commit()

    return user
