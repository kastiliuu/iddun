"""Add auditable rescheduling requests without rewriting bookings.

Revision ID: r85m3i1j4e62
Revises: q74l2h0i3d51
"""
from alembic import op
import sqlalchemy as sa

revision = "r85m3i1j4e62"
down_revision = "q74l2h0i3d51"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "booking_reschedule_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requested_slot_id", sa.Integer(), sa.ForeignKey("experience_slots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("original_slot_id", sa.Integer(), sa.ForeignKey("experience_slots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("resolved_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("reason", sa.String(255)),
        sa.Column("resolution_reason", sa.String(255)),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('pending', 'withdrawn', 'executed', 'rejected')", name="ck_reschedule_request_status"),
    )
    op.create_index("ix_booking_reschedule_requests_booking_id", "booking_reschedule_requests", ["booking_id"])
    op.create_index("ix_booking_reschedule_requests_status", "booking_reschedule_requests", ["status"])
    op.create_index("uq_pending_reschedule_per_booking", "booking_reschedule_requests", ["booking_id"], unique=True,
                    postgresql_where=sa.text("status = 'pending'"), sqlite_where=sa.text("status = 'pending'"))


def downgrade():
    op.drop_index("uq_pending_reschedule_per_booking", table_name="booking_reschedule_requests")
    op.drop_index("ix_booking_reschedule_requests_status", table_name="booking_reschedule_requests")
    op.drop_index("ix_booking_reschedule_requests_booking_id", table_name="booking_reschedule_requests")
    op.drop_table("booking_reschedule_requests")
