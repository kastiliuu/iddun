"""professional experiences

Revision ID: i96d4f2a5b73
Revises: h85c3e1f4a62
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa


revision = "i96d4f2a5b73"
down_revision = "h85c3e1f4a62"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "professional_experiences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=False),
        sa.Column("establishment_id", sa.Integer(), nullable=True),
        sa.Column("company_name", sa.String(length=160), nullable=False),
        sa.Column("role_title", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("started_at", sa.Date(), nullable=False),
        sa.Column("ended_at", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column(
            "verification_status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id"],
            ["establishments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_professional_experiences_professional_id",
        "professional_experiences",
        ["professional_id"],
        unique=False,
    )
    op.create_index(
        "ix_professional_experiences_establishment_id",
        "professional_experiences",
        ["establishment_id"],
        unique=False,
    )
    op.create_index(
        "ix_professional_experiences_verification_status",
        "professional_experiences",
        ["verification_status"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_professional_experiences_verification_status",
        table_name="professional_experiences",
    )
    op.drop_index(
        "ix_professional_experiences_establishment_id",
        table_name="professional_experiences",
    )
    op.drop_index(
        "ix_professional_experiences_professional_id",
        table_name="professional_experiences",
    )
    op.drop_table("professional_experiences")
