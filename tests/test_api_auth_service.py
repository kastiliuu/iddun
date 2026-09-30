"""Testes das sessões revogáveis usadas pela API mobile."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.api_session import ApiSession
from app.models.user import User, UserRole
from app.services.api_auth import (
    ACCESS_TOKEN_TTL,
    REFRESH_TOKEN_TTL,
    get_user_by_access_token,
    issue_session,
    revoke_session,
    rotate_refresh_token,
)


START = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def account(app):
    user = User(
        name="Cliente de teste",
        email="api-session@example.com",
        role=UserRole.CLIENT,
    )
    user.set_password("senha-forte-123")

    db.session.add(user)
    db.session.commit()

    return user


def test_issue_stores_only_token_hashes(account):
    tokens = issue_session(account, now=START)
    saved = db.session.scalar(select(ApiSession))

    assert saved is not None
    assert saved.user_id == account.id
    assert saved.revoked_at is None

    assert saved.access_token_hash == sha256(
        tokens.access_token.encode("ascii")
    ).hexdigest()
    assert saved.refresh_token_hash == sha256(
        tokens.refresh_token.encode("ascii")
    ).hexdigest()

    assert saved.access_token_hash != tokens.access_token
    assert saved.refresh_token_hash != tokens.refresh_token
    assert tokens.access_token != tokens.refresh_token

    assert get_user_by_access_token(
        tokens.access_token,
        now=START,
    ).id == account.id

    # Um token de renovação não serve como token de acesso.
    assert get_user_by_access_token(
        tokens.refresh_token,
        now=START,
    ) is None


def test_access_token_expires_at_the_boundary(account):
    tokens = issue_session(account, now=START)

    assert get_user_by_access_token(
        tokens.access_token,
        now=START + ACCESS_TOKEN_TTL - timedelta(microseconds=1),
    ) is not None

    assert get_user_by_access_token(
        tokens.access_token,
        now=START + ACCESS_TOKEN_TTL,
    ) is None


def test_refresh_rotates_both_tokens_and_rejects_reuse(account):
    original = issue_session(account, now=START)
    original_session = db.session.scalar(select(ApiSession))
    refresh_time = START + timedelta(minutes=5)

    renewed = rotate_refresh_token(
        original.refresh_token,
        now=refresh_time,
    )

    assert renewed is not None
    assert renewed.access_token != original.access_token
    assert renewed.refresh_token != original.refresh_token
    assert renewed.access_expires_at == refresh_time + ACCESS_TOKEN_TTL
    assert renewed.refresh_expires_at == refresh_time + REFRESH_TOKEN_TTL

    assert get_user_by_access_token(
        original.access_token,
        now=refresh_time,
    ) is None
    assert rotate_refresh_token(
        original.refresh_token,
        now=refresh_time,
    ) is None
    assert rotate_refresh_token(
        original.access_token,
        now=refresh_time,
    ) is None

    assert get_user_by_access_token(
        renewed.access_token,
        now=refresh_time,
    ).id == account.id

    assert db.session.scalar(
        select(func.count()).select_from(ApiSession)
    ) == 1
    assert db.session.scalar(select(ApiSession)).id == original_session.id


def test_refresh_token_expires_at_the_boundary(account):
    tokens = issue_session(account, now=START)

    assert rotate_refresh_token(
        tokens.refresh_token,
        now=START + REFRESH_TOKEN_TTL,
    ) is None


def test_logout_revokes_access_and_refresh_even_if_access_expired(account):
    tokens = issue_session(account, now=START)
    logout_time = START + ACCESS_TOKEN_TTL + timedelta(seconds=1)

    assert revoke_session(tokens.access_token, now=logout_time) is True
    assert revoke_session(tokens.access_token, now=logout_time) is False

    assert get_user_by_access_token(
        tokens.access_token,
        now=logout_time,
    ) is None
    assert rotate_refresh_token(
        tokens.refresh_token,
        now=logout_time,
    ) is None

    saved = db.session.scalar(select(ApiSession))
    assert saved.revoked_at is not None


def test_deactivated_account_cannot_use_or_renew_tokens(account):
    tokens = issue_session(account, now=START)

    account.is_active_account = False
    db.session.commit()

    assert get_user_by_access_token(
        tokens.access_token,
        now=START,
    ) is None
    assert rotate_refresh_token(
        tokens.refresh_token,
        now=START,
    ) is None

    with pytest.raises(ValueError, match="Conta indisponível"):
        issue_session(account, now=START)


@pytest.mark.parametrize(
    "invalid_token",
    [
        None,
        "",
        "token-curto",
        "A" * 1000,
        "é" * 43,
    ],
)
def test_malformed_tokens_are_rejected(account, invalid_token):
    issue_session(account, now=START)

    assert get_user_by_access_token(
        invalid_token,
        now=START,
    ) is None
    assert rotate_refresh_token(
        invalid_token,
        now=START,
    ) is None
    assert revoke_session(
        invalid_token,
        now=START,
    ) is False