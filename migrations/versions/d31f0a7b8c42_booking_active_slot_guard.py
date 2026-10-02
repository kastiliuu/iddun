"""booking active slot guard

Revision ID: d31f0a7b8c42
Revises: c51e6a8b7d42
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa


revision = "d31f0a7b8c42"
down_revision = "c51e6a8b7d42"
branch_labels = None
depends_on = None


ACTIVE_BOOKING_PREDICATE = (
    "status IN ('pending', 'confirmed')"
)


def upgrade():
    op.create_index(
        "uq_bookings_active_slot",
        "bookings",
        ["slot_id"],
        unique=True,
        postgresql_where=sa.text(
            ACTIVE_BOOKING_PREDICATE
        ),
        sqlite_where=sa.text(
            ACTIVE_BOOKING_PREDICATE
        ),
    )


def downgrade():
    op.drop_index(
        "uq_bookings_active_slot",
        table_name="bookings",
    )
