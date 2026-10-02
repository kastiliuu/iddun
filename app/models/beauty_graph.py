from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class FollowTarget:
    PROFESSIONAL = "professional"
    ESTABLISHMENT = "establishment"

    VALUES = (
        PROFESSIONAL,
        ESTABLISHMENT,
    )


class SaveTarget:
    PROFESSIONAL = "professional"
    ESTABLISHMENT = "establishment"
    EXPERIENCE = "experience"
    PORTFOLIO_ITEM = "portfolio_item"
    WORK_POST = "work_post"

    VALUES = (
        PROFESSIONAL,
        ESTABLISHMENT,
        EXPERIENCE,
        PORTFOLIO_ITEM,
        WORK_POST,
    )


class Follow(db.Model):
    __tablename__ = "follows"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    target_type = db.Column(
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
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    user = db.relationship(
        "User",
        back_populates="follows",
    )
    professional = db.relationship(
        "ProfessionalProfile"
    )
    establishment = db.relationship(
        "Establishment"
    )

    __table_args__ = (
        db.CheckConstraint(
            (
                "("
                "target_type = 'professional' "
                "AND professional_id IS NOT NULL "
                "AND establishment_id IS NULL"
                ") OR ("
                "target_type = 'establishment' "
                "AND establishment_id IS NOT NULL "
                "AND professional_id IS NULL"
                ")"
            ),
            name="ck_follow_target_shape",
        ),
        db.UniqueConstraint(
            "user_id",
            "professional_id",
            name="uq_follow_user_professional",
        ),
        db.UniqueConstraint(
            "user_id",
            "establishment_id",
            name="uq_follow_user_establishment",
        ),
    )


class Save(db.Model):
    __tablename__ = "saves"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    target_type = db.Column(
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
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    portfolio_item_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "professional_portfolio_items.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    work_post_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "work_posts.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    user = db.relationship(
        "User",
        back_populates="saves",
    )
    professional = db.relationship(
        "ProfessionalProfile"
    )
    establishment = db.relationship(
        "Establishment"
    )
    experience = db.relationship(
        "Experience"
    )
    portfolio_item = db.relationship(
        "ProfessionalPortfolioItem"
    )
    work_post = db.relationship(
        "WorkPost"
    )

    __table_args__ = (
        db.CheckConstraint(
            (
                "("
                "target_type = 'professional' "
                "AND professional_id IS NOT NULL "
                "AND establishment_id IS NULL "
                "AND experience_id IS NULL "
                "AND portfolio_item_id IS NULL "
                "AND work_post_id IS NULL"
                ") OR ("
                "target_type = 'establishment' "
                "AND establishment_id IS NOT NULL "
                "AND professional_id IS NULL "
                "AND experience_id IS NULL "
                "AND portfolio_item_id IS NULL "
                "AND work_post_id IS NULL"
                ") OR ("
                "target_type = 'experience' "
                "AND experience_id IS NOT NULL "
                "AND professional_id IS NULL "
                "AND establishment_id IS NULL "
                "AND portfolio_item_id IS NULL "
                "AND work_post_id IS NULL"
                ") OR ("
                "target_type = 'portfolio_item' "
                "AND portfolio_item_id IS NOT NULL "
                "AND professional_id IS NULL "
                "AND establishment_id IS NULL "
                "AND experience_id IS NULL "
                "AND work_post_id IS NULL"
                ") OR ("
                "target_type = 'work_post' "
                "AND work_post_id IS NOT NULL "
                "AND professional_id IS NULL "
                "AND establishment_id IS NULL "
                "AND experience_id IS NULL "
                "AND portfolio_item_id IS NULL"
                ")"
            ),
            name="ck_save_target_shape",
        ),
        db.UniqueConstraint(
            "user_id",
            "professional_id",
            name="uq_save_user_professional",
        ),
        db.UniqueConstraint(
            "user_id",
            "establishment_id",
            name="uq_save_user_establishment",
        ),
        db.UniqueConstraint(
            "user_id",
            "experience_id",
            name="uq_save_user_experience",
        ),
        db.UniqueConstraint(
            "user_id",
            "portfolio_item_id",
            name="uq_save_user_portfolio_item",
        ),
        db.UniqueConstraint(
            "user_id",
            "work_post_id",
            name="uq_save_user_work_post",
        ),
    )
