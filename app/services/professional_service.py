from copy import deepcopy

from sqlalchemy import select

from app.data.mock_professionals import PROFESSIONAL_CATALOG
from app.data.mock_marketplace import EXPERIENCE_CATALOG
from app.extensions import db
from app.models.establishment import Establishment, MembershipStatus
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.services.reputation_service import reputation_summary


def _db_item(profile):
    primary = next(
        (
            membership
            for membership in profile.memberships
            if membership.is_primary and membership.status == MembershipStatus.ACTIVE
        ),
        None,
    )
    location_parts = []
    if primary and primary.establishment.neighborhood:
        location_parts.append(primary.establishment.neighborhood)
    if profile.city:
        location_parts.append(profile.city)
    elif primary and primary.establishment.city:
        location_parts.append(primary.establishment.city)

    reputation = reputation_summary(profile.reviews_received)
    return {
        "slug": profile.slug,
        "name": profile.display_name,
        "role": profile.primary_specialty or "Profissional de beleza",
        "rating": reputation["average_label"],
        "reviews": str(reputation["count"]),
        "location": " · ".join(location_parts) or "Brasil",
        "image": profile.avatar_url or "img/category-hair.jpg",
        "image_position": f"{50 if profile.avatar_focus_x is None else profile.avatar_focus_x}% {50 if profile.avatar_focus_y is None else profile.avatar_focus_y}%",
        "specialties": profile.specialties or ["Curadoria IDDUN"],
        "verified": profile.is_verified,
        "source": "database",
        "theme": profile.visual_theme or "beauty",
    }


def list_professionals():
    database_items = [
        _db_item(item)
        for item in db.session.scalars(
            select(ProfessionalProfile)
            .where(ProfessionalProfile.is_active.is_(True))
            .order_by(ProfessionalProfile.is_verified.desc(), ProfessionalProfile.created_at.desc())
        ).all()
    ]
    db_slugs = {item["slug"] for item in database_items}
    mocks = []
    for source in deepcopy(PROFESSIONAL_CATALOG):
        if source["slug"] in db_slugs:
            continue
        source.setdefault("verified", True)
        source.setdefault("source", "mock")
        role = (source.get("role") or "").lower()
        source.setdefault("theme", "barber" if "barbe" in role else "beauty")
        mocks.append(source)
    return database_items + mocks


def get_professional_profile_by_slug(slug):
    return db.session.scalar(
        select(ProfessionalProfile).where(
            ProfessionalProfile.slug == slug,
            ProfessionalProfile.is_active.is_(True),
        )
    )


def get_professional_public_view(slug):
    profile = get_professional_profile_by_slug(slug)
    if profile is not None:
        workplaces = [
            membership.establishment
            for membership in profile.memberships
            if membership.status == MembershipStatus.ACTIVE
            and membership.establishment.is_active
        ]
        experiences = db.session.scalars(
            select(Experience)
            .where(
                Experience.professional_id == profile.id,
                Experience.status == ExperienceStatus.PUBLISHED,
            )
            .order_by(Experience.is_featured.desc(), Experience.created_at.desc())
        ).all()
        reputation = reputation_summary(profile.reviews_received)
        return {
            "source": "database",
            "profile": profile,
            "slug": profile.slug,
            "name": profile.display_name,
            "role": profile.primary_specialty or "Profissional de beleza",
            "headline": profile.headline,
            "bio": profile.bio,
            "rating": reputation["average_label"],
            "reviews": str(reputation["count"]),
            "reputation": reputation,
            "location": " · ".join(part for part in [profile.city, profile.state] if part) or "Brasil",
            "image": profile.avatar_url or "img/category-hair.jpg",
            "cover": profile.cover_url,
            "avatar_position": f"{profile.avatar_focus_x}% {profile.avatar_focus_y}%",
            "cover_position": f"{profile.cover_focus_x}% {profile.cover_focus_y}%",
            "specialties": profile.specialties,
            "verified": profile.is_verified,
            "portfolio": list(profile.portfolio_items),
            "workplaces": workplaces,
            "experiences": experiences,
            "theme": profile.visual_theme or "beauty",
            "instagram": profile.instagram,
            "whatsapp_available": bool(profile.whatsapp_enabled and profile.phone),
            "certifications": [item for item in profile.certifications if item.is_public],
            "review_items": [item for item in profile.reviews_received if item.is_visible],
        }

    mock = next((deepcopy(item) for item in PROFESSIONAL_CATALOG if item["slug"] == slug), None)
    if mock is None:
        return None

    role = (mock.get("role") or "").lower()
    return {
        "source": "mock",
        "profile": None,
        "slug": mock["slug"],
        "name": mock["name"],
        "role": mock["role"],
        "headline": f"{mock['role']} no IDDUN",
        "bio": "Conheça o trabalho, as especialidades e as experiências deste profissional dentro do IDDUN.",
        "rating": mock.get("rating", "Novo"),
        "reviews": mock.get("reviews", "0"),
        "location": mock.get("location", "Brasil"),
        "image": mock.get("image", "img/category-hair.jpg"),
        "cover": None,
        "avatar_position": mock.get("image_position", "50% 50%"),
        "cover_position": "50% 50%",
        "specialties": mock.get("specialties", []),
        "verified": True,
        "portfolio": [],
        "workplaces": [],
        "experiences": [
            {**deepcopy(item), "image_url": item.get("image"), "duration_minutes": item.get("duration_minutes", 90)}
            for item in EXPERIENCE_CATALOG
            if item.get("professional") == mock["name"]
        ],
        "theme": "barber" if "barbe" in role else "beauty",
        "instagram": None,
        "whatsapp_available": False,
        "certifications": [],
        "review_items": [],
        "reputation": {
            "count": 0,
            "average": None,
            "average_label": mock.get("rating", "Novo"),
            "recommendation_percent": None,
            "recommendation_label": "Sem avaliações verificadas no IDDUN",
        },
    }



def list_establishments():
    return db.session.scalars(
        select(Establishment)
        .where(Establishment.is_active.is_(True))
        .order_by(Establishment.is_verified.desc(), Establishment.created_at.desc())
    ).all()

def get_establishment_public_view(slug):
    establishment = db.session.scalar(
        select(Establishment).where(
            Establishment.slug == slug,
            Establishment.is_active.is_(True),
        )
    )
    if establishment is None:
        return None

    memberships = [
        membership
        for membership in establishment.memberships
        if membership.status == MembershipStatus.ACTIVE
        and membership.professional.is_active
    ]
    experiences = db.session.scalars(
        select(Experience)
        .where(
            Experience.establishment_id == establishment.id,
            Experience.status == ExperienceStatus.PUBLISHED,
        )
        .order_by(Experience.is_featured.desc(), Experience.created_at.desc())
    ).all()
    reputation = reputation_summary(establishment.reviews_received)
    return {
        "establishment": establishment,
        "team": memberships,
        "experiences": experiences,
        "theme": establishment.visual_theme or "beauty",
        "reputation": reputation,
        "review_items": [item for item in establishment.reviews_received if item.is_visible],
        "whatsapp_available": bool(establishment.whatsapp_enabled and establishment.phone),
    }
