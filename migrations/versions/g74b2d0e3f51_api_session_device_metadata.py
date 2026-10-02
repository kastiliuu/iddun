"""api session device metadata

Revision ID: g74b2d0e3f51
Revises: f63a1c9d2e40
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa


revision = "g74b2d0e3f51"
down_revision = "f63a1c9d2e40"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        "api_sessions"
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "device_name",
                sa.String(length=120),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "platform",
                sa.String(length=32),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "last_seen_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_api_sessions_last_seen_at",
            ["last_seen_at"],
            unique=False,
        )

    op.execute(
        sa.text(
            """
            UPDATE api_sessions
            SET last_seen_at = created_at
            WHERE last_seen_at IS NULL
            """
        )
    )


def downgrade():
    with op.batch_alter_table(
        "api_sessions"
    ) as batch_op:
        batch_op.drop_index(
            "ix_api_sessions_last_seen_at"
        )
        batch_op.drop_column(
            "last_seen_at"
        )
        batch_op.drop_column(
            "platform"
        )
        batch_op.drop_column(
            "device_name"
        )
