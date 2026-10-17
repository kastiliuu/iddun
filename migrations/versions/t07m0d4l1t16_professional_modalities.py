"""Add optional professional attendance modalities.

Revision ID: t07m0d4l1t16
Revises: s96n4j2k5f73
"""
from alembic import op
import sqlalchemy as sa

revision = "t07m0d4l1t16"
down_revision = "s96n4j2k5f73"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "professional_profiles",
        sa.Column("attendance_modalities", sa.String(length=120), nullable=True),
    )


def downgrade():
    op.drop_column("professional_profiles", "attendance_modalities")
