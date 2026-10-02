from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class MembershipStatus:
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    INACTIVE = "inactive"


class EstablishmentAccessRole:
    OWNER = "owner"
    MANAGER = "manager"


class EstablishmentAccessStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"


class Establishment(db.Model):
    __tablename__ = "establishments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(190), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(64), nullable=True)
    visual_theme = db.Column(db.String(24), nullable=False, default="beauty")
    plan_tier = db.Column(db.String(24), nullable=False, default="free")
    onboarding_completed = db.Column(db.Boolean, nullable=False, default=False)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)
    phone = db.Column(db.String(32), nullable=True)
    whatsapp_enabled = db.Column(db.Boolean, nullable=False, default=True)
    email = db.Column(db.String(255), nullable=True)
    instagram = db.Column(db.String(120), nullable=True)
    address_line1 = db.Column(db.String(180), nullable=True)
    address_line2 = db.Column(db.String(120), nullable=True)
    neighborhood = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(2), nullable=True)
    postal_code = db.Column(db.String(16), nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    cover_url = db.Column(db.String(500), nullable=True)
    logo_focus_x = db.Column(db.SmallInteger, nullable=False, default=50)
    logo_focus_y = db.Column(db.SmallInteger, nullable=False, default=50)
    cover_focus_x = db.Column(db.SmallInteger, nullable=False, default=50)
    cover_focus_y = db.Column(db.SmallInteger, nullable=False, default=50)
    latitude = db.Column(db.Numeric(10, 7), nullable=True)
    longitude = db.Column(db.Numeric(10, 7), nullable=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    timezone = db.Column(db.String(64), nullable=False, default="America/Sao_Paulo")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    experiences = db.relationship(
        "Experience",
        back_populates="establishment",
        lazy="selectin",
    )

    slots = db.relationship(
        "ExperienceSlot",
        back_populates="establishment",
        order_by="ExperienceSlot.starts_at.asc()",
    )

    bookings = db.relationship(
        "Booking",
        back_populates="establishment",
        order_by="Booking.created_at.desc()",
    )

    memberships = db.relationship(
        "ProfessionalEstablishmentMembership",
        back_populates="establishment",
        cascade="all, delete-orphan",
        order_by="ProfessionalEstablishmentMembership.created_at.desc()",
    )

    user_accesses = db.relationship(
        "EstablishmentUserAccess",
        back_populates="establishment",
        cascade="all, delete-orphan",
        order_by="EstablishmentUserAccess.created_at.asc()",
    )

    reviews_received = db.relationship(
        "Review",
        back_populates="establishment",
        cascade="all, delete-orphan",
        order_by="Review.created_at.desc()",
    )

    contact_clicks = db.relationship(
        "ContactClick",
        back_populates="establishment",
        cascade="all, delete-orphan",
    )

    gallery_items = db.relationship(
        "EstablishmentGalleryItem",
        back_populates="establishment",
        cascade="all, delete-orphan",
        order_by="EstablishmentGalleryItem.sort_order.asc(), EstablishmentGalleryItem.created_at.asc()",
    )

    @property
    def active_memberships(self):
        return [item for item in self.memberships if item.status == MembershipStatus.ACTIVE]

    @property
    def pending_memberships(self):
        return [item for item in self.memberships if item.status == MembershipStatus.PENDING]

    @property
    def profile_completion(self):
        checks = [
            bool(self.logo_url),
            bool(self.name),
            bool(self.description),
            bool(self.category),
            bool(self.city and self.state),
            bool(self.address_line1),
        ]
        return round((sum(checks) / len(checks)) * 100)

    @property
    def ready_to_publish(self):
        return self.profile_completion == 100


class EstablishmentUserAccess(db.Model):
    __tablename__ = "establishment_user_accesses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    establishment_id = db.Column(
        db.Integer,
        db.ForeignKey("establishments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = db.Column(db.String(24), nullable=False, default=EstablishmentAccessRole.MANAGER)
    status = db.Column(db.String(24), nullable=False, default=EstablishmentAccessStatus.ACTIVE)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="establishment_accesses")
    establishment = db.relationship("Establishment", back_populates="user_accesses")

    __table_args__ = (
        db.UniqueConstraint("user_id", "establishment_id", name="uq_establishment_user_access"),
    )


class EstablishmentGalleryItem(db.Model):
    __tablename__ = "establishment_gallery_items"

    id = db.Column(db.Integer, primary_key=True)
    establishment_id = db.Column(
        db.Integer,
        db.ForeignKey("establishments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(180), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    establishment = db.relationship("Establishment", back_populates="gallery_items")


class ProfessionalEstablishmentMembership(db.Model):
    __tablename__ = "professional_establishment_memberships"

    id = db.Column(db.Integer, primary_key=True)
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey("professional_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    establishment_id = db.Column(
        db.Integer,
        db.ForeignKey("establishments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_name = db.Column(db.String(120), nullable=True)
    status = db.Column(
        db.String(24),
        nullable=False,
        default=MembershipStatus.PENDING,
        index=True,
    )
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    started_at = db.Column(db.Date, nullable=True)
    ended_at = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    professional = db.relationship("ProfessionalProfile", back_populates="memberships")
    establishment = db.relationship("Establishment", back_populates="memberships")

    __table_args__ = (
        db.UniqueConstraint(
            "professional_id",
            "establishment_id",
            name="uq_membership_professional_establishment",
        ),
    )
