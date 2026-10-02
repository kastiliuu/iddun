from datetime import (
    datetime,
    timedelta,
    timezone,
)
from hashlib import sha256

from sqlalchemy import select

from app.extensions import db
from app.models.account_token import (
    AccountToken,
    AccountTokenPurpose,
)
from app.models.api_session import ApiSession
from app.models.user import User, UserRole
from app.services.account_security import (
    EMAIL_VERIFICATION_TTL,
    PASSWORD_RESET_TTL,
    get_valid_account_token,
    issue_account_token,
    reset_password_token,
    verify_email_token,
)
from app.services.api_auth import (
    get_user_by_access_token,
    issue_session,
)


def _utc(value):
    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    )


START = datetime(
    2026,
    10,
    2,
    12,
    0,
    tzinfo=timezone.utc,
)


def _account(app):
    with app.app_context():
        user = User(
            name="Conta Segurança",
            email="security@example.com",
            role=UserRole.CLIENT,
        )
        user.set_password(
            "senha-antiga-123"
        )
        db.session.add(user)
        db.session.commit()

        return user.id


def test_account_token_is_stored_only_as_hash(
    app,
):
    user_id = _account(app)

    with app.app_context():
        user = db.session.get(
            User,
            user_id,
        )

        issued = issue_account_token(
            user,
            AccountTokenPurpose.PASSWORD_RESET,
            now=START,
        )

        stored = db.session.scalar(
            select(AccountToken)
        )

        assert (
            stored.token_hash
            != issued.token
        )
        assert (
            stored.token_hash
            == sha256(
                issued.token.encode(
                    "ascii"
                )
            ).hexdigest()
        )
        assert (
            _utc(
                stored.expires_at
            )
            == START
            + PASSWORD_RESET_TTL
        )


def test_issuing_new_token_invalidates_previous_one(
    app,
):
    user_id = _account(app)

    with app.app_context():
        user = db.session.get(
            User,
            user_id,
        )

        first = issue_account_token(
            user,
            AccountTokenPurpose.EMAIL_VERIFICATION,
            now=START,
        )

        second = issue_account_token(
            user,
            AccountTokenPurpose.EMAIL_VERIFICATION,
            now=(
                START
                + timedelta(minutes=1)
            ),
        )

        assert (
            get_valid_account_token(
                first.token,
                AccountTokenPurpose.EMAIL_VERIFICATION,
                now=(
                    START
                    + timedelta(minutes=2)
                ),
            )
            is None
        )

        assert (
            get_valid_account_token(
                second.token,
                AccountTokenPurpose.EMAIL_VERIFICATION,
                now=(
                    START
                    + timedelta(minutes=2)
                ),
            )
            is not None
        )


def test_email_verification_is_single_use(
    app,
):
    user_id = _account(app)

    with app.app_context():
        user = db.session.get(
            User,
            user_id,
        )

        issued = issue_account_token(
            user,
            AccountTokenPurpose.EMAIL_VERIFICATION,
            now=START,
        )

        verified = verify_email_token(
            issued.token,
            now=(
                START
                + timedelta(minutes=5)
            ),
        )

        assert (
            verified.id
            == user_id
        )
        assert (
            _utc(
                verified.email_verified_at
            )
            == START
            + timedelta(minutes=5)
        )

        assert (
            verify_email_token(
                issued.token,
                now=(
                    START
                    + timedelta(minutes=6)
                ),
            )
            is None
        )


def test_expired_email_token_is_rejected(
    app,
):
    user_id = _account(app)

    with app.app_context():
        user = db.session.get(
            User,
            user_id,
        )

        issued = issue_account_token(
            user,
            AccountTokenPurpose.EMAIL_VERIFICATION,
            now=START,
        )

        assert (
            verify_email_token(
                issued.token,
                now=(
                    START
                    + EMAIL_VERIFICATION_TTL
                ),
            )
            is None
        )


def test_password_reset_changes_password_and_revokes_api_sessions(
    app,
):
    user_id = _account(app)

    with app.app_context():
        user = db.session.get(
            User,
            user_id,
        )

        session = issue_session(
            user,
            now=START,
        )

        issued = issue_account_token(
            user,
            AccountTokenPurpose.PASSWORD_RESET,
            now=START,
        )

        reset = reset_password_token(
            issued.token,
            "nova-senha-456",
            now=(
                START
                + timedelta(minutes=10)
            ),
        )

        assert reset.id == user_id
        assert reset.check_password(
            "nova-senha-456"
        )
        assert not reset.check_password(
            "senha-antiga-123"
        )
        assert (
            reset.email_verified_at
            is not None
        )

        api_session = db.session.scalar(
            select(ApiSession)
        )

        assert (
            _utc(
                api_session.revoked_at
            )
            == START
            + timedelta(minutes=10)
        )

        assert (
            get_user_by_access_token(
                session.access_token,
                now=(
                    START
                    + timedelta(minutes=11)
                ),
            )
            is None
        )

        assert (
            reset_password_token(
                issued.token,
                "outra-senha-789",
                now=(
                    START
                    + timedelta(minutes=11)
                ),
            )
            is None
        )


def test_expired_password_reset_is_rejected(
    app,
):
    user_id = _account(app)

    with app.app_context():
        user = db.session.get(
            User,
            user_id,
        )

        issued = issue_account_token(
            user,
            AccountTokenPurpose.PASSWORD_RESET,
            now=START,
        )

        assert (
            reset_password_token(
                issued.token,
                "nova-senha-456",
                now=(
                    START
                    + PASSWORD_RESET_TTL
                ),
            )
            is None
        )

        assert user.check_password(
            "senha-antiga-123"
        )
