from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class NotificationKind:
    BOOKING = "booking"
    IDDUN_NOW = "iddun_now"
    FOLLOW = "follow"
    SYSTEM = "system"

    VALUES = (
        BOOKING,
        IDDUN_NOW,
        FOLLOW,
        SYSTEM,
    )


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

    user = db.relationship(
        "User",
        back_populates="notifications",
    )

    __table_args__ = (
        db.CheckConstraint(
            (
                "kind IN "
                "('booking', 'iddun_now', 'follow', 'system')"
            ),
            name="ck_notification_kind",
        ),
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
