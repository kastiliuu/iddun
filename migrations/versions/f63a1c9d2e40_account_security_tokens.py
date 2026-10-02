"""account security tokens and email verification

Revision ID: f63a1c9d2e40
Revises: e52c9b4d7a11
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa


revision = "f63a1c9d2e40"
down_revision = "e52c9b4d7a11"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        "users"
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "email_verified_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

    op.create_table(
        "account_tokens",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "purpose",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "token_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "consumed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "purpose IN "
                "('password_reset', 'email_verification')"
            ),
            name="ck_account_token_purpose",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_account_tokens_user_id",
        "account_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_account_tokens_purpose",
        "account_tokens",
        ["purpose"],
        unique=False,
    )
    op.create_index(
        "ix_account_tokens_token_hash",
        "account_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_account_tokens_expires_at",
        "account_tokens",
        ["expires_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_account_tokens_expires_at",
        table_name="account_tokens",
    )
    op.drop_index(
        "ix_account_tokens_token_hash",
        table_name="account_tokens",
    )
    op.drop_index(
        "ix_account_tokens_purpose",
        table_name="account_tokens",
    )
    op.drop_index(
        "ix_account_tokens_user_id",
        table_name="account_tokens",
    )
    op.drop_table(
        "account_tokens"
    )

    with op.batch_alter_table(
        "users"
    ) as batch_op:
        batch_op.drop_column(
            "email_verified_at"
        )
