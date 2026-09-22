"""opportunities and booking v1

Revision ID: e4b19c7a2f10
Revises: f31c9a72d6e4
Create Date: 2026-09-15 16:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e4b19c7a2f10"
down_revision = "f31c9a72d6e4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "professional_profiles",
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="America/Sao_Paulo",
        ),
    )
    op.add_column(
        "professional_profiles",
        sa.Column(
            "default_booking_cutoff_minutes",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
    )
    op.add_column(
        "establishments",
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="America/Sao_Paulo",
        ),
    )
    op.add_column(
        "experiences",
        sa.Column("booking_cutoff_minutes", sa.Integer(), nullable=True),
    )

    op.create_table(
        "experience_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experience_id", sa.Integer(), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=False),
        sa.Column("establishment_id", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("booking_cutoff_minutes", sa.Integer(), nullable=True),
        sa.Column("hold_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_calendar_provider", sa.String(length=32), nullable=True),
        sa.Column("external_event_id", sa.String(length=255), nullable=True),
        sa.Column("external_block_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["establishment_id"], ["establishments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["experience_id"], ["experiences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["professional_id"], ["professional_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experience_slots_experience_id", "experience_slots", ["experience_id"], unique=False)
    op.create_index("ix_experience_slots_professional_id", "experience_slots", ["professional_id"], unique=False)
    op.create_index("ix_experience_slots_establishment_id", "experience_slots", ["establishment_id"], unique=False)
    op.create_index("ix_experience_slots_starts_at", "experience_slots", ["starts_at"], unique=False)
    op.create_index("ix_experience_slots_status", "experience_slots", ["status"], unique=False)
    op.create_index("ix_experience_slots_hold_expires_at", "experience_slots", ["hold_expires_at"], unique=False)
    op.create_index(
        "ix_experience_slots_professional_window",
        "experience_slots",
        ["professional_id", "starts_at", "ends_at"],
        unique=False,
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("experience_id", sa.Integer(), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=False),
        sa.Column("establishment_id", sa.Integer(), nullable=True),
        sa.Column("slot_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("price_at_booking", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("hold_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("no_show_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["client_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["establishment_id"], ["establishments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["experience_id"], ["experiences.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["professional_id"], ["professional_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["slot_id"], ["experience_slots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookings_client_id", "bookings", ["client_id"], unique=False)
    op.create_index("ix_bookings_experience_id", "bookings", ["experience_id"], unique=False)
    op.create_index("ix_bookings_professional_id", "bookings", ["professional_id"], unique=False)
    op.create_index("ix_bookings_establishment_id", "bookings", ["establishment_id"], unique=False)
    op.create_index("ix_bookings_slot_id", "bookings", ["slot_id"], unique=False)
    op.create_index("ix_bookings_status", "bookings", ["status"], unique=False)
    op.create_index("ix_bookings_hold_expires_at", "bookings", ["hold_expires_at"], unique=False)


def downgrade():
    op.drop_index("ix_bookings_hold_expires_at", table_name="bookings")
    op.drop_index("ix_bookings_status", table_name="bookings")
    op.drop_index("ix_bookings_slot_id", table_name="bookings")
    op.drop_index("ix_bookings_establishment_id", table_name="bookings")
    op.drop_index("ix_bookings_professional_id", table_name="bookings")
    op.drop_index("ix_bookings_experience_id", table_name="bookings")
    op.drop_index("ix_bookings_client_id", table_name="bookings")
    op.drop_table("bookings")

    op.drop_index("ix_experience_slots_professional_window", table_name="experience_slots")
    op.drop_index("ix_experience_slots_hold_expires_at", table_name="experience_slots")
    op.drop_index("ix_experience_slots_status", table_name="experience_slots")
    op.drop_index("ix_experience_slots_starts_at", table_name="experience_slots")
    op.drop_index("ix_experience_slots_establishment_id", table_name="experience_slots")
    op.drop_index("ix_experience_slots_professional_id", table_name="experience_slots")
    op.drop_index("ix_experience_slots_experience_id", table_name="experience_slots")
    op.drop_table("experience_slots")

    op.drop_column("experiences", "booking_cutoff_minutes")
    op.drop_column("establishments", "timezone")
    op.drop_column("professional_profiles", "default_booking_cutoff_minutes")
    op.drop_column("professional_profiles", "timezone")
