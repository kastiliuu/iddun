from datetime import date, datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class ProfessionalExperienceVerification:
    UNVERIFIED = "unverified"
    VERIFIED_MEMBERSHIP = "verified_membership"


class ProfessionalExperience(db.Model):
    __tablename__ = "professional_experiences"

    id = db.Column(db.Integer, primary_key=True)
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
    company_name = db.Column(db.String(160), nullable=False)
    role_title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.Date, nullable=False)
    ended_at = db.Column(db.Date, nullable=True)
    is_current = db.Column(db.Boolean, nullable=False, default=False)
    verification_status = db.Column(
        db.String(32),
        nullable=False,
        default=ProfessionalExperienceVerification.UNVERIFIED,
        index=True,
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
        back_populates="professional_experiences",
    )
    establishment = db.relationship("Establishment")

    @property
    def verified(self):
        return (
            self.verification_status
            == ProfessionalExperienceVerification.VERIFIED_MEMBERSHIP
        )

    def normalize_dates(self):
        if self.is_current:
            self.ended_at = None

        if self.ended_at and self.ended_at < self.started_at:
            raise ValueError(
                "A data final não pode ser anterior à data inicial."
            )

        if self.started_at > date.today():
            raise ValueError(
                "A data inicial não pode estar no futuro."
            )
