"""Booking events trail and no-show tolerance per establishment (V1 PR 2).

Revision ID: z63b0k1e2026
Revises: y52f0l1w2026

Approved by the owner on 17/11/2026 (Notion 08, V1-CONV-D02, applying
D-NV07-01/02/03).

Upgrade (additive only):
- New table booking_events: who did what to a booking (cancelled,
  completed, no_show), in which role (executor or admin), why and when.
- establishments.no_show_tolerance_minutes, NOT NULL with server default
  15, so every existing row gets 15 without a data rewrite; a check keeps
  it between 0 and 60.

Downgrade: drops exactly what the upgrade created. Existing bookings and
establishments are untouched either way.
"""

from alembic import op
import sqlalchemy as sa

revision = "z63b0k1e2026"
down_revision = "y52f0l1w2026"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "booking_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.Integer(),
            sa.ForeignKey("bookings.id", name="fk_booking_events_booking_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", name="fk_booking_events_actor_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_role", sa.String(length=16), nullable=False),
        sa.Column("action", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action IN ('cancelled', 'completed', 'no_show')",
            name="ck_booking_event_action",
        ),
        sa.CheckConstraint(
            "actor_role IN ('executor', 'admin')",
            name="ck_booking_event_actor_role",
        ),
    )
    op.create_index("ix_booking_events_booking_id", "booking_events", ["booking_id"])
    op.create_index("ix_booking_events_actor_user_id", "booking_events", ["actor_user_id"])

    with op.batch_alter_table("establishments") as batch:
        batch.add_column(
            sa.Column(
                "no_show_tolerance_minutes",
                sa.SmallInteger(),
                nullable=False,
                server_default="15",
            )
        )
        batch.create_check_constraint(
            "ck_establishment_no_show_tolerance",
            "no_show_tolerance_minutes BETWEEN 0 AND 60",
        )


def downgrade():
    with op.batch_alter_table("establishments") as batch:
        batch.drop_constraint("ck_establishment_no_show_tolerance", type_="check")
        batch.drop_column("no_show_tolerance_minutes")

    op.drop_index("ix_booking_events_actor_user_id", table_name="booking_events")
    op.drop_index("ix_booking_events_booking_id", table_name="booking_events")
    op.drop_table("booking_events")
