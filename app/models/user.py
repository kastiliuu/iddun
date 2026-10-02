from datetime import datetime, timezone

from flask_login import UserMixin
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
