"""account deletion marker

Revision ID: h85c3e1f4a62
Revises: g74b2d0e3f51
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa


revision = "h85c3e1f4a62"
down_revision = "g74b2d0e3f51"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        "users"
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "deleted_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_users_deleted_at",
            ["deleted_at"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table(
        "users"
    ) as batch_op:
        batch_op.drop_index(
            "ix_users_deleted_at"
        )
        batch_op.drop_column(
            "deleted_at"
        )
