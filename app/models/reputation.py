from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class ReviewTarget:
    PROFESSIONAL = "professional"
    ESTABLISHMENT = "establishment"

    CHOICES = {PROFESSIONAL, ESTABLISHMENT}


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id = db.Column(
        db.Integer,
        db.ForeignKey("client_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type = db.Column(db.String(24), nullable=False, index=True)
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey("professional_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    establishment_id = db.Column(
        db.Integer,
        db.ForeignKey("establishments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    rating = db.Column(db.SmallInteger, nullable=False)
    recommended = db.Column(db.Boolean, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    is_visible = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    booking = db.relationship("Booking", back_populates="reviews")
    client = db.relationship("ClientProfile", back_populates="reviews")
    professional = db.relationship("ProfessionalProfile", back_populates="reviews_received")
    establishment = db.relationship("Establishment", back_populates="reviews_received")

    __table_args__ = (
        db.UniqueConstraint("booking_id", "target_type", name="uq_review_booking_target"),
        db.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_1_5"),
    )

    @property
    def verified(self):
        return True


class ContactClick(db.Model):
    __tablename__ = "contact_clicks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey("professional_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    establishment_id = db.Column(
        db.Integer,
        db.ForeignKey("establishments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    channel = db.Column(db.String(32), nullable=False, default="whatsapp", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    user = db.relationship("User")
    professional = db.relationship("ProfessionalProfile", back_populates="contact_clicks")
    establishment = db.relationship("Establishment", back_populates="contact_clicks")
