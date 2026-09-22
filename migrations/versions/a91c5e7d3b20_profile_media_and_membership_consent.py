"""profile media focus and membership consent

Revision ID: a91c5e7d3b20
Revises: f8a14d6c2e31
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "a91c5e7d3b20"
down_revision = "f8a14d6c2e31"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("professional_profiles") as batch_op:
        batch_op.add_column(sa.Column("cover_focus_x", sa.SmallInteger(), nullable=False, server_default="50"))
        batch_op.add_column(sa.Column("cover_focus_y", sa.SmallInteger(), nullable=False, server_default="50"))

    with op.batch_alter_table("establishments") as batch_op:
        batch_op.add_column(sa.Column("logo_focus_x", sa.SmallInteger(), nullable=False, server_default="50"))
        batch_op.add_column(sa.Column("logo_focus_y", sa.SmallInteger(), nullable=False, server_default="50"))
        batch_op.add_column(sa.Column("cover_focus_x", sa.SmallInteger(), nullable=False, server_default="50"))
        batch_op.add_column(sa.Column("cover_focus_y", sa.SmallInteger(), nullable=False, server_default="50"))


def downgrade():
    with op.batch_alter_table("establishments") as batch_op:
        batch_op.drop_column("cover_focus_y")
        batch_op.drop_column("cover_focus_x")
        batch_op.drop_column("logo_focus_y")
        batch_op.drop_column("logo_focus_x")

    with op.batch_alter_table("professional_profiles") as batch_op:
        batch_op.drop_column("cover_focus_y")
        batch_op.drop_column("cover_focus_x")
