"""Follow people, not Pro profiles (SOC-R1 PR 1).

Revision ID: y52f0l1w2026
Revises: x41u5n4m2026

Approved by the owner on 14/11/2026 (Notion 08, ID-SOC-R1-03 and -04): any
active account follows any active person or establishment.

Upgrade:
- follows gains followed_user_id (FK users, ON DELETE CASCADE), the target
  shape accepts 'person', and (user_id, followed_user_id) is unique.
- Every 'professional' follow becomes a 'person' follow of the account that
  owns that Pro profile. If the same follower already follows that person,
  the rows are merged keeping the oldest created_at.
- A follow of a catalogue Pro profile without an account (user_id NULL,
  created by an admin) stays 'professional', unchanged: no follower is lost.
- A follow of the follower's own Pro profile was never allowed (D-SOC-06)
  and is removed if one exists.
- Establishment follows do not change.

Downgrade:
- A 'person' follow whose account has a Pro profile goes back to
  'professional'. Other 'person' follows (people without a Pro profile,
  only possible after the upgrade) are removed: the old schema cannot hold
  them. Then the column and constraints are dropped.
"""

from alembic import op
import sqlalchemy as sa


revision = "y52f0l1w2026"
down_revision = "x41u5n4m2026"
branch_labels = None
depends_on = None


OLD_SHAPE = (
    "("
    "target_type = 'professional' "
    "AND professional_id IS NOT NULL "
    "AND establishment_id IS NULL"
    ") OR ("
    "target_type = 'establishment' "
    "AND establishment_id IS NOT NULL "
    "AND professional_id IS NULL"
    ")"
)

NEW_SHAPE = (
    "("
    "target_type = 'person' "
    "AND followed_user_id IS NOT NULL "
    "AND professional_id IS NULL "
    "AND establishment_id IS NULL"
    ") OR ("
    "target_type = 'professional' "
    "AND professional_id IS NOT NULL "
    "AND establishment_id IS NULL "
    "AND followed_user_id IS NULL"
    ") OR ("
    "target_type = 'establishment' "
    "AND establishment_id IS NOT NULL "
    "AND professional_id IS NULL "
    "AND followed_user_id IS NULL"
    ")"
)

follows = sa.table(
    "follows",
    sa.column("id", sa.Integer),
    sa.column("user_id", sa.Integer),
    sa.column("target_type", sa.String),
    sa.column("professional_id", sa.Integer),
    sa.column("establishment_id", sa.Integer),
    sa.column("followed_user_id", sa.Integer),
    sa.column("created_at", sa.DateTime(timezone=True)),
)
professionals = sa.table(
    "professional_profiles",
    sa.column("id", sa.Integer),
    sa.column("user_id", sa.Integer),
)


def upgrade():
    with op.batch_alter_table("follows") as batch:
        batch.add_column(sa.Column("followed_user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_follows_followed_user_id",
            "users",
            ["followed_user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_index("ix_follows_followed_user_id", ["followed_user_id"])
        batch.drop_constraint("ck_follow_target_shape", type_="check")
        batch.create_check_constraint("ck_follow_target_shape", NEW_SHAPE)

    conn = op.get_bind()
    owner_by_profile = dict(
        conn.execute(sa.select(professionals.c.id, professionals.c.user_id)).all()
    )
    rows = conn.execute(
        sa.select(
            follows.c.id,
            follows.c.user_id,
            follows.c.professional_id,
            follows.c.created_at,
        )
        .where(follows.c.target_type == "professional")
        .order_by(follows.c.created_at, follows.c.id)
    ).all()

    kept = {}
    for follow_id, follower_id, professional_id, created_at in rows:
        person_id = owner_by_profile.get(professional_id)
        if person_id is None:
            # Catalogue profile without an account: nobody to follow as a
            # person, so the follow stays on the profile, unchanged.
            continue
        if person_id == follower_id:
            # Following oneself was never allowed (D-SOC-06).
            conn.execute(follows.delete().where(follows.c.id == follow_id))
            continue
        key = (follower_id, person_id)
        if key in kept:
            # Oldest first: the kept row already has the earliest date.
            conn.execute(follows.delete().where(follows.c.id == follow_id))
            continue
        kept[key] = follow_id
        conn.execute(
            follows.update()
            .where(follows.c.id == follow_id)
            .values(
                target_type="person",
                followed_user_id=person_id,
                professional_id=None,
            )
        )

    with op.batch_alter_table("follows") as batch:
        batch.create_unique_constraint("uq_follow_user_person", ["user_id", "followed_user_id"])


def downgrade():
    conn = op.get_bind()
    profile_by_owner = {
        user_id: profile_id
        for profile_id, user_id in conn.execute(
            sa.select(professionals.c.id, professionals.c.user_id).where(
                professionals.c.user_id.is_not(None)
            )
        ).all()
    }
    rows = conn.execute(
        sa.select(follows.c.id, follows.c.followed_user_id).where(
            follows.c.target_type == "person"
        )
    ).all()
    for follow_id, person_id in rows:
        profile_id = profile_by_owner.get(person_id)
        if profile_id is None:
            conn.execute(follows.delete().where(follows.c.id == follow_id))
            continue
        conn.execute(
            follows.update()
            .where(follows.c.id == follow_id)
            .values(
                target_type="professional",
                professional_id=profile_id,
                followed_user_id=None,
            )
        )

    with op.batch_alter_table("follows") as batch:
        batch.drop_constraint("uq_follow_user_person", type_="unique")
        batch.drop_constraint("ck_follow_target_shape", type_="check")
        batch.create_check_constraint("ck_follow_target_shape", OLD_SHAPE)
        batch.drop_index("ix_follows_followed_user_id")
        batch.drop_constraint("fk_follows_followed_user_id", type_="foreignkey")
        batch.drop_column("followed_user_id")
