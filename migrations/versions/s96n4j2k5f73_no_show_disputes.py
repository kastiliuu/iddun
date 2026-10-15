"""Auditable no-show disputes, without modifying existing bookings.

Revision ID: s96n4j2k5f73
Revises: r85m3i1j4e62
"""
from alembic import op
import sqlalchemy as sa

revision = "s96n4j2k5f73"
down_revision = "r85m3i1j4e62"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "booking_no_show_disputes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reviewer_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("evidence_reference", sa.String(500)),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("resolution_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'rejected')", name="ck_no_show_dispute_status"),
    )
    op.create_index("ix_booking_no_show_disputes_booking_id", "booking_no_show_disputes", ["booking_id"])
    op.create_index("ix_booking_no_show_disputes_status", "booking_no_show_disputes", ["status"])
    op.create_index("uq_pending_no_show_dispute", "booking_no_show_disputes", ["booking_id"], unique=True,
        postgresql_where=sa.text("status = 'pending'"), sqlite_where=sa.text("status = 'pending'"))


def downgrade():
    op.drop_index("uq_pending_no_show_dispute", table_name="booking_no_show_disputes")
    op.drop_index("ix_booking_no_show_disputes_status", table_name="booking_no_show_disputes")
    op.drop_index("ix_booking_no_show_disputes_booking_id", table_name="booking_no_show_disputes")
    op.drop_table("booking_no_show_disputes")
