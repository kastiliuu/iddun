"""create revocable API sessions

Revision ID: c51e6a8b7d42
Revises: b24d68e91f03
Create Date: 2026-09-29
"""

from alembic import op
import sqlalchemy as sa


revision = "c51e6a8b7d42"
down_revision = "b24d68e91f03"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "api_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "access_token_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "refresh_token_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "access_expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "refresh_expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_api_sessions_user_id",
        "api_sessions",
        ["user_id"],
    )
    op.create_index(
        "ix_api_sessions_access_token_hash",
        "api_sessions",
        ["access_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_api_sessions_refresh_token_hash",
        "api_sessions",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_api_sessions_refresh_expires_at",
        "api_sessions",
        ["refresh_expires_at"],
    )


def downgrade():
    op.drop_index(
        "ix_api_sessions_refresh_expires_at",
        table_name="api_sessions",
    )
    op.drop_index(
        "ix_api_sessions_refresh_token_hash",
        table_name="api_sessions",
    )
    op.drop_index(
        "ix_api_sessions_access_token_hash",
        table_name="api_sessions",
    )
    op.drop_index(
        "ix_api_sessions_user_id",
        table_name="api_sessions",
    )
    op.drop_table("api_sessions")