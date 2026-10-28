"""Add optional business operation and hours schema (NV-07A1-M).

Revision ID: u18n7a1m2026
Revises: t07m0d4l1t16

Expand-only: no defaults, no backfill, and no changes to publication flags.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "u18n7a1m2026"
down_revision = "t07m0d4l1t16"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "establishments",
        sa.Column("operation_mode", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "establishments",
        sa.Column("business_hours_mode", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "establishments",
        sa.Column(
            "business_hours",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
    )


def downgrade():
    # Destructive once new data is stored. Production rollback should first
    # revert application code, leaving the optional columns intact.
    # Physical downgrade requires an approved backup and explicit authorization.
    op.drop_column("establishments", "business_hours")
    op.drop_column("establishments", "business_hours_mode")
    op.drop_column("establishments", "operation_mode")
