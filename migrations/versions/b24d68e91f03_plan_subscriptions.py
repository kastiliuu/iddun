"""add plan subscriptions and change history

Revision ID: b24d68e91f03
Revises: a91c5e7d3b20
Create Date: 2026-09-28
"""

from alembic import op
import sqlalchemy as sa


revision = "b24d68e91f03"
down_revision = "a91c5e7d3b20"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "plan_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=True),
        sa.Column("establishment_id", sa.Integer(), nullable=True),
        sa.Column("plan_code", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("billing_cycle", sa.String(length=16), nullable=True),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("billing_provider", sa.String(length=32), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=190), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "("
            "professional_id IS NOT NULL "
            "AND establishment_id IS NULL "
            "AND plan_code IN ('essential', 'pro')"
            ") OR ("
            "professional_id IS NULL "
            "AND establishment_id IS NOT NULL "
            "AND plan_code IN ('essential', 'business')"
            ")",
            name="ck_plan_subscriptions_subject_and_plan",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'trialing', 'expired', 'canceled')",
            name="ck_plan_subscriptions_status",
        ),
        sa.CheckConstraint(
            "billing_cycle IS NULL OR billing_cycle IN ('monthly', 'annual')",
            name="ck_plan_subscriptions_billing_cycle",
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id"],
            ["establishments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "professional_id",
            name="uq_plan_subscriptions_professional",
        ),
        sa.UniqueConstraint(
            "establishment_id",
            name="uq_plan_subscriptions_establishment",
        ),
    )
    op.create_index(
        "ix_plan_subscriptions_status_period_end",
        "plan_subscriptions",
        ["status", "current_period_end"],
    )

    op.create_table(
        "plan_change_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("previous_plan_code", sa.String(length=24), nullable=True),
        sa.Column("new_plan_code", sa.String(length=24), nullable=False),
        sa.Column("previous_status", sa.String(length=24), nullable=True),
        sa.Column("new_status", sa.String(length=24), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["plan_subscriptions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_plan_change_events_subscription_id",
        "plan_change_events",
        ["subscription_id"],
    )
    op.create_index(
        "ix_plan_change_events_actor_user_id",
        "plan_change_events",
        ["actor_user_id"],
    )

    connection = op.get_bind()

    subscriptions = sa.table(
        "plan_subscriptions",
        sa.column("id", sa.Integer()),
        sa.column("professional_id", sa.Integer()),
        sa.column("establishment_id", sa.Integer()),
        sa.column("plan_code", sa.String()),
        sa.column("status", sa.String()),
        sa.column("source", sa.String()),
        sa.column("started_at", sa.DateTime(timezone=True)),
        sa.column("cancel_at_period_end", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    professionals = sa.table(
        "professional_profiles",
        sa.column("id", sa.Integer()),
    )
    establishments = sa.table(
        "establishments",
        sa.column("id", sa.Integer()),
    )

    professional_columns = [
        "professional_id",
        "plan_code",
        "status",
        "source",
        "started_at",
        "cancel_at_period_end",
        "created_at",
        "updated_at",
    ]
    connection.execute(
        sa.insert(subscriptions).from_select(
            professional_columns,
            sa.select(
                professionals.c.id,
                sa.literal("essential"),
                sa.literal("active"),
                sa.literal("system"),
                sa.func.current_timestamp(),
                sa.false(),
                sa.func.current_timestamp(),
                sa.func.current_timestamp(),
            ),
        )
    )

    establishment_columns = [
        "establishment_id",
        "plan_code",
        "status",
        "source",
        "started_at",
        "cancel_at_period_end",
        "created_at",
        "updated_at",
    ]
    connection.execute(
        sa.insert(subscriptions).from_select(
            establishment_columns,
            sa.select(
                establishments.c.id,
                sa.literal("essential"),
                sa.literal("active"),
                sa.literal("system"),
                sa.func.current_timestamp(),
                sa.false(),
                sa.func.current_timestamp(),
                sa.func.current_timestamp(),
            ),
        )
    )

    events = sa.table(
        "plan_change_events",
        sa.column("subscription_id", sa.Integer()),
        sa.column("previous_plan_code", sa.String()),
        sa.column("new_plan_code", sa.String()),
        sa.column("previous_status", sa.String()),
        sa.column("new_status", sa.String()),
        sa.column("source", sa.String()),
        sa.column("note", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    connection.execute(
        sa.insert(events).from_select(
            [
                "subscription_id",
                "previous_plan_code",
                "new_plan_code",
                "previous_status",
                "new_status",
                "source",
                "note",
                "created_at",
            ],
            sa.select(
                subscriptions.c.id,
                sa.null(),
                subscriptions.c.plan_code,
                sa.null(),
                subscriptions.c.status,
                sa.literal("system"),
                sa.literal("Migração inicial para IDDUN Essencial"),
                sa.func.current_timestamp(),
            ),
        )
    )


def downgrade():
    op.drop_index(
        "ix_plan_change_events_actor_user_id",
        table_name="plan_change_events",
    )
    op.drop_index(
        "ix_plan_change_events_subscription_id",
        table_name="plan_change_events",
    )
    op.drop_table("plan_change_events")

    op.drop_index(
        "ix_plan_subscriptions_status_period_end",
        table_name="plan_subscriptions",
    )
    op.drop_table("plan_subscriptions")