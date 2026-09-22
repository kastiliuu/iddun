from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class ProfessionalCertification(db.Model):
    __tablename__ = "professional_certifications"

    id = db.Column(db.Integer, primary_key=True)
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey("professional_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(180), nullable=False)
    issuer = db.Column(db.String(180), nullable=False)
    issued_at = db.Column(db.Date, nullable=True)
    expires_at = db.Column(db.Date, nullable=True)
    credential_id = db.Column(db.String(180), nullable=True)
    verification_url = db.Column(db.String(500), nullable=True)
    document_url = db.Column(db.String(500), nullable=True)
    is_public = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    professional = db.relationship("ProfessionalProfile", back_populates="certifications")
