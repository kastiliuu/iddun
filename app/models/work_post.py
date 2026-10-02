from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class WorkPostAuthorType:
    PROFESSIONAL = "professional"
    ESTABLISHMENT = "establishment"

    VALUES = (
        PROFESSIONAL,
        ESTABLISHMENT,
    )


class WorkPostStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    VALUES = (
        DRAFT,
        PUBLISHED,
        ARCHIVED,
    )


class WorkPost(db.Model):
    __tablename__ = "work_posts"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )
    author_type = db.Column(
        db.String(32),
        nullable=False,
        index=True,
    )
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "professional_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    establishment_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "establishments.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    experience_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "experiences.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    caption = db.Column(
        db.String(1200),
        nullable=True,
    )
    image_url = db.Column(
        db.String(500),
        nullable=False,
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
    status = db.Column(
        db.String(24),
        nullable=False,
        default=WorkPostStatus.PUBLISHED,
        index=True,
    )
    published_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        default=utcnow,
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
        back_populates="work_posts",
    )
    establishment = db.relationship(
        "Establishment",
        back_populates="work_posts",
    )
    experience = db.relationship(
        "Experience",
        back_populates="work_posts",
    )

    __table_args__ = (
        db.CheckConstraint(
            (
                "("
                "author_type = 'professional' "
                "AND professional_id IS NOT NULL "
                "AND establishment_id IS NULL"
                ") OR ("
                "author_type = 'establishment' "
                "AND establishment_id IS NOT NULL "
                "AND professional_id IS NULL"
                ")"
            ),
            name="ck_work_post_author_shape",
        ),
        db.CheckConstraint(
            (
                "image_focus_x BETWEEN 0 AND 100 "
                "AND image_focus_y BETWEEN 0 AND 100"
            ),
            name="ck_work_post_focus_range",
        ),
        db.CheckConstraint(
            (
                "status IN "
                "('draft', 'published', 'archived')"
            ),
            name="ck_work_post_status",
        ),
    )
