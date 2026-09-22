"""google calendar v1 and ui polish data

Revision ID: b7d2f9a1c410
Revises: e4b19c7a2f10
Create Date: 2026-09-16 12:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "b7d2f9a1c410"
down_revision = "e4b19c7a2f10"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("establishments", sa.Column("logo_url", sa.String(length=500), nullable=True))

    op.create_table(
        "calendar_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("calendar_id", sa.String(length=255), nullable=True),
        sa.Column("calendar_name", sa.String(length=255), nullable=True),
        sa.Column("account_email", sa.String(length=255), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("sync_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("create_booking_events", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=32), nullable=True),
        sa.Column("last_sync_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["professional_id"], ["professional_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "professional_id",
            "provider",
            name="uq_calendar_connection_professional_provider",
        ),
    )
    op.create_index(
        "ix_calendar_connections_professional_id",
        "calendar_connections",
        ["professional_id"],
        unique=False,
    )
    op.create_index(
        "ix_calendar_connections_provider",
        "calendar_connections",
        ["provider"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_calendar_connections_provider", table_name="calendar_connections")
    op.drop_index("ix_calendar_connections_professional_id", table_name="calendar_connections")
    op.drop_table("calendar_connections")
    op.drop_column("establishments", "logo_url")
