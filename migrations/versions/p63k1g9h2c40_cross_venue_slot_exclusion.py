"""Prevent overlapping active slots for the same professional on PostgreSQL.

Revision ID: p63k1g9h2c40
Revises: o52j0f8g1b39
"""

from alembic import op
import sqlalchemy as sa

revision = "p63k1g9h2c40"
down_revision = "o52j0f8g1b39"
branch_labels = None
depends_on = None

GUARDED = (
    "'available', 'held', 'booked', 'blocked_external', 'blocked_manual'"
)


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Equal professional IDs need the GiST integer operator class.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # Fail loudly if an existing dataset violates the intended invariant:
    # it must be reconciled manually rather than silently discarding slots.
    conflicts = bind.execute(
        sa.text(
            """
            SELECT first_slot.id AS first_id, second_slot.id AS second_id
            FROM experience_slots first_slot
            JOIN experience_slots second_slot
              ON first_slot.professional_id = second_slot.professional_id
             AND first_slot.id < second_slot.id
             AND first_slot.starts_at < second_slot.ends_at
             AND first_slot.ends_at > second_slot.starts_at
            WHERE first_slot.status IN (
                'available', 'held', 'booked', 'blocked_external', 'blocked_manual'
            )
              AND second_slot.status IN (
                'available', 'held', 'booked', 'blocked_external', 'blocked_manual'
            )
            LIMIT 1
            """
        )
    ).first()
    if conflicts:
        raise RuntimeError(
            "Slots ativos sobrepostos existentes: "
            f"{conflicts.first_id} e {conflicts.second_id}. "
            "Reconcilie os registros antes de aplicar esta migration."
        )

    op.execute(
        """
        ALTER TABLE experience_slots
        ADD CONSTRAINT ex_experience_slots_professional_active_window
        EXCLUDE USING gist (
            professional_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        )
        WHERE (status IN (
            'available', 'held', 'booked', 'blocked_external', 'blocked_manual'
        ))
        """
    )
    op.create_check_constraint(
        "ck_experience_slots_valid_window",
        "experience_slots",
        "ends_at > starts_at",
    )


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.drop_constraint(
        "ck_experience_slots_valid_window",
        "experience_slots",
        type_="check",
    )
    op.drop_constraint(
        "ex_experience_slots_professional_active_window",
        "experience_slots",
        type_="exclusion",
    )
    # Keep btree_gist: other DB objects may depend on it.
