"""Cancellation requests: clients request, executors decide.

Revision ID: q74l2h0i3d51
Revises: p63k1g9h2c40
"""
from alembic import op
import sqlalchemy as sa

revision = "q74l2h0i3d51"
down_revision = "p63k1g9h2c40"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "booking_cancellation_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolution_reason", sa.String(255), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'withdrawn', 'executed')", name="ck_cancellation_request_status"),
    )
    op.create_index("ix_booking_cancellation_requests_booking_id", "booking_cancellation_requests", ["booking_id"])
    op.create_index("ix_booking_cancellation_requests_status", "booking_cancellation_requests", ["status"])
    op.create_index("ix_booking_cancellation_request_status", "booking_cancellation_requests", ["booking_id", "status"])


def downgrade():
    op.drop_index("ix_booking_cancellation_request_status", table_name="booking_cancellation_requests")
    op.drop_index("ix_booking_cancellation_requests_status", table_name="booking_cancellation_requests")
    op.drop_index("ix_booking_cancellation_requests_booking_id", table_name="booking_cancellation_requests")
    op.drop_table("booking_cancellation_requests")
