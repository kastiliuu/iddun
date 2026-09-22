from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class ProfilePlan:
    FREE = "free"
    PRO = "pro"


class ProfileTheme:
    BEAUTY = "beauty"
    BARBER = "barber"
    TATTOO = "tattoo"

    CHOICES = [
        (BEAUTY, "Beleza"),
        (BARBER, "Barbearia"),
        (TATTOO, "Tatuagem"),
    ]


class ProfessionalProfile(db.Model):
    __tablename__ = "professional_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    display_name = db.Column(db.String(140), nullable=False)
    slug = db.Column(db.String(180), nullable=False, unique=True, index=True)
    headline = db.Column(db.String(180), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    primary_specialty = db.Column(db.String(120), nullable=True)
    specialties_text = db.Column(db.String(500), nullable=True)
    phone = db.Column(db.String(32), nullable=True)
    whatsapp_enabled = db.Column(db.Boolean, nullable=False, default=True)
    instagram = db.Column(db.String(120), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(2), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    cover_url = db.Column(db.String(500), nullable=True)
    avatar_focus_x = db.Column(db.SmallInteger, nullable=False, default=50)
    avatar_focus_y = db.Column(db.SmallInteger, nullable=False, default=50)
    cover_focus_x = db.Column(db.SmallInteger, nullable=False, default=50)
    cover_focus_y = db.Column(db.SmallInteger, nullable=False, default=50)
    visual_theme = db.Column(db.String(24), nullable=False, default=ProfileTheme.BEAUTY)
    plan_tier = db.Column(db.String(24), nullable=False, default=ProfilePlan.FREE)
    onboarding_completed = db.Column(db.Boolean, nullable=False, default=False)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    timezone = db.Column(db.String(64), nullable=False, default="America/Sao_Paulo")
    default_booking_cutoff_minutes = db.Column(db.Integer, nullable=False, default=60)
    claimed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    user = db.relationship("User", back_populates="professional_profile")
    experiences = db.relationship(
        "Experience",
        back_populates="professional",
        lazy="selectin",
    )

    slots = db.relationship(
        "ExperienceSlot",
        back_populates="professional",
        order_by="ExperienceSlot.starts_at.asc()",
    )

    bookings = db.relationship(
        "Booking",
        back_populates="professional",
        order_by="Booking.created_at.desc()",
    )

    calendar_connections = db.relationship(
        "CalendarConnection",
        back_populates="professional",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    memberships = db.relationship(
        "ProfessionalEstablishmentMembership",
        back_populates="professional",
        cascade="all, delete-orphan",
        order_by="ProfessionalEstablishmentMembership.created_at.desc()",
    )

    certifications = db.relationship(
        "ProfessionalCertification",
        back_populates="professional",
        cascade="all, delete-orphan",
        order_by="ProfessionalCertification.issued_at.desc(), ProfessionalCertification.created_at.desc()",
    )

    reviews_received = db.relationship(
        "Review",
        back_populates="professional",
        cascade="all, delete-orphan",
        order_by="Review.created_at.desc()",
    )

    contact_clicks = db.relationship(
        "ContactClick",
        back_populates="professional",
        cascade="all, delete-orphan",
    )

    portfolio_items = db.relationship(
        "ProfessionalPortfolioItem",
        back_populates="professional",
        cascade="all, delete-orphan",
        order_by="ProfessionalPortfolioItem.sort_order.asc(), ProfessionalPortfolioItem.created_at.asc()",
    )

    @property
    def specialties(self):
        values = []
        if self.primary_specialty:
            values.append(self.primary_specialty.strip())
        if self.specialties_text:
            values.extend(
                item.strip()
                for item in self.specialties_text.split(",")
                if item.strip()
            )
        unique = []
        for item in values:
            if item.lower() not in {existing.lower() for existing in unique}:
                unique.append(item)
        return unique

    @property
    def active_memberships(self):
        return [item for item in self.memberships if item.status == "active"]

    @property
    def pending_memberships(self):
        return [item for item in self.memberships if item.status == "pending"]

    @property
    def profile_completion(self):
        checks = [
            bool(self.avatar_url),
            bool(self.display_name),
            bool(self.primary_specialty),
            bool(self.bio),
            bool(self.city and self.state),
            len(self.portfolio_items) >= 3,
        ]
        return round((sum(checks) / len(checks)) * 100)

    @property
    def ready_to_publish(self):
        return self.profile_completion == 100


class ProfessionalPortfolioItem(db.Model):
    __tablename__ = "professional_portfolio_items"

    id = db.Column(db.Integer, primary_key=True)
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey("professional_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(180), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    professional = db.relationship("ProfessionalProfile", back_populates="portfolio_items")
