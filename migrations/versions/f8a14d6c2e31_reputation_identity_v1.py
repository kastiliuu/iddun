"""reputation, whatsapp contact and certifications

Revision ID: f8a14d6c2e31
Revises: e7f6a3b92c11
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "f8a14d6c2e31"
down_revision = "e7f6a3b92c11"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("professional_profiles") as batch_op:
        batch_op.add_column(
            sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default=sa.true())
        )

    with op.batch_alter_table("establishments") as batch_op:
        batch_op.add_column(
            sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default=sa.true())
        )

    op.create_table(
        "professional_certifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("professional_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("issuer", sa.String(length=180), nullable=False),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("credential_id", sa.String(length=180), nullable=True),
        sa.Column("verification_url", sa.String(length=500), nullable=True),
        sa.Column("document_url", sa.String(length=500), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["professional_id"], ["professional_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_professional_certifications_professional_id",
        "professional_certifications",
        ["professional_id"],
        unique=False,
    )

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=24), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=True),
        sa.Column("establishment_id", sa.Integer(), nullable=True),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("recommended", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_1_5"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["client_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["professional_id"], ["professional_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["establishment_id"], ["establishments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("booking_id", "target_type", name="uq_review_booking_target"),
    )
    for name in ["booking_id", "client_id", "target_type", "professional_id", "establishment_id", "is_visible"]:
        op.create_index(f"ix_reviews_{name}", "reviews", [name], unique=False)

    op.create_table(
        "contact_clicks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("professional_id", sa.Integer(), nullable=True),
        sa.Column("establishment_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False, server_default="whatsapp"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["professional_id"], ["professional_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["establishment_id"], ["establishments.id"], ondelete="CASCADE"),
    )
    for name in ["user_id", "professional_id", "establishment_id", "channel", "created_at"]:
        op.create_index(f"ix_contact_clicks_{name}", "contact_clicks", [name], unique=False)


def downgrade():
    for name in ["created_at", "channel", "establishment_id", "professional_id", "user_id"]:
        op.drop_index(f"ix_contact_clicks_{name}", table_name="contact_clicks")
    op.drop_table("contact_clicks")

    for name in ["is_visible", "establishment_id", "professional_id", "target_type", "client_id", "booking_id"]:
        op.drop_index(f"ix_reviews_{name}", table_name="reviews")
    op.drop_table("reviews")

    op.drop_index("ix_professional_certifications_professional_id", table_name="professional_certifications")
    op.drop_table("professional_certifications")

    with op.batch_alter_table("establishments") as batch_op:
        batch_op.drop_column("whatsapp_enabled")

    with op.batch_alter_table("professional_profiles") as batch_op:
        batch_op.drop_column("whatsapp_enabled")
