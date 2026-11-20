"""Canonical personal avatar and cover (QA-001 / ID-UNI-MEDIA-02).

Revision ID: b85p3r2m2026
Revises: a74c1r2p2026

Approved by the owner in the PR #252 conversation (20/11/2026):
- two nullable columns on users; no legacy column/table removal;
- backfill avatar: Client first, then Pro; cover: Pro only;
- old paths are retained, and all writers dual-write during rollout.
No image file is deleted during upgrade or downgrade.

Downgrade removes only the two new columns. Existing media values are
preserved in client_profiles/professional_profiles, including new uploads
mirrored by the application. Before downgrade, verify all deployed versions
are rollback-compatible; never downgrade application code first.
"""

from alembic import op
import sqlalchemy as sa

revision = "b85p3r2m2026"
down_revision = "a74c1r2p2026"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("avatar_url", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("cover_url", sa.String(length=500), nullable=True))

    # SQLite and PostgreSQL support these correlated selects.
    # Blank legacy strings are treated as missing. No old value is altered.
    op.execute(
        "UPDATE users SET avatar_url = COALESCE("
        " (SELECT NULLIF(cp.avatar_url, '') FROM client_profiles cp WHERE cp.user_id = users.id),"
        " (SELECT NULLIF(pp.avatar_url, '') FROM professional_profiles pp WHERE pp.user_id = users.id)"
        "), cover_url = ("
        " SELECT NULLIF(pp.cover_url, '') FROM professional_profiles pp WHERE pp.user_id = users.id"
        ")"
    )


def downgrade():
    # The application dual-writes into legacy columns, so removal of the
    # canonical columns does not destroy images created through old endpoints.
    # Intentionally do not overwrite historical Client/Pro values.
    with op.batch_alter_table("users") as batch:
        batch.drop_column("cover_url")
        batch.drop_column("avatar_url")
