from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class ClientProfile(db.Model):
    __tablename__ = "client_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    phone = db.Column(db.String(32), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(2), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    onboarding_completed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    user = db.relationship("User", back_populates="client_profile")
    reviews = db.relationship(
        "Review",
        back_populates="client",
        cascade="all, delete-orphan",
        order_by="Review.created_at.desc()",
    )

    bookings = db.relationship(
        "Booking",
        back_populates="client",
        order_by="Booking.created_at.desc()",
    )

    def recalculate_onboarding(self):
        self.onboarding_completed = bool(self.phone and self.city and self.state)
