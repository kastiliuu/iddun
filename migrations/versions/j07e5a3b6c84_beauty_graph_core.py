"""beauty graph core

Revision ID: j07e5a3b6c84
Revises: i96d4f2a5b73
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa


revision = "j07e5a3b6c84"
down_revision = "i96d4f2a5b73"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "follows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=True),
        sa.Column("establishment_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "professional_id",
            name="uq_follow_user_professional",
        ),
        sa.UniqueConstraint(
            "user_id",
            "establishment_id",
            name="uq_follow_user_establishment",
        ),
    )

    op.create_index(
        "ix_follows_user_id",
        "follows",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_follows_target_type",
        "follows",
        ["target_type"],
        unique=False,
    )
    op.create_index(
        "ix_follows_professional_id",
        "follows",
        ["professional_id"],
        unique=False,
    )
    op.create_index(
        "ix_follows_establishment_id",
        "follows",
        ["establishment_id"],
        unique=False,
    )

    op.create_table(
        "saves",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=True),
        sa.Column("establishment_id", sa.Integer(), nullable=True),
        sa.Column("experience_id", sa.Integer(), nullable=True),
        sa.Column("portfolio_item_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
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
            name="ck_save_target_shape",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
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
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_item_id"],
            ["professional_portfolio_items.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "professional_id",
            name="uq_save_user_professional",
        ),
        sa.UniqueConstraint(
            "user_id",
            "establishment_id",
            name="uq_save_user_establishment",
        ),
        sa.UniqueConstraint(
            "user_id",
            "experience_id",
            name="uq_save_user_experience",
        ),
        sa.UniqueConstraint(
            "user_id",
            "portfolio_item_id",
            name="uq_save_user_portfolio_item",
        ),
    )

    op.create_index(
        "ix_saves_user_id",
        "saves",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_saves_target_type",
        "saves",
        ["target_type"],
        unique=False,
    )
    op.create_index(
        "ix_saves_professional_id",
        "saves",
        ["professional_id"],
        unique=False,
    )
    op.create_index(
        "ix_saves_establishment_id",
        "saves",
        ["establishment_id"],
        unique=False,
    )
    op.create_index(
        "ix_saves_experience_id",
        "saves",
        ["experience_id"],
        unique=False,
    )
    op.create_index(
        "ix_saves_portfolio_item_id",
        "saves",
        ["portfolio_item_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_saves_portfolio_item_id",
        table_name="saves",
    )
    op.drop_index(
        "ix_saves_experience_id",
        table_name="saves",
    )
    op.drop_index(
        "ix_saves_establishment_id",
        table_name="saves",
    )
    op.drop_index(
        "ix_saves_professional_id",
        table_name="saves",
    )
    op.drop_index(
        "ix_saves_target_type",
        table_name="saves",
    )
    op.drop_index(
        "ix_saves_user_id",
        table_name="saves",
    )
    op.drop_table("saves")

    op.drop_index(
        "ix_follows_establishment_id",
        table_name="follows",
    )
    op.drop_index(
        "ix_follows_professional_id",
        table_name="follows",
    )
    op.drop_index(
        "ix_follows_target_type",
        table_name="follows",
    )
    op.drop_index(
        "ix_follows_user_id",
        table_name="follows",
    )
    op.drop_table("follows")
