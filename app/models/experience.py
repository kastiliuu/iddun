from datetime import datetime, timezone
from decimal import Decimal

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class ExperienceStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    PAUSED = "paused"
    ARCHIVED = "archived"

    CHOICES = [
        (DRAFT, "Rascunho"),
        (PUBLISHED, "Publicada"),
        (PAUSED, "Pausada"),
        (ARCHIVED, "Arquivada"),
    ]

    LABELS = dict(CHOICES)


class ExperienceCategory:
    """
    Taxonomia principal de experiências do IDDUN.

    Essas categorias representam os grandes contextos de
    descoberta da plataforma. Serviços mais específicos devem
    ser tratados como especialidades, títulos ou subcategorias,
    sem fragmentar excessivamente o catálogo principal.
    """

    HAIR = "cabelo"
    NAILS = "unhas"
    BARBER = "barbearia"
    AESTHETICS = "estetica"
    TATTOO = "tatuagem"
    BROWS = "sobrancelhas"

    CHOICES = [
        (HAIR, "Cabelo"),
        (NAILS, "Unhas"),
        (BARBER, "Barbearia"),
        (AESTHETICS, "Estética"),
        (TATTOO, "Tatuagem"),
        (BROWS, "Sobrancelhas"),
    ]

    LABELS = dict(CHOICES)


class Experience(db.Model):
    __tablename__ = "experiences"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    professional_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "professional_profiles.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    establishment_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "establishments.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    title = db.Column(
        db.String(160),
        nullable=False,
    )

    slug = db.Column(
        db.String(190),
        nullable=False,
        unique=True,
        index=True,
    )

    category = db.Column(
        db.String(32),
        nullable=False,
        index=True,
    )

    short_description = db.Column(
        db.String(220),
        nullable=False,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    badge = db.Column(
        db.String(80),
        nullable=True,
    )

    image_url = db.Column(
        db.String(500),
        nullable=True,
    )

    image_focus_x = db.Column(
        db.SmallInteger,
        nullable=False,
        default=50,
    )

    image_focus_y = db.Column(
        db.SmallInteger,
        nullable=False,
        default=50,
    )

    regular_price = db.Column(
        db.Numeric(10, 2),
        nullable=False,
    )

    price = db.Column(
        db.Numeric(10, 2),
        nullable=False,
    )

    duration_minutes = db.Column(
        db.Integer,
        nullable=False,
        default=60,
    )

    booking_cutoff_minutes = db.Column(
        db.Integer,
        nullable=True,
    )

    recommended_return_days = db.Column(
        db.Integer,
        nullable=True,
    )

    status = db.Column(
        db.String(24),
        nullable=False,
        default=ExperienceStatus.DRAFT,
        index=True,
    )

    is_featured = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    # Legacy column kept for existing databases; it does not limit reservations.
    is_first_experience = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    professional = db.relationship(
        "ProfessionalProfile",
        back_populates="experiences",
    )

    establishment = db.relationship(
        "Establishment",
        back_populates="experiences",
    )

    slots = db.relationship(
        "ExperienceSlot",
        back_populates="experience",
        cascade="all, delete-orphan",
        order_by="ExperienceSlot.starts_at.asc()",
    )

    bookings = db.relationship(
        "Booking",
        back_populates="experience",
        order_by="Booking.created_at.desc()",
    )

    work_posts = db.relationship(
        "WorkPost",
        back_populates="experience",
        order_by="WorkPost.published_at.desc(), WorkPost.id.desc()",
    )

    @property
    def status_label(self):
        return ExperienceStatus.LABELS.get(
            self.status,
            self.status.title(),
        )

    @property
    def category_label(self):
        return ExperienceCategory.LABELS.get(
            self.category,
            self.category.title(),
        )

    @property
    def saving_amount(self):
        regular = Decimal(
            self.regular_price or 0
        )

        current = Decimal(
            self.price or 0
        )

        return max(
            Decimal("0"),
            regular - current,
        )