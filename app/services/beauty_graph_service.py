from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.beauty_graph import (
    Follow,
    FollowTarget,
    Save,
    SaveTarget,
)
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.experience import Experience
from app.models.professional import (
    ProfessionalPortfolioItem,
    ProfessionalProfile,
)
from app.models.work_post import (
    WorkPost,
    WorkPostAuthorType,
    WorkPostStatus,
)
from app.services.feed_service import (
    serialize_work_post,
)
from app.services.media_storage import (
    resolve_image_url,
)
from app.services.public_eligibility import (
    establishment_is_public,
    professional_is_public,
    public_experiences_query,
)
from app.services.reputation_service import (
    reputation_summary,
)


class BeautyGraphError(ValueError):
    pass


class OwnProfileError(BeautyGraphError):
    """D-SOC-06: ninguém segue o próprio perfil Pro nem a própria empresa."""


FOLLOWING_PAGE_SIZE = 20
MAX_FOLLOWING_PAGE_SIZE = 50
MAX_LEGACY_SLUGS = 200


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


def _public_work_post(target_id):
    item = db.session.get(
        WorkPost,
        target_id,
    )

    if (
        item is None
        or item.status
        != WorkPostStatus.PUBLISHED
    ):
        raise BeautyGraphError(
            "Publicação não encontrada."
        )

    if item.author_type == WorkPostAuthorType.CLIENT:
        # Publicação da Cliente (PR 3): conta ativa.
        profile = item.client_profile
        if profile is None or not profile.user.is_active:
            raise BeautyGraphError(
                "Publicação não encontrada."
            )
        return item

    if (
        item.author_type
        == WorkPostAuthorType.PROFESSIONAL
    ):
        if not professional_is_public(
            item.professional
        ):
            raise BeautyGraphError(
                "Publicação não encontrada."
            )
    elif (
        item.author_type
        == WorkPostAuthorType.ESTABLISHMENT
    ):
        if not establishment_is_public(
            item.establishment
        ):
            raise BeautyGraphError(
                "Publicação não encontrada."
            )
    else:
        raise BeautyGraphError(
            "Publicação não encontrada."
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

    if target_type == SaveTarget.WORK_POST:
        return _public_work_post(
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
        SaveTarget.WORK_POST:
            Save.work_post_id,
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


def owns_follow_target(user, target):
    """O perfil Pro da própria conta ou empresa em que a conta é dona ativa."""
    if user is None or user.id is None or target is None:
        return False

    if isinstance(target, ProfessionalProfile):
        return target.user_id == user.id

    return db.session.scalar(
        select(EstablishmentUserAccess.id).where(
            EstablishmentUserAccess.user_id == user.id,
            EstablishmentUserAccess.establishment_id == target.id,
            EstablishmentUserAccess.role == EstablishmentAccessRole.OWNER,
            EstablishmentUserAccess.status == EstablishmentAccessStatus.ACTIVE,
        )
    ) is not None


def follow_target(
    *,
    user,
    target_type,
    target_id,
):
    _require_user(user)
    target = resolve_follow_target(
        target_type,
        target_id,
    )

    if owns_follow_target(user, target):
        raise OwnProfileError(
            "Você não pode seguir o seu próprio perfil."
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
        SaveTarget.WORK_POST:
            "work_post_id",
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
        SaveTarget.WORK_POST:
            item.work_post_id,
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


def _experience_ids_by_slug(slugs):
    """Favoritos antigos do navegador guardavam o slug da experiência."""
    if not slugs:
        return {}

    rows = db.session.execute(
        public_experiences_query()
        .with_only_columns(Experience.slug, Experience.id)
        .where(Experience.slug.in_(slugs))
    ).all()

    return {slug: item_id for slug, item_id in rows}


def reconcile_graph(
    *,
    user,
    follows,
    saves,
    experience_slugs=(),
):
    _require_user(user)

    ids_by_slug = _experience_ids_by_slug(
        list(experience_slugs)
    )
    saves = list(saves)
    legacy_rejected = []

    for slug in experience_slugs:
        if slug in ids_by_slug:
            saves.append(
                {
                    "targetType": SaveTarget.EXPERIENCE,
                    "targetId": ids_by_slug[slug],
                }
            )
        else:
            legacy_rejected.append(slug)

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

    if experience_slugs:
        # Só aparece quando o cliente mandou slugs antigos; o contrato do
        # app continua com follows e saves.
        rejected["experienceSlugs"] = legacy_rejected

    return {
        "state": graph_state(user),
        "imported": imported,
        "rejected": rejected,
    }



def _profile_saved_payload(
    item,
    *,
    kind,
):
    reputation = reputation_summary(
        item.reviews_received
    )

    if kind == SaveTarget.PROFESSIONAL:
        name = item.display_name
        route_id = item.slug
        avatar = (
            item.avatar_url
            or "img/category-hair.jpg"
        )
        specialty = (
            item.primary_specialty
            or "Profissional de beleza"
        )
        location_parts = [
            item.city,
            item.state,
        ]
    else:
        name = item.name
        route_id = item.slug
        avatar = (
            item.logo_url
            or "img/category-hair.jpg"
        )
        specialty = (
            item.category
            or "Espaço de beleza"
        )
        location_parts = [
            item.neighborhood,
            item.city,
            item.state,
        ]

    return {
        "id": str(item.id),
        "routeId": route_id,
        "kind": kind,
        "name": name,
        "avatar": resolve_image_url(
            avatar,
            external=True,
        ),
        "specialty": specialty,
        "location": (
            " · ".join(
                part
                for part in location_parts
                if part
            )
            or "Brasil"
        ),
        # D11: sem upload, a Web mostra iniciais em vez da foto de estoque.
        "avatarUploaded": bool(
            item.avatar_url
            if kind == SaveTarget.PROFESSIONAL
            else item.logo_url
        ),
        "rating": (
            reputation["average"]
        ),
        "reviewsCount": (
            reputation["count"]
        ),
    }


def _experience_saved_payload(
    item,
):
    establishment = (
        item.establishment
    )
    professional = (
        item.professional
    )

    location_parts = (
        [
            establishment.neighborhood,
            establishment.city,
            establishment.state,
        ]
        if establishment is not None
        else [
            professional.city,
            professional.state,
        ]
    )

    return {
        "id": item.slug,
        "entityId": item.id,
        "name": item.title,
        "image": resolve_image_url(
            item.image_url
            or "img/exp-hair.jpg",
            external=True,
        ),
        "category": item.category,
        "professionalName": (
            professional.display_name
        ),
        "location": (
            " · ".join(
                part
                for part in location_parts
                if part
            )
            or "Brasil"
        ),
        "durationMinutes": (
            item.duration_minutes
        ),
        "price": float(
            item.price
        ),
    }


def _portfolio_saved_payload(
    item,
):
    professional = item.professional

    return {
        "id": str(item.id),
        "professionalRouteId": (
            professional.slug
        ),
        "authorName": (
            professional.display_name
        ),
        "image": resolve_image_url(
            item.image_url,
            external=True,
        ),
        "caption": (
            item.caption or ""
        ),
    }


def saved_items(user):
    _require_user(user)

    saves = db.session.scalars(
        select(Save)
        .where(
            Save.user_id == user.id
        )
        .order_by(
            Save.created_at.desc(),
            Save.id.desc(),
        )
    ).all()

    profiles = []
    experiences = []
    posts = []
    portfolio_items = []

    for save in saves:
        try:
            target = resolve_save_target(
                save.target_type,
                save_reference(
                    save
                )["targetId"],
            )
        except BeautyGraphError:
            continue

        if (
            save.target_type
            == SaveTarget.PROFESSIONAL
        ):
            profiles.append(
                _profile_saved_payload(
                    target,
                    kind=SaveTarget.PROFESSIONAL,
                )
            )
        elif (
            save.target_type
            == SaveTarget.ESTABLISHMENT
        ):
            profiles.append(
                _profile_saved_payload(
                    target,
                    kind=SaveTarget.ESTABLISHMENT,
                )
            )
        elif (
            save.target_type
            == SaveTarget.EXPERIENCE
        ):
            experiences.append(
                _experience_saved_payload(
                    target
                )
            )
        elif (
            save.target_type
            == SaveTarget.WORK_POST
        ):
            posts.append(
                serialize_work_post(
                    target
                )
            )
        elif (
            save.target_type
            == SaveTarget.PORTFOLIO_ITEM
        ):
            portfolio_items.append(
                _portfolio_saved_payload(
                    target
                )
            )

    return {
        "profiles": profiles,
        "experiences": experiences,
        "posts": posts,
        "portfolioItems": (
            portfolio_items
        ),
    }


def follower_count(target_type, target_id):
    """Número real de contas que seguem o perfil (D-SOC-05)."""
    column = (
        Follow.professional_id
        if target_type == FollowTarget.PROFESSIONAL
        else Follow.establishment_id
    )

    return db.session.scalar(
        select(func.count(Follow.id)).where(
            Follow.target_type == target_type,
            column == target_id,
        )
    ) or 0


def is_following(user, target_type, target_id):
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    return db.session.scalar(
        select(Follow.id).where(
            *_follow_filters(
                user.id,
                target_type,
                target_id,
            )
        )
    ) is not None


def is_saved(user, target_type, target_id):
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    return db.session.scalar(
        select(Save.id).where(
            *_save_filters(
                user.id,
                target_type,
                target_id,
            )
        )
    ) is not None


def _public_follows_query(user_id):
    """Seguidos cujo perfil continua público, do mais recente ao mais antigo."""
    active_professionals = select(ProfessionalProfile.id).where(
        ProfessionalProfile.is_active.is_(True)
    )
    active_establishments = select(Establishment.id).where(
        Establishment.is_active.is_(True)
    )

    return select(Follow).where(
        Follow.user_id == user_id,
        (
            (
                (Follow.target_type == FollowTarget.PROFESSIONAL)
                & Follow.professional_id.in_(active_professionals)
            )
            | (
                (Follow.target_type == FollowTarget.ESTABLISHMENT)
                & Follow.establishment_id.in_(active_establishments)
            )
        ),
    )


def _location(*parts):
    return " · ".join(part for part in parts if part) or None


def following_payload(follow):
    if follow.target_type == FollowTarget.PROFESSIONAL:
        item = follow.professional
        return {
            "targetType": FollowTarget.PROFESSIONAL,
            "targetId": item.id,
            "slug": item.slug,
            "name": item.display_name,
            "subtitle": item.primary_specialty or "Profissional de beleza",
            "location": _location(item.city, item.state),
            # D11: sem foto enviada, o perfil mostra as iniciais.
            "avatar": (
                resolve_image_url(item.avatar_url, external=True)
                if item.avatar_url
                else None
            ),
            "followedAt": follow.created_at.isoformat(),
        }

    item = follow.establishment
    return {
        "targetType": FollowTarget.ESTABLISHMENT,
        "targetId": item.id,
        "slug": item.slug,
        "name": item.name,
        "subtitle": item.category or "Espaço de beleza",
        "location": _location(item.neighborhood, item.city, item.state),
        "avatar": (
            resolve_image_url(item.logo_url, external=True)
            if item.logo_url
            else None
        ),
        "followedAt": follow.created_at.isoformat(),
    }


def following_page(user, *, limit=FOLLOWING_PAGE_SIZE, before=None):
    """Página de seguidos; `before` é o id do último item da página anterior."""
    _require_user(user)

    limit = max(1, min(int(limit), MAX_FOLLOWING_PAGE_SIZE))
    query = _public_follows_query(user.id)

    total = db.session.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    if before is not None:
        query = query.where(Follow.id < before)

    rows = db.session.scalars(
        query.order_by(Follow.id.desc()).limit(limit + 1)
    ).all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    return {
        "items": [following_payload(item) for item in rows],
        "total": total,
        "nextCursor": str(rows[-1].id) if has_more and rows else None,
    }
