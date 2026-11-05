from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class NotificationKind:
    BOOKING = "booking"
    IDDUN_NOW = "iddun_now"
    FOLLOW = "follow"
    SYSTEM = "system"
    # PR 6a (D-SOC-21).
    LIKE = "like"
    COMMENT = "comment"
    MEMBERSHIP = "membership"
    REVIEW = "review"

    VALUES = (
        BOOKING,
        IDDUN_NOW,
        FOLLOW,
        SYSTEM,
        LIKE,
        COMMENT,
        MEMBERSHIP,
        REVIEW,
    )


class NotificationCategory:
    """Abas da central (DEC-ID-216): Reservas, Social, Profissional e Empresa."""

    BOOKINGS = "bookings"
    SOCIAL = "social"
    WORK = "work"
    SYSTEM = "system"

    VALUES = (BOOKINGS, SOCIAL, WORK, SYSTEM)

    BY_KIND = {
        NotificationKind.BOOKING: BOOKINGS,
        NotificationKind.IDDUN_NOW: BOOKINGS,
        NotificationKind.FOLLOW: SOCIAL,
        NotificationKind.LIKE: SOCIAL,
        NotificationKind.COMMENT: SOCIAL,
        NotificationKind.MEMBERSHIP: WORK,
        NotificationKind.REVIEW: WORK,
        NotificationKind.SYSTEM: SYSTEM,
    }


class NotificationContext:
    """Contexto do aviso (DEC-ID-221)."""

    CLIENT = "client"
    PROFESSIONAL = "professional"
    ESTABLISHMENT = "establishment"

    VALUES = (CLIENT, PROFESSIONAL, ESTABLISHMENT)


class Notification(db.Model):
    __tablename__ = "notifications"

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
    kind = db.Column(
        db.String(32),
        nullable=False,
        index=True,
    )
    title = db.Column(
        db.String(180),
        nullable=False,
    )
    body = db.Column(
        db.String(600),
        nullable=False,
    )
    action_type = db.Column(
        db.String(40),
        nullable=True,
    )
    action_id = db.Column(
        db.String(180),
        nullable=True,
    )
    read_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    # PR 6a (D-SOC-21): aba, contexto, idempotência e agrupamento.
    category = db.Column(
        db.String(24),
        nullable=False,
        default=NotificationCategory.SYSTEM,
        server_default=NotificationCategory.SYSTEM,
    )
    context_type = db.Column(db.String(24), nullable=True)
    context_id = db.Column(db.Integer, nullable=True)
    dedupe_key = db.Column(db.String(160), nullable=True)
    group_key = db.Column(db.String(160), nullable=True)
    group_count = db.Column(
        db.Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    user = db.relationship(
        "User",
        back_populates="notifications",
    )

    __table_args__ = (
        db.CheckConstraint(
            (
                "kind IN "
                "('booking', 'iddun_now', 'follow', 'system', "
                "'like', 'comment', 'membership', 'review')"
            ),
            name="ck_notification_kind",
        ),
        db.CheckConstraint(
            "category IN ('bookings', 'social', 'work', 'system')",
            name="ck_notification_category",
        ),
        db.CheckConstraint(
            "context_type IS NULL OR context_type IN "
            "('client', 'professional', 'establishment')",
            name="ck_notification_context",
        ),
        db.CheckConstraint(
            "group_count >= 1",
            name="ck_notification_group_count",
        ),
        db.UniqueConstraint(
            "user_id",
            "dedupe_key",
            name="uq_notifications_user_dedupe",
        ),
        db.Index("ix_notifications_user_category_read", "user_id", "category", "read_at"),
        db.Index("ix_notifications_user_created", "user_id", "created_at"),
        db.Index("ix_notifications_user_group", "user_id", "group_key"),
    )

    @property
    def is_read(self):
        return self.read_at is not None


class NotificationPreference(db.Model):
    __tablename__ = "notification_preferences"

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
        unique=True,
        index=True,
    )
    booking_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )
    iddun_now_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )
    follow_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )
    system_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )
    # PR 6a: preferências por aba (DEC-ID-218). Reservas são essenciais.
    social_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )
    work_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )
    push_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    user = db.relationship(
        "User",
        back_populates="notification_preference",
    )
