"""professional and business self-service foundation

Revision ID: e7f6a3b92c11
Revises: d2c7f4a91b20
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa


revision = "e7f6a3b92c11"
down_revision = "d2c7f4a91b20"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("professional_profiles") as batch_op:
        batch_op.add_column(sa.Column("headline", sa.String(length=180), nullable=True))
        batch_op.add_column(sa.Column("specialties_text", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("cover_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("visual_theme", sa.String(length=24), nullable=False, server_default="beauty"))
        batch_op.add_column(sa.Column("plan_tier", sa.String(length=24), nullable=False, server_default="free"))
        batch_op.add_column(sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("establishments") as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("visual_theme", sa.String(length=24), nullable=False, server_default="beauty"))
        batch_op.add_column(sa.Column("plan_tier", sa.String(length=24), nullable=False, server_default="free"))
        batch_op.add_column(sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("cover_url", sa.String(length=500), nullable=True))

    op.create_table(
        "professional_portfolio_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("professional_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("caption", sa.String(length=180), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["professional_id"], ["professional_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_professional_portfolio_items_professional_id",
        "professional_portfolio_items",
        ["professional_id"],
        unique=False,
    )

    op.create_table(
        "establishment_gallery_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("establishment_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("caption", sa.String(length=180), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["establishment_id"], ["establishments.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_establishment_gallery_items_establishment_id",
        "establishment_gallery_items",
        ["establishment_id"],
        unique=False,
    )

    op.create_table(
        "establishment_user_accesses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("establishment_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False, server_default="manager"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["establishment_id"], ["establishments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "establishment_id", name="uq_establishment_user_access"),
    )
    op.create_index(
        "ix_establishment_user_accesses_user_id",
        "establishment_user_accesses",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_establishment_user_accesses_establishment_id",
        "establishment_user_accesses",
        ["establishment_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_establishment_user_accesses_establishment_id", table_name="establishment_user_accesses")
    op.drop_index("ix_establishment_user_accesses_user_id", table_name="establishment_user_accesses")
    op.drop_table("establishment_user_accesses")

    op.drop_index("ix_establishment_gallery_items_establishment_id", table_name="establishment_gallery_items")
    op.drop_table("establishment_gallery_items")

    op.drop_index("ix_professional_portfolio_items_professional_id", table_name="professional_portfolio_items")
    op.drop_table("professional_portfolio_items")

    with op.batch_alter_table("establishments") as batch_op:
        batch_op.drop_column("cover_url")
        batch_op.drop_column("published_at")
        batch_op.drop_column("onboarding_completed")
        batch_op.drop_column("plan_tier")
        batch_op.drop_column("visual_theme")
        batch_op.drop_column("category")

    with op.batch_alter_table("professional_profiles") as batch_op:
        batch_op.drop_column("published_at")
        batch_op.drop_column("onboarding_completed")
        batch_op.drop_column("plan_tier")
        batch_op.drop_column("visual_theme")
        batch_op.drop_column("cover_url")
        batch_op.drop_column("specialties_text")
        batch_op.drop_column("headline")
