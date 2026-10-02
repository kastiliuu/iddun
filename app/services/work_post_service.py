from sqlalchemy import select

from app.extensions import db
from app.models.establishment import (
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.work_post import (
    WorkPost,
    WorkPostAuthorType,
    WorkPostStatus,
    utcnow,
)
from app.services.public_eligibility import (
    establishment_is_public,
    professional_is_public,
)


class WorkPostError(ValueError):
    pass


def _require_user(user):
    if (
        user is None
        or user.id is None
        or not user.is_active
    ):
        raise WorkPostError(
            "Entre em uma conta ativa para continuar."
        )


def _clean_caption(value):
    if value is None:
        return None

    if not isinstance(value, str):
        raise WorkPostError(
            "Legenda inválida."
        )

    clean = value.strip()

    if len(clean) > 1200:
        raise WorkPostError(
            "A legenda deve ter no máximo 1200 caracteres."
        )

    return clean or None


def _focus(value, label):
    if value in (None, ""):
        return 50

    try:
        parsed = int(value)
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise WorkPostError(
            f"{label}: use um número entre 0 e 100."
        ) from exc

    if parsed < 0 or parsed > 100:
        raise WorkPostError(
            f"{label}: use um número entre 0 e 100."
        )

    return parsed


def creator_author(
    *,
    user,
    author_type,
    author_id=None,
    publishing=False,
):
    _require_user(user)

    if (
        author_type
        == WorkPostAuthorType.PROFESSIONAL
    ):
        professional = (
            user.professional_profile
        )

        if (
            professional is None
            or (
                author_id is not None
                and professional.id
                != author_id
            )
        ):
            raise WorkPostError(
                "Perfil profissional não encontrado para esta conta."
            )

        if (
            publishing
            and not professional_is_public(
                professional
            )
        ):
            raise WorkPostError(
                "Publique seu perfil profissional antes de publicar trabalhos."
            )

        return professional

    if (
        author_type
        == WorkPostAuthorType.ESTABLISHMENT
    ):
        query = (
            select(
                EstablishmentUserAccess
            )
            .where(
                EstablishmentUserAccess.user_id
                == user.id,
                EstablishmentUserAccess.status
                == EstablishmentAccessStatus.ACTIVE,
            )
            .order_by(
                EstablishmentUserAccess.id.asc()
            )
        )

        if author_id is not None:
            query = query.where(
                EstablishmentUserAccess.establishment_id
                == author_id
            )

        access = db.session.scalar(
            query
        )

        if (
            access is None
            or access.establishment
            is None
        ):
            raise WorkPostError(
                "Estabelecimento não encontrado para esta conta."
            )

        if (
            publishing
            and not establishment_is_public(
                access.establishment
            )
        ):
            raise WorkPostError(
                "Publique o estabelecimento antes de publicar trabalhos."
            )

        return access.establishment

    raise WorkPostError(
        "Tipo de autor inválido."
    )


def _owned_post(
    *,
    user,
    post_id,
):
    _require_user(user)

    post = db.session.get(
        WorkPost,
        post_id,
    )

    if post is None:
        raise WorkPostError(
            "Publicação não encontrada."
        )

    if (
        post.author_type
        == WorkPostAuthorType.PROFESSIONAL
    ):
        professional = (
            user.professional_profile
        )

        if (
            professional is None
            or professional.id
            != post.professional_id
        ):
            raise WorkPostError(
                "Publicação não encontrada."
            )

        return post

    access = db.session.scalar(
        select(
            EstablishmentUserAccess.id
        ).where(
            EstablishmentUserAccess.user_id
            == user.id,
            EstablishmentUserAccess.establishment_id
            == post.establishment_id,
            EstablishmentUserAccess.status
            == EstablishmentAccessStatus.ACTIVE,
        )
    )

    if access is None:
        raise WorkPostError(
            "Publicação não encontrada."
        )

    return post


def _experience_for_author(
    *,
    experience_id,
    author_type,
    author,
    publishing=False,
):
    if experience_id in (
        None,
        "",
    ):
        return None

    try:
        parsed_id = int(
            experience_id
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise WorkPostError(
            "Serviço vinculado inválido."
        ) from exc

    experience = db.session.get(
        Experience,
        parsed_id,
    )

    if experience is None:
        raise WorkPostError(
            "Serviço vinculado não encontrado."
        )

    if (
        author_type
        == WorkPostAuthorType.PROFESSIONAL
        and experience.professional_id
        != author.id
    ):
        raise WorkPostError(
            "Este serviço não pertence ao profissional autor."
        )

    if (
        author_type
        == WorkPostAuthorType.ESTABLISHMENT
        and experience.establishment_id
        != author.id
    ):
        raise WorkPostError(
            "Este serviço não pertence ao estabelecimento autor."
        )

    if (
        publishing
        and experience.status
        != ExperienceStatus.PUBLISHED
    ):
        raise WorkPostError(
            "Somente serviços publicados podem ser vinculados a uma publicação pública."
        )

    return experience


def create_work_post(
    *,
    user,
    author_type,
    image_url,
    author_id=None,
    caption=None,
    experience_id=None,
    status=WorkPostStatus.PUBLISHED,
    image_focus_x=50,
    image_focus_y=50,
):
    if status not in (
        WorkPostStatus.DRAFT,
        WorkPostStatus.PUBLISHED,
    ):
        raise WorkPostError(
            "Status inválido para nova publicação."
        )

    if not image_url:
        raise WorkPostError(
            "Adicione uma imagem à publicação."
        )

    publishing = (
        status
        == WorkPostStatus.PUBLISHED
    )

    author = creator_author(
        user=user,
        author_type=author_type,
        author_id=author_id,
        publishing=publishing,
    )

    experience = (
        _experience_for_author(
            experience_id=experience_id,
            author_type=author_type,
            author=author,
            publishing=publishing,
        )
    )

    post = WorkPost(
        author_type=author_type,
        professional_id=(
            author.id
            if author_type
            == WorkPostAuthorType.PROFESSIONAL
            else None
        ),
        establishment_id=(
            author.id
            if author_type
            == WorkPostAuthorType.ESTABLISHMENT
            else None
        ),
        experience_id=(
            experience.id
            if experience
            else None
        ),
        caption=_clean_caption(
            caption
        ),
        image_url=image_url,
        image_focus_x=_focus(
            image_focus_x,
            "Foco horizontal",
        ),
        image_focus_y=_focus(
            image_focus_y,
            "Foco vertical",
        ),
        status=status,
        published_at=(
            utcnow()
            if publishing
            else None
        ),
    )

    db.session.add(post)
    db.session.commit()

    return post


def update_work_post(
    *,
    user,
    post_id,
    caption=None,
    caption_supplied=False,
    experience_id=None,
    experience_supplied=False,
    status=None,
    image_focus_x=None,
    image_focus_y=None,
):
    post = _owned_post(
        user=user,
        post_id=post_id,
    )

    next_status = (
        status
        if status is not None
        else post.status
    )

    if next_status not in (
        WorkPostStatus.DRAFT,
        WorkPostStatus.PUBLISHED,
        WorkPostStatus.ARCHIVED,
    ):
        raise WorkPostError(
            "Status inválido."
        )

    publishing = (
        next_status
        == WorkPostStatus.PUBLISHED
    )

    author = creator_author(
        user=user,
        author_type=post.author_type,
        author_id=(
            post.professional_id
            if post.author_type
            == WorkPostAuthorType.PROFESSIONAL
            else post.establishment_id
        ),
        publishing=publishing,
    )

    if caption_supplied:
        post.caption = (
            _clean_caption(
                caption
            )
        )

    if experience_supplied:
        experience = (
            _experience_for_author(
                experience_id=experience_id,
                author_type=post.author_type,
                author=author,
                publishing=publishing,
            )
        )
        post.experience_id = (
            experience.id
            if experience
            else None
        )
    elif (
        publishing
        and post.experience_id
        is not None
    ):
        _experience_for_author(
            experience_id=post.experience_id,
            author_type=post.author_type,
            author=author,
            publishing=True,
        )

    if image_focus_x is not None:
        post.image_focus_x = (
            _focus(
                image_focus_x,
                "Foco horizontal",
            )
        )

    if image_focus_y is not None:
        post.image_focus_y = (
            _focus(
                image_focus_y,
                "Foco vertical",
            )
        )

    was_published = (
        post.status
        == WorkPostStatus.PUBLISHED
    )

    post.status = next_status

    if publishing and (
        not was_published
        or post.published_at
        is None
    ):
        post.published_at = (
            utcnow()
        )
    elif not publishing:
        post.published_at = None

    db.session.commit()

    return post


def replace_work_post_image(
    *,
    user,
    post_id,
    image_url,
    image_focus_x=50,
    image_focus_y=50,
):
    post = _owned_post(
        user=user,
        post_id=post_id,
    )

    if not image_url:
        raise WorkPostError(
            "Adicione uma imagem à publicação."
        )

    previous = post.image_url
    post.image_url = image_url
    post.image_focus_x = _focus(
        image_focus_x,
        "Foco horizontal",
    )
    post.image_focus_y = _focus(
        image_focus_y,
        "Foco vertical",
    )

    db.session.commit()

    return post, previous


def owned_work_post(
    *,
    user,
    post_id,
):
    return _owned_post(
        user=user,
        post_id=post_id,
    )


def delete_work_post(
    *,
    user,
    post_id,
):
    post = _owned_post(
        user=user,
        post_id=post_id,
    )
    image_url = post.image_url

    db.session.delete(post)
    db.session.commit()

    return image_url


def owned_posts_query(user):
    _require_user(user)

    professional_id = (
        user.professional_profile.id
        if user.professional_profile
        is not None
        else None
    )

    establishment_ids = [
        access.establishment_id
        for access
        in user.establishment_accesses
        if (
            access.status
            == EstablishmentAccessStatus.ACTIVE
        )
    ]

    from sqlalchemy import or_

    clauses = []

    if professional_id is not None:
        clauses.append(
            WorkPost.professional_id
            == professional_id
        )

    if establishment_ids:
        clauses.append(
            WorkPost.establishment_id.in_(
                establishment_ids
            )
        )

    if not clauses:
        return select(
            WorkPost
        ).where(
            WorkPost.id < 0
        )

    return (
        select(WorkPost)
        .where(
            or_(*clauses)
        )
        .order_by(
            WorkPost.created_at.desc(),
            WorkPost.id.desc(),
        )
    )
