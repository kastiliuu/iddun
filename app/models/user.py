from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import event
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class UserRole:
    CLIENT = "client"
    PROFESSIONAL = "professional"
    ADMIN = "admin"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
        index=True
    )

    # ID-SOC-R1-02: @username público, único e sempre em minúsculas.
    # Preenchido pelo nome quando a conta é criada sem um @ escolhido.
    username = db.Column(
        db.String(30),
        nullable=False,
        unique=True,
        index=True,
    )

    # QA-001: imagens pessoais canônicas; perfis técnicos continuam como
    # espelhos legados durante a transição e podem ser revertidos.
    avatar_url = db.Column(db.String(500), nullable=True)
    cover_url = db.Column(db.String(500), nullable=True)

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(32),
        nullable=False,
        default=UserRole.CLIENT
    )

    is_active_account = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    email_verified_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    deleted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    client_profile = db.relationship(
        "ClientProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    professional_profile = db.relationship(
        "ProfessionalProfile",
        back_populates="user",
        uselist=False,
    )

    establishment_accesses = db.relationship(
        "EstablishmentUserAccess",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    account_tokens = db.relationship(
        "AccountToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    follows = db.relationship(
        "Follow",
        back_populates="user",
        foreign_keys="Follow.user_id",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Follow.created_at.asc()",
    )

    saves = db.relationship(
        "Save",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Save.created_at.asc()",
    )

    notifications = db.relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Notification.created_at.desc()",
    )

    notification_preference = db.relationship(
        "NotificationPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )

    @property
    def is_active(self):
        return self.is_active_account

    @property
    def is_email_verified(self):
        return (
            self.email_verified_at
            is not None
        )


class UsernameHistory(db.Model):
    """@ que a pessoa já usou: continua levando a ela e nunca passa a outra."""

    __tablename__ = "username_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    username = db.Column(
        db.String(30),
        nullable=False,
        unique=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User")


@event.listens_for(User, "before_insert")
def _assign_username(mapper, connection, target):
    """Conta nova sem @ escolhido recebe um sugerido pelo nome (ID-SOC-R1-02).

    Contas criadas no mesmo flush não podem receber o mesmo @: os nomes
    escolhidos ficam na sessão até o fim do flush.
    """
    from sqlalchemy.orm import object_session

    from app.services.username_service import normalize, suggest

    session = object_session(target)
    pending = session.info.setdefault("iddun_pending_usernames", set()) if session else set()
    if target.username:
        target.username = normalize(target.username)
    else:
        target.username = suggest(target.name, taken=pending)
    pending.add(target.username)


@event.listens_for(Session, "after_flush_postexec")
def _forget_pending_usernames(session, flush_context):
    session.info.pop("iddun_pending_usernames", None)
