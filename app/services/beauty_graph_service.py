from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.beauty_graph import (
    Follow,
    FollowTarget,
    Save,
    SaveTarget,
)
from app.models.establishment import Establishment
from app.models.experience import Experience
from app.models.professional import (
    ProfessionalPortfolioItem,
    ProfessionalProfile,
)
from app.services.public_eligibility import (
    establishment_is_public,
    professional_is_public,
    public_experiences_query,
)


class BeautyGraphError(ValueError):
    pass


def _require_user(user):
    if (
        user is None
        or user.id is None
        or not user.is_active
    ):
        raise BeautyGraphError(
            "Entre em uma conta ativa para continuar."
        )


def _public_professional(target_id):
    item = db.session.get(
        ProfessionalProfile,
        target_id,
    )

    if not professional_is_public(item):
        raise BeautyGraphError(
            "Profissional não encontrado."
        )

    return item


def _public_establishment(target_id):
    item = db.session.get(
        Establishment,
        target_id,
    )

    if not establishment_is_public(item):
        raise BeautyGraphError(
            "Estabelecimento não encontrado."
        )

    return item


def _public_experience(target_id):
    item = db.session.scalar(
        public_experiences_query().where(
            Experience.id == target_id
        )
    )

    if item is None:
        raise BeautyGraphError(
            "Experiência não encontrada."
        )

    return item


def _public_portfolio_item(target_id):
    item = db.session.get(
        ProfessionalPortfolioItem,
        target_id,
    )

    if (
        item is None
        or not professional_is_public(
            item.professional
        )
    ):
        raise BeautyGraphError(
            "Trabalho não encontrado."
        )

    return item


def resolve_follow_target(
    target_type,
    target_id,
):
    if target_type == FollowTarget.PROFESSIONAL:
        return _public_professional(
            target_id
        )

    if target_type == FollowTarget.ESTABLISHMENT:
        return _public_establishment(
            target_id
        )

    raise BeautyGraphError(
        "Tipo de perfil inválido para Follow."
    )


def resolve_save_target(
    target_type,
    target_id,
):
    if target_type == SaveTarget.PROFESSIONAL:
        return _public_professional(
            target_id
        )

    if target_type == SaveTarget.ESTABLISHMENT:
        return _public_establishment(
            target_id
        )

    if target_type == SaveTarget.EXPERIENCE:
        return _public_experience(
            target_id
        )

    if target_type == SaveTarget.PORTFOLIO_ITEM:
        return _public_portfolio_item(
            target_id
        )

    raise BeautyGraphError(
        "Tipo de item inválido para Save."
    )


def _follow_filters(
    user_id,
    target_type,
    target_id,
):
    filters = [
        Follow.user_id == user_id,
        Follow.target_type == target_type,
    ]

    if target_type == FollowTarget.PROFESSIONAL:
        filters.append(
            Follow.professional_id
            == target_id
        )
    else:
        filters.append(
            Follow.establishment_id
            == target_id
        )

    return filters


def _save_filters(
    user_id,
    target_type,
    target_id,
):
    filters = [
        Save.user_id == user_id,
        Save.target_type == target_type,
    ]

    mapping = {
        SaveTarget.PROFESSIONAL:
            Save.professional_id,
        SaveTarget.ESTABLISHMENT:
            Save.establishment_id,
        SaveTarget.EXPERIENCE:
            Save.experience_id,
        SaveTarget.PORTFOLIO_ITEM:
            Save.portfolio_item_id,
    }

    column = mapping.get(
        target_type
    )

    if column is None:
        raise BeautyGraphError(
            "Tipo de item inválido para Save."
        )

    filters.append(
        column == target_id
    )

    return filters


def follow_target(
    *,
    user,
    target_type,
    target_id,
):
    _require_user(user)
    resolve_follow_target(
        target_type,
        target_id,
    )

    existing = db.session.scalar(
        select(Follow).where(
            *_follow_filters(
                user.id,
                target_type,
                target_id,
            )
        )
    )

    if existing is not None:
        return existing

    item = Follow(
        user_id=user.id,
        target_type=target_type,
        professional_id=(
            target_id
            if target_type
            == FollowTarget.PROFESSIONAL
            else None
        ),
        establishment_id=(
            target_id
            if target_type
            == FollowTarget.ESTABLISHMENT
            else None
        ),
    )

    db.session.add(item)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

        existing = db.session.scalar(
            select(Follow).where(
                *_follow_filters(
                    user.id,
                    target_type,
                    target_id,
                )
            )
        )

        if existing is not None:
            return existing

        raise

    return item


def unfollow_target(
    *,
    user,
    target_type,
    target_id,
):
    _require_user(user)

    item = db.session.scalar(
        select(Follow).where(
            *_follow_filters(
                user.id,
                target_type,
                target_id,
            )
        )
    )

    if item is None:
        return False

    db.session.delete(item)
    db.session.commit()

    return True


def save_target(
    *,
    user,
    target_type,
    target_id,
):
    _require_user(user)
    resolve_save_target(
        target_type,
        target_id,
    )

    existing = db.session.scalar(
        select(Save).where(
            *_save_filters(
                user.id,
                target_type,
                target_id,
            )
        )
    )

    if existing is not None:
        return existing

    kwargs = {
        "user_id": user.id,
        "target_type": target_type,
    }

    field_by_type = {
        SaveTarget.PROFESSIONAL:
            "professional_id",
        SaveTarget.ESTABLISHMENT:
            "establishment_id",
        SaveTarget.EXPERIENCE:
            "experience_id",
        SaveTarget.PORTFOLIO_ITEM:
            "portfolio_item_id",
    }

    kwargs[
        field_by_type[target_type]
    ] = target_id

    item = Save(**kwargs)
    db.session.add(item)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

        existing = db.session.scalar(
            select(Save).where(
                *_save_filters(
                    user.id,
                    target_type,
                    target_id,
                )
            )
        )

        if existing is not None:
            return existing

        raise

    return item


def unsave_target(
    *,
    user,
    target_type,
    target_id,
):
    _require_user(user)

    item = db.session.scalar(
        select(Save).where(
            *_save_filters(
                user.id,
                target_type,
                target_id,
            )
        )
    )

    if item is None:
        return False

    db.session.delete(item)
    db.session.commit()

    return True


def follow_reference(item):
    if (
        item.target_type
        == FollowTarget.PROFESSIONAL
    ):
        target_id = item.professional_id
    else:
        target_id = item.establishment_id

    return {
        "targetType": item.target_type,
        "targetId": target_id,
    }


def save_reference(item):
    mapping = {
        SaveTarget.PROFESSIONAL:
            item.professional_id,
        SaveTarget.ESTABLISHMENT:
            item.establishment_id,
        SaveTarget.EXPERIENCE:
            item.experience_id,
        SaveTarget.PORTFOLIO_ITEM:
            item.portfolio_item_id,
    }

    return {
        "targetType": item.target_type,
        "targetId": mapping[
            item.target_type
        ],
    }


def graph_state(user):
    _require_user(user)

    follows = db.session.scalars(
        select(Follow)
        .where(
            Follow.user_id == user.id
        )
        .order_by(
            Follow.created_at.asc(),
            Follow.id.asc(),
        )
    ).all()

    saves = db.session.scalars(
        select(Save)
        .where(
            Save.user_id == user.id
        )
        .order_by(
            Save.created_at.asc(),
            Save.id.asc(),
        )
    ).all()

    return {
        "follows": [
            follow_reference(item)
            for item in follows
        ],
        "saves": [
            save_reference(item)
            for item in saves
        ],
    }


def reconcile_graph(
    *,
    user,
    follows,
    saves,
):
    _require_user(user)

    imported = {
        "follows": [],
        "saves": [],
    }
    rejected = {
        "follows": [],
        "saves": [],
    }

    for reference in follows:
        try:
            item = follow_target(
                user=user,
                target_type=reference[
                    "targetType"
                ],
                target_id=reference[
                    "targetId"
                ],
            )
            imported[
                "follows"
            ].append(
                follow_reference(item)
            )
        except (
            BeautyGraphError,
            KeyError,
            TypeError,
        ):
            rejected[
                "follows"
            ].append(reference)

    for reference in saves:
        try:
            item = save_target(
                user=user,
                target_type=reference[
                    "targetType"
                ],
                target_id=reference[
                    "targetId"
                ],
            )
            imported[
                "saves"
            ].append(
                save_reference(item)
            )
        except (
            BeautyGraphError,
            KeyError,
            TypeError,
        ):
            rejected[
                "saves"
            ].append(reference)

    return {
        "state": graph_state(user),
        "imported": imported,
        "rejected": rejected,
    }
