"""Add professional weekly working hours.

Revision ID: o52j0f8g1b39
Revises: n41i9e7f0a28
Create Date: 2026-10-09
"""

from alembic import op
import sqlalchemy as sa


revision = "o52j0f8g1b39"
down_revision = "n41i9e7f0a28"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "professional_working_hours",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "professional_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "weekday",
            sa.SmallInteger(),
            nullable=False,
        ),
        sa.Column(
            "start_time",
            sa.Time(),
            nullable=False,
        ),
        sa.Column(
            "end_time",
            sa.Time(),
            nullable=False,
        ),
        sa.Column(
            "break_start_time",
            sa.Time(),
            nullable=True,
        ),
        sa.Column(
            "break_end_time",
            sa.Time(),
            nullable=True,
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
        sa.CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name=(
                "ck_professional_working_hours_"
                "weekday"
            ),
        ),
        sa.CheckConstraint(
            "start_time < end_time",
            name=(
                "ck_professional_working_hours_"
                "range"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "professional_id",
            "weekday",
            name=(
                "uq_professional_working_hours_"
                "professional_weekday"
            ),
        ),
    )
    op.create_index(
        "ix_professional_working_hours_professional_id",
        "professional_working_hours",
        ["professional_id"],
    )
    op.create_index(
        "ix_professional_working_hours_weekday",
        "professional_working_hours",
        ["weekday"],
    )


def downgrade():
    op.drop_index(
        "ix_professional_working_hours_weekday",
        table_name="professional_working_hours",
    )
    op.drop_index(
        "ix_professional_working_hours_professional_id",
        table_name="professional_working_hours",
    )
    op.drop_table(
        "professional_working_hours"
    )
