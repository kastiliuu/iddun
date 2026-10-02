from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class SlotStatus:
    AVAILABLE = "available"
    HELD = "held"
    BOOKED = "booked"
    BLOCKED_EXTERNAL = "blocked_external"
    BLOCKED_MANUAL = "blocked_manual"
    EXPIRED = "expired"

    CHOICES = [
        (AVAILABLE, "Disponível"),
        (HELD, "Em reserva"),
        (BOOKED, "Reservado"),
        (BLOCKED_EXTERNAL, "Bloqueado pela agenda"),
        (BLOCKED_MANUAL, "Bloqueado manualmente"),
        (EXPIRED, "Expirado"),
    ]
    LABELS = dict(CHOICES)


class BookingStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

    CHOICES = [
        (PENDING, "Aguardando confirmação"),
        (CONFIRMED, "Confirmada"),
        (COMPLETED, "Concluída"),
        (CANCELLED, "Cancelada"),
        (NO_SHOW, "Não compareceu"),
    ]
    LABELS = dict(CHOICES)


class ExperienceSlot(db.Model):
    __tablename__ = "experience_slots"

    id = db.Column(db.Integer, primary_key=True)
    experience_id = db.Column(
        db.Integer,
        db.ForeignKey("experiences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey("professional_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    establishment_id = db.Column(
        db.Integer,
        db.ForeignKey("establishments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(
        db.String(32),
        nullable=False,
        default=SlotStatus.AVAILABLE,
        index=True,
    )
    booking_cutoff_minutes = db.Column(db.Integer, nullable=True)
    hold_expires_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    external_calendar_provider = db.Column(db.String(32), nullable=True)
    external_event_id = db.Column(db.String(255), nullable=True)
    external_block_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    experience = db.relationship("Experience", back_populates="slots")
    professional = db.relationship("ProfessionalProfile", back_populates="slots")
    establishment = db.relationship("Establishment", back_populates="slots")
    bookings = db.relationship(
        "Booking",
        back_populates="slot",
        order_by="Booking.created_at.desc()",
    )

    __table_args__ = (
        db.Index(
            "ix_experience_slots_professional_window",
            "professional_id",
            "starts_at",
            "ends_at",
        ),
    )

    @property
    def status_label(self):
        return SlotStatus.LABELS.get(self.status, self.status.title())


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.Integer,
        db.ForeignKey("client_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    experience_id = db.Column(
        db.Integer,
        db.ForeignKey("experiences.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey("professional_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    establishment_id = db.Column(
        db.Integer,
        db.ForeignKey("establishments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slot_id = db.Column(
        db.Integer,
        db.ForeignKey("experience_slots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = db.Column(
        db.String(32),
        nullable=False,
        default=BookingStatus.PENDING,
        index=True,
    )
    price_at_booking = db.Column(db.Numeric(10, 2), nullable=False)
    hold_expires_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancelled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    no_show_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancellation_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    client = db.relationship("ClientProfile", back_populates="bookings")
    experience = db.relationship("Experience", back_populates="bookings")
    professional = db.relationship("ProfessionalProfile", back_populates="bookings")
    establishment = db.relationship("Establishment", back_populates="bookings")
    slot = db.relationship("ExperienceSlot", back_populates="bookings")
    reviews = db.relationship(
        "Review",
        back_populates="booking",
        cascade="all, delete-orphan",
        order_by="Review.created_at.asc()",
    )

    __table_args__ = (
        db.Index(
            "uq_bookings_active_slot",
            "slot_id",
            unique=True,
            postgresql_where=db.text(
                "status IN ('pending', 'confirmed')"
            ),
            sqlite_where=db.text(
                "status IN ('pending', 'confirmed')"
            ),
        ),
    )

    @property
    def status_label(self):
        return BookingStatus.LABELS.get(self.status, self.status.title())
