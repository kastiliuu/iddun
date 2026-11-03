from sqlalchemy import select

from app.extensions import db
from app.models.establishment import (
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.work_post import (
    MAX_POST_IMAGES,
    WorkPost,
    WorkPostAuthorType,
    WorkPostMedia,
    WorkPostStatus,
    utcnow,
)
from app.services.profile_service import ensure_client_profile
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

    if author_type == WorkPostAuthorType.CLIENT:
        # DEC-ID-224: a Cliente publica no próprio contexto.
        profile = ensure_client_profile(user)
        if author_id is not None and profile.id != author_id:
            raise WorkPostError(
                "Perfil de cliente não encontrado para esta conta."
            )
        return profile

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
                # D-SOC-02: só a dona publica como empresa até existir
                # permissão de conteúdo (DEC-ID-224, AUD-14).
                EstablishmentUserAccess.role
                == EstablishmentAccessRole.OWNER,
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
    """
    Publicação que a conta pode editar e remover (DEC-ID-232): a própria
    como Cliente ou Pro; da empresa, a dona ou quem criou o post enquanto
    tiver acesso ativo. Removida não volta.
    """
    _require_user(user)

    post = db.session.get(
        WorkPost,
        post_id,
    )

    if post is None or post.status == WorkPostStatus.REMOVED:
        raise WorkPostError(
            "Publicação não encontrada."
        )

    if post.author_type == WorkPostAuthorType.CLIENT:
        profile = user.client_profile
        if profile is None or profile.id != post.client_profile_id:
            raise WorkPostError(
                "Publicação não encontrada."
            )
        return post

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
            EstablishmentUserAccess
        ).where(
            EstablishmentUserAccess.user_id
            == user.id,
            EstablishmentUserAccess.establishment_id
            == post.establishment_id,
            EstablishmentUserAccess.status
            == EstablishmentAccessStatus.ACTIVE,
        )
    )

    if access is None or not (
        access.role == EstablishmentAccessRole.OWNER
        or (
            post.created_by_user_id is not None
            and post.created_by_user_id == user.id
        )
    ):
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


def _clean_alt(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise WorkPostError("Texto alternativo inválido.")
    clean = value.strip()
    if len(clean) > 300:
        raise WorkPostError(
            "O texto alternativo deve ter no máximo 300 caracteres."
        )
    return clean or None


def _normalized_images(images, image_url, image_focus_x, image_focus_y):
    """Lista ordenada de imagens; aceita o formato antigo de uma imagem."""
    if images is None:
        images = (
            [{"image_url": image_url, "focus_x": image_focus_x, "focus_y": image_focus_y}]
            if image_url
            else []
        )

    if len(images) > MAX_POST_IMAGES:
        raise WorkPostError(
            f"Uma publicação pode ter até {MAX_POST_IMAGES} imagens."
        )

    clean = []
    for item in images:
        if not item.get("image_url"):
            raise WorkPostError("Imagem inválida.")
        clean.append(
            {
                "image_url": item["image_url"],
                "focus_x": _focus(item.get("focus_x"), "Foco horizontal"),
                "focus_y": _focus(item.get("focus_y"), "Foco vertical"),
                "alt_text": _clean_alt(item.get("alt_text")),
            }
        )
    return clean


def create_work_post(
    *,
    user,
    author_type,
    image_url=None,
    author_id=None,
    caption=None,
    experience_id=None,
    status=WorkPostStatus.PUBLISHED,
    image_focus_x=50,
    image_focus_y=50,
    images=None,
):
    """
    Texto, imagem única ou carrossel até 10 (DEC-ID-225). Publicação vazia
    é recusada. `images` é uma lista de {image_url, focus_x, focus_y,
    alt_text}; `image_url` continua aceito para uma imagem só.
    """
    if status not in (
        WorkPostStatus.DRAFT,
        WorkPostStatus.PUBLISHED,
    ):
        raise WorkPostError(
            "Status inválido para nova publicação."
        )

    media = _normalized_images(images, image_url, image_focus_x, image_focus_y)
    clean_caption = _clean_caption(caption)

    if not media and not clean_caption:
        raise WorkPostError(
            "Escreva um texto ou adicione uma imagem."
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

    if author_type == WorkPostAuthorType.CLIENT and experience_id not in (None, ""):
        raise WorkPostError(
            "Somente Pro e empresa vinculam serviços à publicação."
        )

    experience = (
        _experience_for_author(
            experience_id=experience_id,
            author_type=author_type,
            author=author,
            publishing=publishing,
        )
    )

    cover = media[0] if media else None

    post = WorkPost(
        author_type=author_type,
        client_profile_id=(
            author.id
            if author_type == WorkPostAuthorType.CLIENT
            else None
        ),
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
        created_by_user_id=user.id,
        experience_id=(
            experience.id
            if experience
            else None
        ),
        caption=clean_caption,
        image_url=cover["image_url"] if cover else None,
        image_focus_x=cover["focus_x"] if cover else 50,
        image_focus_y=cover["focus_y"] if cover else 50,
        status=status,
        published_at=(
            utcnow()
            if publishing
            else None
        ),
    )

    post.media = [
        WorkPostMedia(
            position=index,
            image_url=item["image_url"],
            focus_x=item["focus_x"],
            focus_y=item["focus_y"],
            alt_text=item["alt_text"],
        )
        for index, item in enumerate(media)
    ]

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

    if post.status == WorkPostStatus.HIDDEN:
        # Ocultado pela moderação: só a equipe da plataforma restaura.
        raise WorkPostError(
            "Esta publicação está em análise e não pode ser alterada agora."
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
            post.client_profile_id
            if post.author_type == WorkPostAuthorType.CLIENT
            else post.professional_id
            if post.author_type
            == WorkPostAuthorType.PROFESSIONAL
            else post.establishment_id
        ),
        publishing=publishing,
    )

    if (
        experience_supplied
        and post.author_type == WorkPostAuthorType.CLIENT
        and experience_id not in (None, "")
    ):
        raise WorkPostError(
            "Somente Pro e empresa vinculam serviços à publicação."
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

    if post.media and (image_focus_x is not None or image_focus_y is not None):
        post.media[0].focus_x = post.image_focus_x
        post.media[0].focus_y = post.image_focus_y

    if caption_supplied and not post.caption and not post.media:
        raise WorkPostError(
            "Escreva um texto ou adicione uma imagem."
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

    # A primeira imagem do carrossel acompanha a capa.
    if post.media:
        cover = post.media[0]
        cover.image_url = image_url
        cover.focus_x = post.image_focus_x
        cover.focus_y = post.image_focus_y
    else:
        post.media.append(
            WorkPostMedia(
                position=0,
                image_url=image_url,
                focus_x=post.image_focus_x,
                focus_y=post.image_focus_y,
            )
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
    """
    D-SOC-09: remoção lógica. O post some de tudo na hora, as imagens saem
    do armazenamento e a linha fica para o histórico das denúncias.
    Devolve os caminhos das imagens para apagar depois do commit.
    """
    post = _owned_post(
        user=user,
        post_id=post_id,
    )

    paths = [item.image_url for item in post.media]
    if post.image_url and post.image_url not in paths:
        paths.append(post.image_url)

    post.media = []
    post.image_url = None
    post.status = WorkPostStatus.REMOVED
    post.removed_at = utcnow()
    db.session.commit()

    return paths


def creator_options(user):
    """Contextos em que a conta pode publicar (DEC-ID-224, D-SOC-02)."""
    _require_user(user)

    client = ensure_client_profile(user)
    authors = [
        {
            "type": WorkPostAuthorType.CLIENT,
            "id": client.id,
            "name": user.name,
        }
    ]
    professional_ids = []
    establishment_ids = []

    professional = (
        user.professional_profile
    )

    if (
        professional is not None
        and professional_is_public(
            professional
        )
    ):
        professional_ids.append(
            professional.id
        )
        authors.append(
            {
                "type":
                    WorkPostAuthorType.PROFESSIONAL,
                "id":
                    professional.id,
                "name":
                    professional.display_name,
            }
        )

    for access in (
        user.establishment_accesses
    ):
        if (
            access.status
            != EstablishmentAccessStatus.ACTIVE
            or access.role
            != EstablishmentAccessRole.OWNER
            or access.establishment
            is None
            or not establishment_is_public(
                access.establishment
            )
        ):
            continue

        establishment_ids.append(
            access.establishment_id
        )
        authors.append(
            {
                "type":
                    WorkPostAuthorType.ESTABLISHMENT,
                "id":
                    access.establishment_id,
                "name":
                    access.establishment.name,
            }
        )

    conditions = []

    if professional_ids:
        conditions.append(
            Experience.professional_id.in_(
                professional_ids
            )
        )

    if establishment_ids:
        conditions.append(
            Experience.establishment_id.in_(
                establishment_ids
            )
        )

    experiences = []

    if conditions:
        from sqlalchemy import or_

        rows = db.session.scalars(
            select(Experience)
            .where(
                Experience.status
                == ExperienceStatus.PUBLISHED,
                or_(*conditions),
            )
            .order_by(
                Experience.title.asc(),
                Experience.id.asc(),
            )
        ).all()

        for item in rows:
            if (
                item.professional_id
                in professional_ids
            ):
                experiences.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "authorType":
                            WorkPostAuthorType.PROFESSIONAL,
                        "authorId":
                            item.professional_id,
                    }
                )

            if (
                item.establishment_id
                in establishment_ids
            ):
                experiences.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "authorType":
                            WorkPostAuthorType.ESTABLISHMENT,
                        "authorId":
                            item.establishment_id,
                    }
                )

    return {
        "authors": authors,
        "experiences": experiences,
    }


def owned_posts_query(user):
    _require_user(user)

    professional_id = (
        user.professional_profile.id
        if user.professional_profile
        is not None
        else None
    )

    owned_establishments = [
        access.establishment_id
        for access
        in user.establishment_accesses
        if (
            access.status
            == EstablishmentAccessStatus.ACTIVE
            and access.role == EstablishmentAccessRole.OWNER
        )
    ]
    managed_establishments = [
        access.establishment_id
        for access
        in user.establishment_accesses
        if access.status == EstablishmentAccessStatus.ACTIVE
    ]

    from sqlalchemy import and_, or_

    clauses = []

    if user.client_profile is not None:
        clauses.append(
            WorkPost.client_profile_id == user.client_profile.id
        )

    if managed_establishments:
        # Quem criou o post da empresa continua vendo enquanto tiver acesso.
        clauses.append(
            and_(
                WorkPost.establishment_id.in_(managed_establishments),
                WorkPost.created_by_user_id == user.id,
            )
        )

    if professional_id is not None:
        clauses.append(
            WorkPost.professional_id
            == professional_id
        )

    if owned_establishments:
        clauses.append(
            WorkPost.establishment_id.in_(
                owned_establishments
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
            or_(*clauses),
            WorkPost.status != WorkPostStatus.REMOVED,
        )
        .order_by(
            WorkPost.created_at.desc(),
            WorkPost.id.desc(),
        )
    )
