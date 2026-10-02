"""work posts

Revision ID: k18f6b4c7d95
Revises: j07e5a3b6c84
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa


revision = "k18f6b4c7d95"
down_revision = "j07e5a3b6c84"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "work_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("author_type", sa.String(length=32), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=True),
        sa.Column("establishment_id", sa.Integer(), nullable=True),
        sa.Column("experience_id", sa.Integer(), nullable=True),
        sa.Column("caption", sa.String(length=1200), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("image_focus_x", sa.SmallInteger(), nullable=False),
        sa.Column("image_focus_y", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            (
                "image_focus_x BETWEEN 0 AND 100 "
                "AND image_focus_y BETWEEN 0 AND 100"
            ),
            name="ck_work_post_focus_range",
        ),
        sa.CheckConstraint(
            (
                "status IN "
                "('draft', 'published', 'archived')"
            ),
            name="ck_work_post_status",
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id"],
            ["establishments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["experience_id"],
            ["experiences.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_work_posts_author_type",
        "work_posts",
        ["author_type"],
        unique=False,
    )
    op.create_index(
        "ix_work_posts_professional_id",
        "work_posts",
        ["professional_id"],
        unique=False,
    )
    op.create_index(
        "ix_work_posts_establishment_id",
        "work_posts",
        ["establishment_id"],
        unique=False,
    )
    op.create_index(
        "ix_work_posts_experience_id",
        "work_posts",
        ["experience_id"],
        unique=False,
    )
    op.create_index(
        "ix_work_posts_status",
        "work_posts",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_work_posts_published_at",
        "work_posts",
        ["published_at"],
        unique=False,
    )

    op.add_column(
        "saves",
        sa.Column(
            "work_post_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_saves_work_post_id_work_posts",
        "saves",
        "work_posts",
        ["work_post_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_saves_work_post_id",
        "saves",
        ["work_post_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_save_user_work_post",
        "saves",
        ["user_id", "work_post_id"],
    )
    op.drop_constraint(
        "ck_save_target_shape",
        "saves",
        type_="check",
    )
    op.create_check_constraint(
        "ck_save_target_shape",
        "saves",
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
    )


def downgrade():
    op.drop_constraint(
        "ck_save_target_shape",
        "saves",
        type_="check",
    )
    op.create_check_constraint(
        "ck_save_target_shape",
        "saves",
        (
            "("
            "target_type = 'professional' "
            "AND professional_id IS NOT NULL "
            "AND establishment_id IS NULL "
            "AND experience_id IS NULL "
            "AND portfolio_item_id IS NULL"
            ") OR ("
            "target_type = 'establishment' "
            "AND establishment_id IS NOT NULL "
            "AND professional_id IS NULL "
            "AND experience_id IS NULL "
            "AND portfolio_item_id IS NULL"
            ") OR ("
            "target_type = 'experience' "
            "AND experience_id IS NOT NULL "
            "AND professional_id IS NULL "
            "AND establishment_id IS NULL "
            "AND portfolio_item_id IS NULL"
            ") OR ("
            "target_type = 'portfolio_item' "
            "AND portfolio_item_id IS NOT NULL "
            "AND professional_id IS NULL "
            "AND establishment_id IS NULL "
            "AND experience_id IS NULL"
            ")"
        ),
    )
    op.drop_constraint(
        "uq_save_user_work_post",
        "saves",
        type_="unique",
    )
    op.drop_index(
        "ix_saves_work_post_id",
        table_name="saves",
    )
    op.drop_constraint(
        "fk_saves_work_post_id_work_posts",
        "saves",
        type_="foreignkey",
    )
    op.drop_column(
        "saves",
        "work_post_id",
    )
    op.drop_index(
        "ix_work_posts_published_at",
        table_name="work_posts",
    )
    op.drop_index(
        "ix_work_posts_status",
        table_name="work_posts",
    )
    op.drop_index(
        "ix_work_posts_experience_id",
        table_name="work_posts",
    )
    op.drop_index(
        "ix_work_posts_establishment_id",
        table_name="work_posts",
    )
    op.drop_index(
        "ix_work_posts_professional_id",
        table_name="work_posts",
    )
    op.drop_index(
        "ix_work_posts_author_type",
        table_name="work_posts",
    )
    op.drop_table("work_posts")
