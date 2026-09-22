from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class CalendarProvider:
    GOOGLE = "google"


class CalendarConnection(db.Model):
    __tablename__ = "calendar_connections"

    id = db.Column(db.Integer, primary_key=True)
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey("professional_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = db.Column(db.String(32), nullable=False, default=CalendarProvider.GOOGLE, index=True)
    calendar_id = db.Column(db.String(255), nullable=True)
    calendar_name = db.Column(db.String(255), nullable=True)
    account_email = db.Column(db.String(255), nullable=True)
    access_token_encrypted = db.Column(db.Text, nullable=True)
    refresh_token_encrypted = db.Column(db.Text, nullable=True)
    token_expiry = db.Column(db.DateTime(timezone=True), nullable=True)
    scopes = db.Column(db.Text, nullable=True)
    sync_enabled = db.Column(db.Boolean, nullable=False, default=True)
    create_booking_events = db.Column(db.Boolean, nullable=False, default=True)
    last_synced_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_sync_status = db.Column(db.String(32), nullable=True)
    last_sync_error = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    professional = db.relationship("ProfessionalProfile", back_populates="calendar_connections")

    __table_args__ = (
        db.UniqueConstraint(
            "professional_id",
            "provider",
            name="uq_calendar_connection_professional_provider",
        ),
    )
