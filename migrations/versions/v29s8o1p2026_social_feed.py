"""Social feed V0: client authors, carousel, likes, comments, reports (PR 3).

Revision ID: v29s8o1p2026
Revises: u18n7a1m2026

Approved plan D-SOC-08 (03/11/2026). Expand-only:
- work_posts gains client_profile_id, created_by_user_id and removed_at;
  image_url becomes optional (text-only posts); the author check accepts
  the client shape and the status check accepts hidden/removed.
- New tables: work_post_media, work_post_likes, work_post_comments,
  content_reports, moderation_actions.
- Backfill: every existing post with an image gets its media row at
  position 0 with the same image and focus. No existing row is changed
  or deleted.
"""

from alembic import op
import sqlalchemy as sa


revision = "v29s8o1p2026"
down_revision = "u18n7a1m2026"
branch_labels = None
depends_on = None


OLD_AUTHOR_SHAPE = (
    "("
    "author_type = 'professional' "
    "AND professional_id IS NOT NULL "
    "AND establishment_id IS NULL"
    ") OR ("
    "author_type = 'establishment' "
    "AND establishment_id IS NOT NULL "
    "AND professional_id IS NULL"
    ")"
)

NEW_AUTHOR_SHAPE = (
    "("
    "author_type = 'client' "
    "AND client_profile_id IS NOT NULL "
    "AND professional_id IS NULL "
    "AND establishment_id IS NULL"
    ") OR ("
    "author_type = 'professional' "
    "AND professional_id IS NOT NULL "
    "AND establishment_id IS NULL "
    "AND client_profile_id IS NULL"
    ") OR ("
    "author_type = 'establishment' "
    "AND establishment_id IS NOT NULL "
    "AND professional_id IS NULL "
    "AND client_profile_id IS NULL"
    ")"
)

OLD_STATUS = "status IN ('draft', 'published', 'archived')"
NEW_STATUS = "status IN ('draft', 'published', 'archived', 'hidden', 'removed')"


def upgrade():
    with op.batch_alter_table("work_posts") as batch_op:
        batch_op.add_column(sa.Column("client_profile_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("created_by_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column(
            "image_url",
            existing_type=sa.String(length=500),
            nullable=True,
        )
        batch_op.create_foreign_key(
            "fk_work_posts_client_profile_id",
            "client_profiles",
            ["client_profile_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_work_posts_created_by_user_id",
            "users",
            ["created_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_work_posts_client_profile_id", ["client_profile_id"])
        batch_op.create_index("ix_work_posts_created_by_user_id", ["created_by_user_id"])
        batch_op.drop_constraint("ck_work_post_author_shape", type_="check")
        batch_op.create_check_constraint("ck_work_post_author_shape", NEW_AUTHOR_SHAPE)
        batch_op.drop_constraint("ck_work_post_status", type_="check")
        batch_op.create_check_constraint("ck_work_post_status", NEW_STATUS)

    op.create_table(
        "work_post_media",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("focus_x", sa.SmallInteger(), nullable=False),
        sa.Column("focus_y", sa.SmallInteger(), nullable=False),
        sa.Column("alt_text", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["work_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "position", name="uq_work_post_media_position"),
        sa.CheckConstraint("position BETWEEN 0 AND 9", name="ck_work_post_media_position"),
        sa.CheckConstraint(
            "focus_x BETWEEN 0 AND 100 AND focus_y BETWEEN 0 AND 100",
            name="ck_work_post_media_focus",
        ),
    )
    op.create_index("ix_work_post_media_post_id", "work_post_media", ["post_id"])

    op.create_table(
        "work_post_likes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["work_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_work_post_like_user"),
    )
    op.create_index("ix_work_post_likes_post_id", "work_post_likes", ["post_id"])
    op.create_index("ix_work_post_likes_user_id", "work_post_likes", ["user_id"])

    op.create_table(
        "work_post_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["work_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["work_post_comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('visible', 'hidden_by_author', 'removed_by_moderation', 'deleted')",
            name="ck_work_post_comment_status",
        ),
    )
    op.create_index(
        "ix_work_post_comments_post_created",
        "work_post_comments",
        ["post_id", "created_at"],
    )
    op.create_index("ix_work_post_comments_user_id", "work_post_comments", ["user_id"])
    op.create_index("ix_work_post_comments_parent_id", "work_post_comments", ["parent_id"])

    op.create_table(
        "content_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=36), nullable=False),
        sa.Column("reporter_user_id", sa.Integer(), nullable=True),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=True),
        sa.Column("comment_id", sa.Integer(), nullable=True),
        sa.Column("target_excerpt", sa.String(length=500), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_user_id", sa.Integer(), nullable=True),
        sa.Column("decision_note", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["post_id"], ["work_posts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["comment_id"], ["work_post_comments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("protocol", name="uq_content_reports_protocol"),
        sa.CheckConstraint("target_type IN ('post', 'comment')", name="ck_content_report_target"),
        sa.CheckConstraint(
            "category IN ('spam', 'sexual', 'violence', 'harassment', "
            "'misinformation', 'image_rights', 'other')",
            name="ck_content_report_category",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'actioned', 'dismissed')",
            name="ck_content_report_status",
        ),
    )
    op.create_index("ix_content_reports_reporter_user_id", "content_reports", ["reporter_user_id"])
    op.create_index("ix_content_reports_post_id", "content_reports", ["post_id"])
    op.create_index("ix_content_reports_comment_id", "content_reports", ["comment_id"])
    op.create_index("ix_content_reports_status", "content_reports", ["status"])

    op.create_table(
        "moderation_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=True),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=True),
        sa.Column("comment_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=24), nullable=False),
        sa.Column("moderator_user_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["content_reports.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["post_id"], ["work_posts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["comment_id"], ["work_post_comments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["moderator_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("target_type IN ('post', 'comment')", name="ck_moderation_action_target"),
        sa.CheckConstraint(
            "action IN ('hide', 'restore', 'remove_comment', 'dismiss')",
            name="ck_moderation_action_type",
        ),
    )
    op.create_index("ix_moderation_actions_report_id", "moderation_actions", ["report_id"])
    op.create_index("ix_moderation_actions_post_id", "moderation_actions", ["post_id"])

    # Backfill: the current image of every post becomes position 0.
    op.execute(
        "INSERT INTO work_post_media "
        "(post_id, position, image_url, focus_x, focus_y, alt_text, created_at) "
        "SELECT id, 0, image_url, image_focus_x, image_focus_y, NULL, created_at "
        "FROM work_posts WHERE image_url IS NOT NULL"
    )


def downgrade():
    # Destructive once client posts, carousels, likes, comments or reports
    # exist. Production rollback should revert application code first and
    # keep this schema; a physical downgrade needs an approved backup and
    # explicit authorization. The old checks cannot hold client posts,
    # text-only posts or the new statuses, so the downgrade refuses them.
    bind = op.get_bind()
    blocking = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM work_posts "
            "WHERE author_type = 'client' OR image_url IS NULL "
            "OR status IN ('hidden', 'removed')"
        )
    ).scalar()
    if blocking:
        raise RuntimeError(
            "Downgrade bloqueado: existem publicações de Cliente, só de texto "
            "ou ocultadas/removidas. Faça backup e trate esses registros antes."
        )

    op.drop_index("ix_moderation_actions_post_id", table_name="moderation_actions")
    op.drop_index("ix_moderation_actions_report_id", table_name="moderation_actions")
    op.drop_table("moderation_actions")
    op.drop_index("ix_content_reports_status", table_name="content_reports")
    op.drop_index("ix_content_reports_comment_id", table_name="content_reports")
    op.drop_index("ix_content_reports_post_id", table_name="content_reports")
    op.drop_index("ix_content_reports_reporter_user_id", table_name="content_reports")
    op.drop_table("content_reports")
    op.drop_index("ix_work_post_comments_parent_id", table_name="work_post_comments")
    op.drop_index("ix_work_post_comments_user_id", table_name="work_post_comments")
    op.drop_index("ix_work_post_comments_post_created", table_name="work_post_comments")
    op.drop_table("work_post_comments")
    op.drop_index("ix_work_post_likes_user_id", table_name="work_post_likes")
    op.drop_index("ix_work_post_likes_post_id", table_name="work_post_likes")
    op.drop_table("work_post_likes")
    op.drop_index("ix_work_post_media_post_id", table_name="work_post_media")
    op.drop_table("work_post_media")

    with op.batch_alter_table("work_posts") as batch_op:
        batch_op.drop_constraint("ck_work_post_status", type_="check")
        batch_op.create_check_constraint("ck_work_post_status", OLD_STATUS)
        batch_op.drop_constraint("ck_work_post_author_shape", type_="check")
        batch_op.create_check_constraint("ck_work_post_author_shape", OLD_AUTHOR_SHAPE)
        batch_op.drop_index("ix_work_posts_created_by_user_id")
        batch_op.drop_index("ix_work_posts_client_profile_id")
        batch_op.drop_constraint("fk_work_posts_created_by_user_id", type_="foreignkey")
        batch_op.drop_constraint("fk_work_posts_client_profile_id", type_="foreignkey")
        batch_op.alter_column(
            "image_url",
            existing_type=sa.String(length=500),
            nullable=False,
        )
        batch_op.drop_column("removed_at")
        batch_op.drop_column("created_by_user_id")
        batch_op.drop_column("client_profile_id")
