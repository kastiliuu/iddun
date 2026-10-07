from sqlalchemy import or_, select

from app.extensions import db
from app.models.booking import (
    Booking,
    BookingStatus,
    ExperienceSlot,
)
from app.models.establishment import Establishment
from app.models.professional import ProfessionalProfile
from app.services.availability_service import (
    iddun_now_slots,
    slot_is_urgent,
    slot_time_label,
)
from app.services.beauty_graph_service import (
    graph_state,
    saved_items,
)
from app.services.feed_service import feed_page
from app.services.media_storage import resolve_image_url
from app.services.notification_service import list_notifications
from app.services.profile_service import ensure_client_profile
from app.services.public_eligibility import (
    public_establishments_query,
    public_professionals_query,
)
from app.services.reputation_service import reputation_summary
from app.services.time_service import utcnow


def _profile_completion(user, profile):
    fields = {
        "nome": user.name,
        "e-mail": user.email,
        "foto": profile.avatar_url,
        "telefone": profile.phone,
        "data de nascimento": profile.birth_date,
        "cidade": profile.city,
        "UF": profile.state,
    }

    completed = sum(
        bool(value)
        for value in fields.values()
    )

    missing = [
        label
        for label, value in fields.items()
        if not value
    ]

    return {
        "percentage": round(
            (
                completed
                / len(fields)
            )
            * 100
        ),
        "missing": missing,
        "next": (
            missing[0]
            if missing
            else None
        ),
    }


def _next_booking(profile):
    return db.session.scalar(
        select(Booking)
        .join(
            ExperienceSlot,
            Booking.slot_id
            == ExperienceSlot.id,
        )
        .where(
            Booking.client_id
            == profile.id,
            Booking.status.in_(
                (
                    BookingStatus.PENDING,
                    BookingStatus.CONFIRMED,
                )
            ),
            ExperienceSlot.starts_at
            >= utcnow(),
        )
        .order_by(
            ExperienceSlot.starts_at.asc(),
            Booking.id.asc(),
        )
        .limit(1)
    )


def _location_label(
    *,
    neighborhood=None,
    city=None,
    state=None,
):
    parts = [
        part
        for part in (
            neighborhood,
            city,
            state,
        )
        if part
    ]

    return (
        " · ".join(parts)
        if parts
        else "Brasil"
    )


def _profile_recommendation(
    item,
    *,
    kind,
):
    reputation = reputation_summary(
        item.reviews_received
    )

    if kind == "professional":
        return {
            "id": item.id,
            "kind": kind,
            "slug": item.slug,
            "name": item.display_name,
            "specialty": (
                item.primary_specialty
                or "Profissional de beleza"
            ),
            "location": _location_label(
                city=item.city,
                state=item.state,
            ),
            "avatar": resolve_image_url(
                item.avatar_url
                or "img/category-hair.jpg"
            ),
            "rating": reputation[
                "average_label"
            ],
            "reviews": reputation[
                "count"
            ],
            "verified": item.is_verified,
        }

    return {
        "id": item.id,
        "kind": kind,
        "slug": item.slug,
        "name": item.name,
        "specialty": (
            item.category
            or "Estabelecimento de beleza"
        ),
        "location": _location_label(
            neighborhood=item.neighborhood,
            city=item.city,
            state=item.state,
        ),
        "avatar": resolve_image_url(
            item.logo_url
            or "img/category-hair.jpg"
        ),
        "rating": reputation[
            "average_label"
        ],
        "reviews": reputation[
            "count"
        ],
        "verified": item.is_verified,
    }


def _recommendations(
    *,
    user,
    profile,
    graph,
    limit=4,
):
    followed_professionals = {
        item["targetId"]
        for item in graph["follows"]
        if (
            item["targetType"]
            == "professional"
        )
    }

    followed_establishments = {
        item["targetId"]
        for item in graph["follows"]
        if (
            item["targetType"]
            == "establishment"
        )
    }

    professional_query = (
        public_professionals_query()
        .where(
            or_(
                ProfessionalProfile.user_id.is_(
                    None
                ),
                ProfessionalProfile.user_id
                != user.id,
            )
        )
        .order_by(
            ProfessionalProfile.is_verified.desc(),
            ProfessionalProfile.created_at.desc(),
        )
    )

    managed_establishment_ids = {
        access.establishment_id
        for access
        in user.establishment_accesses
    }

    establishment_query = (
        public_establishments_query()
        .order_by(
            Establishment.is_verified.desc(),
            Establishment.created_at.desc(),
        )
    )

    if followed_professionals:
        professional_query = (
            professional_query.where(
                ProfessionalProfile.id.not_in(
                    followed_professionals
                )
            )
        )

    excluded_establishments = (
        followed_establishments
        | managed_establishment_ids
    )

    if excluded_establishments:
        establishment_query = (
            establishment_query.where(
                Establishment.id.not_in(
                    excluded_establishments
                )
            )
        )

    professionals = list(
        db.session.scalars(
            professional_query.limit(
                limit * 2
            )
        ).all()
    )

    establishments = list(
        db.session.scalars(
            establishment_query.limit(
                limit * 2
            )
        ).all()
    )

    if profile.city:
        city = profile.city.strip().casefold()

        professionals.sort(
            key=lambda item: (
                (
                    item.city
                    or ""
                ).strip().casefold()
                != city,
                not item.is_verified,
                -item.id,
            )
        )

        establishments.sort(
            key=lambda item: (
                (
                    item.city
                    or ""
                ).strip().casefold()
                != city,
                not item.is_verified,
                -item.id,
            )
        )

    return {
        "professionals": [
            _profile_recommendation(
                item,
                kind="professional",
            )
            for item in professionals[
                :limit
            ]
        ],
        "establishments": [
            _profile_recommendation(
                item,
                kind="establishment",
            )
            for item in establishments[
                :limit
            ]
        ],
    }


def _iddun_now_payload(slot):
    establishment = (
        slot.establishment
    )

    return {
        "id": slot.id,
        "experienceSlug": (
            slot.experience.slug
        ),
        "experienceTitle": (
            slot.experience.title
        ),
        "professionalName": (
            slot.professional.display_name
        ),
        "professionalSlug": (
            slot.professional.slug
        ),
        "image": resolve_image_url(
            slot.experience.image_url
            or slot.professional.avatar_url
            or "img/exp-hair.jpg"
        ),
        "timeLabel": slot_time_label(
            slot
        ),
        "urgent": slot_is_urgent(
            slot
        ),
        "price": float(
            slot.experience.price
        ),
        "location": _location_label(
            neighborhood=(
                establishment.neighborhood
                if establishment
                else None
            ),
            city=(
                establishment.city
                if establishment
                else slot.professional.city
            ),
            state=(
                establishment.state
                if establishment
                else slot.professional.state
            ),
        ),
    }


def client_feed_page(
    user,
    *,
    mode="for-you",
    cursor=None,
    limit=24,
):
    graph = graph_state(
        user
    )

    page = feed_page(
        mode=mode,
        user=user,
        cursor=cursor,
        limit=limit,
    )

    return {
        "feed_items":
            page_context[
                "feed_items"
            ],
        "next_cursor":
            page_context[
                "next_cursor"
            ],
        "followed_keys": {
            (
                item["targetType"],
                item["targetId"],
            )
            for item in graph[
                "follows"
            ]
        },
        "saved_keys": {
            (
                item["targetType"],
                item["targetId"],
            )
            for item in graph[
                "saves"
            ]
        },
        "graph": graph,
    }


def client_feed_context(
    user,
    *,
    mode="for-you",
    limit=24,
):
    profile = ensure_client_profile(
        user
    )

    page_context = client_feed_page(
        user,
        mode=mode,
        limit=limit,
    )

    graph = page_context["graph"]

    notifications, _, unread_count = (
        list_notifications(
            user,
            limit=6,
        )
    )

    next_booking = _next_booking(
        profile
    )

    recommendations = _recommendations(
        user=user,
        profile=profile,
        graph=graph,
    )

    now_items = [
        _iddun_now_payload(
            item
        )
        for item in iddun_now_slots(
            limit=4,
            mode="all",
        )
    ]

    return {
        "profile": profile,
        "profile_completion":
            _profile_completion(
                user,
                profile,
            ),
        "feed_items":
            page["items"],
        "next_cursor":
            page["nextCursor"],
        "mode": mode,
        "follow_count": len(
            graph["follows"]
        ),
        "save_count": len(
            graph["saves"]
        ),
        "followed_keys":
            page_context[
                "followed_keys"
            ],
        "saved_keys":
            page_context[
                "saved_keys"
            ],
        "notifications":
            notifications,
        "unread_notification_count":
            unread_count,
        "next_booking":
            next_booking,
        "next_booking_label": (
            slot_time_label(
                next_booking.slot
            )
            if next_booking
            is not None
            else None
        ),
        "saved_items":
            saved_items(user),
        "iddun_now":
            now_items,
        "recommended_professionals":
            recommendations[
                "professionals"
            ],
        "recommended_establishments":
            recommendations[
                "establishments"
            ],
    }
