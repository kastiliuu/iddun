"""Recruitment pilot per establishment and manager grants (V1 PR 3).

Revision ID: a74c1r2p2026
Revises: z63b0k1e2026

Approved by the owner on 19/11/2026 (Notion 08, V1-CONV-D05, resolving
A1-DEC-01/02 together with V1-CONV-D03/D04).

Upgrade (additive only):
- establishments.recruitment_enabled: NOT NULL, server default false. Only
  the IDDUN admin turns it on or off, with a reason.
- establishment_user_accesses.can_recruit: NOT NULL, server default false.
  The owner grants it to a manager; legacy managers get no automatic grant.
- recruitment_audit_events: who changed what, when and why.

Existing job posts and applications are untouched: published jobs stay
online (V1-CONV-D04); only new jobs need the pilot.

Downgrade: drops exactly what the upgrade created.
"""

from alembic import op
import sqlalchemy as sa

revision = "a74c1r2p2026"
down_revision = "z63b0k1e2026"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("establishments") as batch:
        batch.add_column(
            sa.Column("recruitment_enabled", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    with op.batch_alter_table("establishment_user_accesses") as batch:
        batch.add_column(
            sa.Column("can_recruit", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    op.create_table(
        "recruitment_audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "establishment_id",
            sa.Integer(),
            sa.ForeignKey(
                "establishments.id",
                name="fk_recruitment_audit_events_establishment_id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", name="fk_recruitment_audit_events_actor_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "subject_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", name="fk_recruitment_audit_events_subject_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action IN ('pilot_enabled', 'pilot_revoked', 'grant_given', 'grant_revoked')",
            name="ck_recruitment_audit_action",
        ),
    )
    op.create_index(
        "ix_recruitment_audit_events_establishment_id", "recruitment_audit_events", ["establishment_id"]
    )
    op.create_index(
        "ix_recruitment_audit_events_actor_user_id", "recruitment_audit_events", ["actor_user_id"]
    )


def downgrade():
    op.drop_index("ix_recruitment_audit_events_actor_user_id", table_name="recruitment_audit_events")
    op.drop_index("ix_recruitment_audit_events_establishment_id", table_name="recruitment_audit_events")
    op.drop_table("recruitment_audit_events")

    with op.batch_alter_table("establishment_user_accesses") as batch:
        batch.drop_column("can_recruit")

    with op.batch_alter_table("establishments") as batch:
        batch.drop_column("recruitment_enabled")
