"""jobs and applications

Revision ID: m30h8d6e9f17
Revises: l29g7c5d8e06
Create Date: 2026-10-07
"""

from alembic import op
import sqlalchemy as sa


revision = "m30h8d6e9f17"
down_revision = "l29g7c5d8e06"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "job_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("establishment_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("specialty", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=80), nullable=True),
        sa.Column("neighborhood", sa.String(length=120), nullable=True),
        sa.Column("employment_type", sa.String(length=40), nullable=True),
        sa.Column("compensation_text", sa.String(length=180), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'closed')",
            name="ck_job_post_status",
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id"],
            ["establishments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_job_posts_establishment_id",
        "job_posts",
        ["establishment_id"],
        unique=False,
    )
    op.create_index(
        "ix_job_posts_specialty",
        "job_posts",
        ["specialty"],
        unique=False,
    )
    op.create_index(
        "ix_job_posts_city",
        "job_posts",
        ["city"],
        unique=False,
    )
    op.create_index(
        "ix_job_posts_status",
        "job_posts",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_job_posts_published_at",
        "job_posts",
        ["published_at"],
        unique=False,
    )
    op.create_index(
        "ix_job_posts_created_at",
        "job_posts",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "job_applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(length=1200), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('submitted', 'withdrawn')",
            name="ck_job_application_status",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["job_posts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "professional_id",
            name="uq_job_application_professional",
        ),
    )
    op.create_index(
        "ix_job_applications_job_id",
        "job_applications",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "ix_job_applications_professional_id",
        "job_applications",
        ["professional_id"],
        unique=False,
    )
    op.create_index(
        "ix_job_applications_status",
        "job_applications",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_job_applications_created_at",
        "job_applications",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_job_applications_created_at",
        table_name="job_applications",
    )
    op.drop_index(
        "ix_job_applications_status",
        table_name="job_applications",
    )
    op.drop_index(
        "ix_job_applications_professional_id",
        table_name="job_applications",
    )
    op.drop_index(
        "ix_job_applications_job_id",
        table_name="job_applications",
    )
    op.drop_table("job_applications")

    op.drop_index(
        "ix_job_posts_created_at",
        table_name="job_posts",
    )
    op.drop_index(
        "ix_job_posts_published_at",
        table_name="job_posts",
    )
    op.drop_index(
        "ix_job_posts_status",
        table_name="job_posts",
    )
    op.drop_index(
        "ix_job_posts_city",
        table_name="job_posts",
    )
    op.drop_index(
        "ix_job_posts_specialty",
        table_name="job_posts",
    )
    op.drop_index(
        "ix_job_posts_establishment_id",
        table_name="job_posts",
    )
    op.drop_table("job_posts")
