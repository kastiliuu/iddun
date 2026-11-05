"""Notification center V0: categories, context, dedupe and grouping (PR 6a).

Revision ID: w30n1o2t2026
Revises: v29s8o1p2026

Approved plan D-SOC-21 (05/11/2026). Expand-only:
- notifications gains category (bookings, social, work, system; backfilled
  from kind), context_type/context_id, dedupe_key (unique per user, so the
  same event never notifies twice) and group_key/group_count (likes on the
  same post become one notice).
- The kind check accepts like, comment, membership and review.
- New indexes (user_id, category, read_at) and (user_id, created_at).
- notification_preferences gains social_enabled and work_enabled.
No existing row is deleted; existing notices keep kind, text and read state.
"""

from alembic import op
import sqlalchemy as sa


revision = "w30n1o2t2026"
down_revision = "v29s8o1p2026"
branch_labels = None
depends_on = None


OLD_KINDS = "kind IN ('booking', 'iddun_now', 'follow', 'system')"
NEW_KINDS = (
    "kind IN ('booking', 'iddun_now', 'follow', 'system', "
    "'like', 'comment', 'membership', 'review')"
)
CATEGORIES = "category IN ('bookings', 'social', 'work', 'system')"
CONTEXTS = (
    "context_type IS NULL OR context_type IN "
    "('client', 'professional', 'establishment')"
)


def upgrade():
    with op.batch_alter_table("notifications") as batch:
        batch.add_column(
            sa.Column("category", sa.String(length=24), nullable=False, server_default="system")
        )
        batch.add_column(sa.Column("context_type", sa.String(length=24), nullable=True))
        batch.add_column(sa.Column("context_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("dedupe_key", sa.String(length=160), nullable=True))
        batch.add_column(sa.Column("group_key", sa.String(length=160), nullable=True))
        batch.add_column(
            sa.Column("group_count", sa.Integer(), nullable=False, server_default="1")
        )
        batch.drop_constraint("ck_notification_kind", type_="check")
        batch.create_check_constraint("ck_notification_kind", NEW_KINDS)
        batch.create_check_constraint("ck_notification_category", CATEGORIES)
        batch.create_check_constraint("ck_notification_context", CONTEXTS)
        batch.create_check_constraint("ck_notification_group_count", "group_count >= 1")
        batch.create_unique_constraint(
            "uq_notifications_user_dedupe", ["user_id", "dedupe_key"]
        )

    # Backfill: the category follows the old kind.
    op.execute(
        "UPDATE notifications SET category = CASE kind "
        "WHEN 'booking' THEN 'bookings' "
        "WHEN 'iddun_now' THEN 'bookings' "
        "WHEN 'follow' THEN 'social' "
        "ELSE 'system' END"
    )

    op.create_index(
        "ix_notifications_user_category_read",
        "notifications",
        ["user_id", "category", "read_at"],
    )
    op.create_index(
        "ix_notifications_user_created",
        "notifications",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_notifications_user_group",
        "notifications",
        ["user_id", "group_key"],
    )

    with op.batch_alter_table("notification_preferences") as batch:
        batch.add_column(
            sa.Column("social_enabled", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.add_column(
            sa.Column("work_enabled", sa.Boolean(), nullable=False, server_default=sa.true())
        )


def downgrade():
    # The old check cannot hold the new kinds. A physical downgrade with them
    # present needs an approved backup and explicit authorization.
    bind = op.get_bind()
    blocking = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM notifications "
            "WHERE kind IN ('like', 'comment', 'membership', 'review')"
        )
    ).scalar()
    if blocking:
        raise RuntimeError(
            "Downgrade bloqueado: existem notificações dos tipos novos "
            "(curtida, comentário, vínculo ou avaliação). Faça backup e trate "
            "esses registros antes."
        )

    with op.batch_alter_table("notification_preferences") as batch:
        batch.drop_column("work_enabled")
        batch.drop_column("social_enabled")

    op.drop_index("ix_notifications_user_group", table_name="notifications")
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_index("ix_notifications_user_category_read", table_name="notifications")

    with op.batch_alter_table("notifications") as batch:
        batch.drop_constraint("uq_notifications_user_dedupe", type_="unique")
        batch.drop_constraint("ck_notification_group_count", type_="check")
        batch.drop_constraint("ck_notification_context", type_="check")
        batch.drop_constraint("ck_notification_category", type_="check")
        batch.drop_constraint("ck_notification_kind", type_="check")
        batch.create_check_constraint("ck_notification_kind", OLD_KINDS)
        batch.drop_column("group_count")
        batch.drop_column("group_key")
        batch.drop_column("dedupe_key")
        batch.drop_column("context_id")
        batch.drop_column("context_type")
        batch.drop_column("category")
