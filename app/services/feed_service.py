from base64 import urlsafe_b64decode, urlsafe_b64encode

from sqlalchemy import and_, func, or_, select

from app.extensions import db
from app.models.beauty_graph import (
    Follow,
    FollowTarget,
)
from app.models.establishment import Establishment
from app.models.experience import Experience
from app.models.profile import ClientProfile
from app.models.professional import ProfessionalProfile
from app.models.user import User
from app.models.work_post import (
    CommentStatus,
    WorkPost,
    WorkPostAuthorType,
    WorkPostComment,
    WorkPostLike,
    WorkPostStatus,
)
from app.services.media_storage import resolve_image_url
from app.services.public_eligibility import (
    public_experiences_query,
)


class FeedError(ValueError):
    pass


def _public_post_query():
    return (
        select(WorkPost)
        .outerjoin(
            ProfessionalProfile,
            WorkPost.professional_id
            == ProfessionalProfile.id,
        )
        .outerjoin(
            Establishment,
            WorkPost.establishment_id
            == Establishment.id,
        )
        .outerjoin(
            ClientProfile,
            WorkPost.client_profile_id
            == ClientProfile.id,
        )
        .outerjoin(
            User,
            ClientProfile.user_id == User.id,
        )
        .where(
            WorkPost.status
            == WorkPostStatus.PUBLISHED,
            WorkPost.published_at.is_not(
                None
            ),
            or_(
                and_(
                    WorkPost.author_type
                    == WorkPostAuthorType.PROFESSIONAL,
                    ProfessionalProfile.is_active.is_(
                        True
                    ),
                ),
                and_(
                    WorkPost.author_type
                    == WorkPostAuthorType.ESTABLISHMENT,
                    Establishment.is_active.is_(
                        True
                    ),
                ),
                # DEC-ID-224: publicação da Cliente, de conta ativa.
                and_(
                    WorkPost.author_type
                    == WorkPostAuthorType.CLIENT,
                    User.is_active_account.is_(True),
                ),
            ),
        )
    )


def _cursor(post_id):
    raw = str(
        post_id
    ).encode("utf-8")

    return (
        urlsafe_b64encode(
            raw
        )
        .decode("ascii")
        .rstrip("=")
    )


def _parse_cursor(value):
    if not value:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise FeedError(
            "Cursor inválido."
        )

    try:
        padding = (
            "="
            * (
                -len(value)
                % 4
            )
        )
        decoded = (
            urlsafe_b64decode(
                (
                    value
                    + padding
                ).encode(
                    "ascii"
                )
            )
            .decode("utf-8")
        )
        post_id = int(
            decoded
        )
    except (
        ValueError,
        UnicodeError,
    ) as exc:
        raise FeedError(
            "Cursor inválido."
        ) from exc

    if post_id <= 0:
        raise FeedError(
            "Cursor inválido."
        )

    return post_id


def _public_experience_ids():
    return {
        item
        for item in db.session.scalars(
            public_experiences_query().with_only_columns(
                Experience.id
            )
        )
    }


def _media_url(value):
    if not value:
        return None

    return resolve_image_url(
        value,
        external=True,
    )


def _review_summary(author):
    reviews = [
        review
        for review
        in author.reviews_received
        if review.is_visible
    ]

    if not reviews:
        return (
            None,
            0,
        )

    return (
        round(
            sum(
                review.rating
                for review
                in reviews
            )
            / len(reviews),
            1,
        ),
        len(reviews),
    )


def _author_payload(post):
    if post.author_type == WorkPostAuthorType.CLIENT:
        # DEC-ID-227: só nome e foto; nada de cidade ou dados privados.
        profile = post.client_profile
        return {
            "id": str(profile.id),
            "routeId": None,
            "kind": "client",
            "name": profile.user.name,
            "avatar": _media_url(profile.avatar_url),
            "specialty": None,
            "rating": None,
            "reviewsCount": 0,
        }

    if (
        post.author_type
        == WorkPostAuthorType.PROFESSIONAL
    ):
        author = post.professional
        rating, reviews_count = (
            _review_summary(
                author
            )
        )

        return {
            "id": str(
                author.id
            ),
            "routeId": author.slug,
            "kind": "professional",
            "name": (
                author.display_name
            ),
            "avatar": _media_url(
                author.avatar_url
            ),
            "specialty": (
                author.primary_specialty
            ),
            "rating": rating,
            "reviewsCount":
                reviews_count,
        }

    author = post.establishment
    rating, reviews_count = (
        _review_summary(
            author
        )
    )

    return {
        "id": str(
            author.id
        ),
        "routeId": author.slug,
        "kind": "establishment",
        "name": author.name,
        "avatar": _media_url(
            author.logo_url
        ),
        "specialty": (
            author.category
        ),
        "rating": rating,
        "reviewsCount":
            reviews_count,
    }


def _service_payload(
    post,
    public_experience_ids,
):
    experience = (
        post.experience
    )

    if (
        experience is None
        or experience.id
        not in public_experience_ids
    ):
        return None

    return {
        "id": experience.slug,
        "name": (
            experience.title
        ),
        "price": float(
            experience.price
        ),
        "availabilityLabel": None,
        "image": _media_url(
            experience.image_url
        ),
        "category": (
            experience.category
        ),
    }


def _viewer_authorship(viewer):
    """O que a conta pode remover: própria Cliente/Pro, empresa de que é
    dona, ou post da empresa que ela criou (DEC-ID-232)."""
    if viewer is None or not getattr(viewer, "is_authenticated", False):
        return None
    from app.models.establishment import (
        EstablishmentAccessRole,
        EstablishmentAccessStatus,
    )

    accesses = [
        item for item in viewer.establishment_accesses
        if item.status == EstablishmentAccessStatus.ACTIVE
    ]
    return {
        "user_id": viewer.id,
        "client": viewer.client_profile.id if viewer.client_profile else None,
        "professional": viewer.professional_profile.id if viewer.professional_profile else None,
        "owned": {item.establishment_id for item in accesses if item.role == EstablishmentAccessRole.OWNER},
        "managed": {item.establishment_id for item in accesses},
    }


def _is_mine(post, authorship):
    if not authorship:
        return False
    if post.author_type == WorkPostAuthorType.CLIENT:
        return post.client_profile_id == authorship["client"]
    if post.author_type == WorkPostAuthorType.PROFESSIONAL:
        return post.professional_id == authorship["professional"]
    return post.establishment_id in authorship["owned"] or (
        post.establishment_id in authorship["managed"]
        and post.created_by_user_id == authorship["user_id"]
    )


def interaction_counts(post_ids, viewer=None):
    """Curtidas e comentários reais por post, numa consulta cada (D-SOC-08)."""
    post_ids = list(post_ids)
    if not post_ids:
        return {}

    likes = dict(
        db.session.execute(
            select(WorkPostLike.post_id, func.count(WorkPostLike.id))
            .where(WorkPostLike.post_id.in_(post_ids))
            .group_by(WorkPostLike.post_id)
        ).all()
    )
    comments = dict(
        db.session.execute(
            select(WorkPostComment.post_id, func.count(WorkPostComment.id))
            .where(
                WorkPostComment.post_id.in_(post_ids),
                WorkPostComment.status == CommentStatus.VISIBLE,
            )
            .group_by(WorkPostComment.post_id)
        ).all()
    )
    liked = set()
    if viewer is not None and getattr(viewer, "is_authenticated", False):
        liked = set(
            db.session.scalars(
                select(WorkPostLike.post_id).where(
                    WorkPostLike.post_id.in_(post_ids),
                    WorkPostLike.user_id == viewer.id,
                )
            )
        )

    result = {
        post_id: {
            "likes": likes.get(post_id, 0),
            "comments": comments.get(post_id, 0),
            "liked": post_id in liked,
        }
        for post_id in post_ids
    }
    result["_authorship"] = _viewer_authorship(viewer)
    return result


def serialize_work_post(
    post,
    *,
    public_experience_ids=None,
    counts=None,
):
    if public_experience_ids is None:
        public_experience_ids = (
            _public_experience_ids()
        )

    authorship = (counts or {}).get("_authorship")
    counts = (counts or {}).get(post.id, {})
    media = [
        {
            "url": _media_url(item.image_url),
            "focusX": item.focus_x,
            "focusY": item.focus_y,
            "alt": item.alt_text or "",
        }
        for item in post.media
    ]
    if not media and post.image_url:
        media = [
            {
                "url": _media_url(post.image_url),
                "focusX": post.image_focus_x,
                "focusY": post.image_focus_y,
                "alt": "",
            }
        ]

    return {
        "id": str(post.id),
        "authorId": (
            str(post.client_profile_id)
            if post.author_type == WorkPostAuthorType.CLIENT
            else str(
                post.professional_id
            )
            if post.author_type
            == WorkPostAuthorType.PROFESSIONAL
            else str(
                post.establishment_id
            )
        ),
        "authorKind": (
            post.author_type
        ),
        "author": (
            _author_payload(
                post
            )
        ),
        # Primeira imagem, para clientes antigos; nula em post só de texto.
        "image": media[0]["url"] if media else None,
        "media": media,
        "imageFocusX": (
            post.image_focus_x
        ),
        "imageFocusY": (
            post.image_focus_y
        ),
        "caption": (
            post.caption or ""
        ),
        "serviceId": (
            post.experience.slug
            if (
                post.experience_id
                is not None
                and post.experience_id
                in public_experience_ids
                and post.experience
                is not None
            )
            else None
        ),
        "service": (
            _service_payload(
                post,
                public_experience_ids,
            )
        ),
        "likesCount": counts.get("likes", 0),
        "commentsCount": counts.get("comments", 0),
        "likedByMe": counts.get("liked", False),
        # A conta vê o post como seu e pode removê-lo (DEC-ID-232).
        "mine": _is_mine(post, authorship),
        "publishedAt": (
            post.published_at.isoformat()
            if post.published_at
            else None
        ),
        "deepLink": (
            f"iddun://post/{post.id}"
        ),
    }


def feed_page(
    *,
    mode="for-you",
    user=None,
    cursor=None,
    limit=20,
):
    if mode not in (
        "for-you",
        "following",
    ):
        raise FeedError(
            "Modo de feed inválido."
        )

    try:
        parsed_limit = int(
            limit
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise FeedError(
            "Limite inválido."
        ) from exc

    parsed_limit = max(
        1,
        min(
            parsed_limit,
            50,
        ),
    )

    cursor_id = (
        _parse_cursor(
            cursor
        )
    )

    query = (
        _public_post_query()
    )

    if cursor_id is not None:
        query = query.where(
            WorkPost.id
            < cursor_id
        )

    if mode == "following":
        if (
            user is None
            or not user.is_active
        ):
            raise FeedError(
                "Entre na sua conta para ver quem você segue."
            )

        professional_ids = (
            select(
                Follow.professional_id
            ).where(
                Follow.user_id
                == user.id,
                Follow.target_type
                == FollowTarget.PROFESSIONAL,
                Follow.professional_id.is_not(
                    None
                ),
            )
        )

        establishment_ids = (
            select(
                Follow.establishment_id
            ).where(
                Follow.user_id
                == user.id,
                Follow.target_type
                == FollowTarget.ESTABLISHMENT,
                Follow.establishment_id.is_not(
                    None
                ),
            )
        )

        query = query.where(
            or_(
                and_(
                    WorkPost.author_type
                    == WorkPostAuthorType.PROFESSIONAL,
                    WorkPost.professional_id.in_(
                        professional_ids
                    ),
                ),
                and_(
                    WorkPost.author_type
                    == WorkPostAuthorType.ESTABLISHMENT,
                    WorkPost.establishment_id.in_(
                        establishment_ids
                    ),
                ),
            )
        )

    rows = db.session.scalars(
        query.order_by(
            WorkPost.id.desc()
        ).limit(
            parsed_limit
            + 1
        )
    ).all()

    has_more = (
        len(rows)
        > parsed_limit
    )
    page = rows[
        :parsed_limit
    ]

    public_ids = (
        _public_experience_ids()
    )
    counts = interaction_counts(
        [item.id for item in page],
        user,
    )

    return {
        "items": [
            serialize_work_post(
                item,
                public_experience_ids=public_ids,
                counts=counts,
            )
            for item in page
        ],
        "nextCursor": (
            _cursor(
                page[-1].id
            )
            if (
                has_more
                and page
            )
            else None
        ),
    }


def public_post_record(post_id):
    """O post se estiver publicado e com autoria ativa; senão None."""
    return db.session.scalar(
        _public_post_query().where(
            WorkPost.id == post_id
        )
    )


def public_post(
    post_id,
    viewer=None,
):
    post = public_post_record(post_id)

    if post is None:
        return None

    return serialize_work_post(
        post,
        counts=interaction_counts([post.id], viewer),
    )
