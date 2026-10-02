"""Tokens de uso único para ações sensíveis de conta."""

from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class AccountTokenPurpose:
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"

    CHOICES = (
        PASSWORD_RESET,
        EMAIL_VERIFICATION,
    )


class AccountToken(db.Model):
    __tablename__ = "account_tokens"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    purpose = db.Column(
        db.String(40),
        nullable=False,
        index=True,
    )

    token_hash = db.Column(
        db.String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    consumed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    user = db.relationship(
        "User",
        back_populates="account_tokens",
    )

    __table_args__ = (
        db.CheckConstraint(
            (
                "purpose IN "
                "('password_reset', 'email_verification')"
            ),
            name="ck_account_token_purpose",
        ),
    )
