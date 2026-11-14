"""@username for every account and the history of old handles (SOC-R1 PR 1).

Revision ID: x41u5n4m2026
Revises: w30n1o2t2026

Approved by the owner on 14/11/2026 (Notion 08, ID-SOC-R1-02). Expand-only:
- users gains username (lowercase, unique). Existing accounts get one from
  their name: no accents, lowercase, letters/numbers joined by dots, up to
  24 characters, with a numeric suffix on collision (ana.costa, ana.costa2).
  Reserved words fall back to "pessoa". After the backfill the column is
  NOT NULL.
- New table username_history: a handle a person used keeps pointing to them
  and is never given to someone else.
No other column or row changes. Downgrade drops both additions.

The generator is copied here on purpose: the migration must keep producing
the same result even if app/services/username_service.py changes later.
"""

import re
import unicodedata

from alembic import op
import sqlalchemy as sa


revision = "x41u5n4m2026"
down_revision = "w30n1o2t2026"
branch_labels = None
depends_on = None


RESERVED = {
    "iddun",
    "admin",
    "suporte",
    "oficial",
    "ajuda",
    "seguranca",
    "api",
    "pro",
    "business",
}


def _is_reserved(value):
    core = re.sub(r"[._0-9]", "", value)
    return core in RESERVED or core.startswith("iddun")


def _base(name):
    ascii_name = (
        unicodedata.normalize("NFKD", name or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    base = re.sub(r"[^a-z0-9]+", ".", ascii_name).strip(".")
    base = base[:24].strip(".")
    if len(base) < 3 or _is_reserved(base):
        base = "pessoa"
    return base


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("username", sa.String(length=30), nullable=True))

    op.create_table(
        "username_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_username_history_user_id"),
            nullable=False,
        ),
        sa.Column("username", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("username", name="uq_username_history_username"),
    )
    op.create_index("ix_username_history_user_id", "username_history", ["user_id"])

    # Backfill in id order, so the oldest account keeps the plain handle.
    conn = op.get_bind()
    users = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("username", sa.String),
    )
    taken = set()
    for user_id, name in conn.execute(
        sa.select(users.c.id, users.c.name).order_by(users.c.id)
    ).all():
        base = _base(name)
        candidate = base
        suffix = 1
        while candidate in taken:
            suffix += 1
            candidate = f"{base}{suffix}"
        taken.add(candidate)
        conn.execute(
            users.update().where(users.c.id == user_id).values(username=candidate)
        )

    with op.batch_alter_table("users") as batch:
        batch.alter_column("username", existing_type=sa.String(length=30), nullable=False)
        batch.create_index("ix_users_username", ["username"], unique=True)


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_username")
        batch.drop_column("username")
    op.drop_index("ix_username_history_user_id", table_name="username_history")
    op.drop_table("username_history")
