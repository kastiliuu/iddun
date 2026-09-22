"""admin catalog v1

Revision ID: f31c9a72d6e4
Revises: c9b7e12d4a10
Create Date: 2026-09-15 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f31c9a72d6e4"
down_revision = "c9b7e12d4a10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "experiences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=False),
        sa.Column("establishment_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=190), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("short_description", sa.String(length=220), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("badge", sa.String(length=80), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("regular_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("is_first_experience", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["establishment_id"], ["establishments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["professional_id"], ["professional_profiles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiences_category", "experiences", ["category"], unique=False)
    op.create_index("ix_experiences_establishment_id", "experiences", ["establishment_id"], unique=False)
    op.create_index("ix_experiences_professional_id", "experiences", ["professional_id"], unique=False)
    op.create_index("ix_experiences_slug", "experiences", ["slug"], unique=True)
    op.create_index("ix_experiences_status", "experiences", ["status"], unique=False)


def downgrade():
    op.drop_index("ix_experiences_status", table_name="experiences")
    op.drop_index("ix_experiences_slug", table_name="experiences")
    op.drop_index("ix_experiences_professional_id", table_name="experiences")
    op.drop_index("ix_experiences_establishment_id", table_name="experiences")
    op.drop_index("ix_experiences_category", table_name="experiences")
    op.drop_table("experiences")
