"""core profiles v1

Revision ID: c9b7e12d4a10
Revises: a14c14f8493c
Create Date: 2026-09-15 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c9b7e12d4a10"
down_revision = "a14c14f8493c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "client_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_client_profiles_user_id", "client_profiles", ["user_id"], unique=True)

    op.create_table(
        "professional_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("display_name", sa.String(length=140), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("primary_specialty", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("instagram", sa.String(length=120), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_professional_profiles_slug", "professional_profiles", ["slug"], unique=True)
    op.create_index("ix_professional_profiles_user_id", "professional_profiles", ["user_id"], unique=True)

    op.create_table(
        "establishments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=190), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("instagram", sa.String(length=120), nullable=True),
        sa.Column("address_line1", sa.String(length=180), nullable=True),
        sa.Column("address_line2", sa.String(length=120), nullable=True),
        sa.Column("neighborhood", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("postal_code", sa.String(length=16), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_establishments_slug", "establishments", ["slug"], unique=True)

    op.create_table(
        "professional_establishment_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=False),
        sa.Column("establishment_id", sa.Integer(), nullable=False),
        sa.Column("role_name", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.Date(), nullable=True),
        sa.Column("ended_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["establishment_id"], ["establishments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["professional_id"], ["professional_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_membership_professional_establishment",
        "professional_establishment_memberships",
        ["professional_id", "establishment_id"],
        unique=False,
    )
    op.create_index(
        "ix_professional_establishment_memberships_establishment_id",
        "professional_establishment_memberships",
        ["establishment_id"],
        unique=False,
    )
    op.create_index(
        "ix_professional_establishment_memberships_professional_id",
        "professional_establishment_memberships",
        ["professional_id"],
        unique=False,
    )
    op.create_index(
        "ix_professional_establishment_memberships_status",
        "professional_establishment_memberships",
        ["status"],
        unique=False,
    )

    # Existing client users receive a profile automatically.
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO client_profiles
                (user_id, onboarding_completed, created_at, updated_at)
            SELECT id, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM users
            WHERE role = 'client'
              AND NOT EXISTS (
                  SELECT 1 FROM client_profiles cp WHERE cp.user_id = users.id
              )
            """
        )
    )


def downgrade():
    op.drop_index(
        "ix_professional_establishment_memberships_status",
        table_name="professional_establishment_memberships",
    )
    op.drop_index(
        "ix_professional_establishment_memberships_professional_id",
        table_name="professional_establishment_memberships",
    )
    op.drop_index(
        "ix_professional_establishment_memberships_establishment_id",
        table_name="professional_establishment_memberships",
    )
    op.drop_index(
        "ix_membership_professional_establishment",
        table_name="professional_establishment_memberships",
    )
    op.drop_table("professional_establishment_memberships")

    op.drop_index("ix_establishments_slug", table_name="establishments")
    op.drop_table("establishments")

    op.drop_index("ix_professional_profiles_user_id", table_name="professional_profiles")
    op.drop_index("ix_professional_profiles_slug", table_name="professional_profiles")
    op.drop_table("professional_profiles")

    op.drop_index("ix_client_profiles_user_id", table_name="client_profiles")
    op.drop_table("client_profiles")
