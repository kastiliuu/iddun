"""data integrity guards

Revision ID: e52c9b4d7a11
Revises: d31f0a7b8c42
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa


revision = "e52c9b4d7a11"
down_revision = "d31f0a7b8c42"
branch_labels = None
depends_on = None


def _assert_memberships_are_unique(bind):
    duplicates = bind.execute(
        sa.text(
            """
            SELECT
                professional_id,
                establishment_id,
                COUNT(*) AS total
            FROM professional_establishment_memberships
            GROUP BY professional_id, establishment_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()

    if duplicates:
        pairs = ", ".join(
            (
                f"professional={row.professional_id}, "
                f"establishment={row.establishment_id}"
            )
            for row in duplicates[:10]
        )

        raise RuntimeError(
            "Não foi possível aplicar a constraint de vínculo "
            "profissional/estabelecimento porque existem "
            f"duplicidades: {pairs}."
        )


def _assert_reviews_are_consistent(bind):
    invalid_count = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM reviews
            WHERE NOT (
                (
                    target_type = 'professional'
                    AND professional_id IS NOT NULL
                    AND establishment_id IS NULL
                )
                OR
                (
                    target_type = 'establishment'
                    AND establishment_id IS NOT NULL
                    AND professional_id IS NULL
                )
            )
            """
        )
    ).scalar_one()

    if invalid_count:
        raise RuntimeError(
            "Não foi possível aplicar a constraint de avaliações "
            f"porque existem {invalid_count} registro(s) com alvo inconsistente."
        )


def upgrade():
    bind = op.get_bind()

    _assert_memberships_are_unique(bind)
    _assert_reviews_are_consistent(bind)

    with op.batch_alter_table(
        "professional_establishment_memberships"
    ) as batch_op:
        batch_op.drop_index(
            "ix_membership_professional_establishment"
        )
        batch_op.create_unique_constraint(
            "uq_membership_professional_establishment",
            [
                "professional_id",
                "establishment_id",
            ],
        )

    with op.batch_alter_table(
        "reviews"
    ) as batch_op:
        batch_op.create_check_constraint(
            "ck_review_target_consistency",
            (
                "(target_type = 'professional' "
                "AND professional_id IS NOT NULL "
                "AND establishment_id IS NULL) "
                "OR "
                "(target_type = 'establishment' "
                "AND establishment_id IS NOT NULL "
                "AND professional_id IS NULL)"
            ),
        )


def downgrade():
    with op.batch_alter_table(
        "reviews"
    ) as batch_op:
        batch_op.drop_constraint(
            "ck_review_target_consistency",
            type_="check",
        )

    with op.batch_alter_table(
        "professional_establishment_memberships"
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_membership_professional_establishment",
            type_="unique",
        )
        batch_op.create_index(
            "ix_membership_professional_establishment",
            [
                "professional_id",
                "establishment_id",
            ],
            unique=False,
        )
