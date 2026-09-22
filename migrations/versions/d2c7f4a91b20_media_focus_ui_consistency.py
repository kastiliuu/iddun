"""media focal points and ui consistency

Revision ID: d2c7f4a91b20
Revises: b7d2f9a1c410
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "d2c7f4a91b20"
down_revision = "b7d2f9a1c410"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "professional_profiles",
        sa.Column("avatar_focus_x", sa.SmallInteger(), nullable=False, server_default="50"),
    )
    op.add_column(
        "professional_profiles",
        sa.Column("avatar_focus_y", sa.SmallInteger(), nullable=False, server_default="50"),
    )
    op.add_column(
        "experiences",
        sa.Column("image_focus_x", sa.SmallInteger(), nullable=False, server_default="50"),
    )
    op.add_column(
        "experiences",
        sa.Column("image_focus_y", sa.SmallInteger(), nullable=False, server_default="50"),
    )


def downgrade():
    op.drop_column("experiences", "image_focus_y")
    op.drop_column("experiences", "image_focus_x")
    op.drop_column("professional_profiles", "avatar_focus_y")
    op.drop_column("professional_profiles", "avatar_focus_x")
