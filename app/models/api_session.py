"""Sessões revogáveis para a API do aplicativo IDDUN.

Somente os hashes SHA-256 dos tokens de acesso e renovação são
armazenados. A emissão e a validação dos tokens ficam no serviço
de autenticação da API.
"""

from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class ApiSession(db.Model):
    __tablename__ = "api_sessions"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    access_token_hash = db.Column(
        db.String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    refresh_token_hash = db.Column(
        db.String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    access_expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
    )

    refresh_expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    revoked_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    user = db.relationship("User")