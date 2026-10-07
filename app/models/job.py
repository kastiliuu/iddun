from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class JobPostStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"

    VALUES = (
        DRAFT,
        PUBLISHED,
        CLOSED,
    )


class JobApplicationStatus:
    SUBMITTED = "submitted"
    WITHDRAWN = "withdrawn"

    VALUES = (
        SUBMITTED,
        WITHDRAWN,
    )


class JobPost(db.Model):
    __tablename__ = "job_posts"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )
    establishment_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "establishments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    title = db.Column(
        db.String(160),
        nullable=False,
    )
    specialty = db.Column(
        db.String(120),
        nullable=True,
        index=True,
    )
    description = db.Column(
        db.Text,
        nullable=False,
    )
    city = db.Column(
        db.String(120),
        nullable=True,
        index=True,
    )
    state = db.Column(
        db.String(80),
        nullable=True,
    )
    neighborhood = db.Column(
        db.String(120),
        nullable=True,
    )
    employment_type = db.Column(
        db.String(40),
        nullable=True,
    )
    compensation_text = db.Column(
        db.String(180),
        nullable=True,
    )
    status = db.Column(
        db.String(24),
        nullable=False,
        default=JobPostStatus.DRAFT,
        index=True,
    )
    published_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    closed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    establishment = db.relationship(
        "Establishment",
        lazy="joined",
    )
    applications = db.relationship(
        "JobApplication",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('draft', 'published', 'closed')",
            name="ck_job_post_status",
        ),
    )


class JobApplication(db.Model):
    __tablename__ = "job_applications"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )
    job_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "job_posts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "professional_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    message = db.Column(
        db.String(1200),
        nullable=True,
    )
    status = db.Column(
        db.String(24),
        nullable=False,
        default=JobApplicationStatus.SUBMITTED,
        index=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    job = db.relationship(
        "JobPost",
        back_populates="applications",
    )
    professional = db.relationship(
        "ProfessionalProfile",
        lazy="joined",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "job_id",
            "professional_id",
            name="uq_job_application_professional",
        ),
        db.CheckConstraint(
            "status IN ('submitted', 'withdrawn')",
            name="ck_job_application_status",
        ),
    )
