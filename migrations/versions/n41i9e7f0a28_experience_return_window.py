"""Add recommended return window to experiences.

Revision ID: n41i9e7f0a28
Revises: m30h8d6e9f17
Create Date: 2026-10-09
"""

from alembic import op
import sqlalchemy as sa


revision = "n41i9e7f0a28"
down_revision = "m30h8d6e9f17"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("experiences") as batch_op:
        batch_op.add_column(
            sa.Column(
                "recommended_return_days",
                sa.Integer(),
                nullable=True,
            )
        )


def downgrade():
    with op.batch_alter_table("experiences") as batch_op:
        batch_op.drop_column(
            "recommended_return_days"
        )
