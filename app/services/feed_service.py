from base64 import urlsafe_b64decode, urlsafe_b64encode

from sqlalchemy import and_, or_, select

from app.extensions import db
from app.models.beauty_graph import (
    Follow,
    FollowTarget,
)
from app.models.establishment import Establishment
from app.models.experience import Experience
from app.models.professional import ProfessionalProfile
from app.models.work_post import (
    WorkPost,
    WorkPostAuthorType,
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


def serialize_work_post(
    post,
    *,
    public_experience_ids=None,
):
    if public_experience_ids is None:
        public_experience_ids = (
            _public_experience_ids()
        )

    return {
        "id": str(post.id),
        "authorId": (
            str(
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
        "image": _media_url(
            post.image_url
        ),
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
        "commentsCount": 0,
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

    return {
        "items": [
            serialize_work_post(
                item,
                public_experience_ids=public_ids,
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


def public_post(
    post_id,
):
    post = db.session.scalar(
        _public_post_query().where(
            WorkPost.id == post_id
        )
    )

    if post is None:
        return None

    return serialize_work_post(
        post
    )
