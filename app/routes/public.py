from flask import Blueprint, abort, current_app, redirect, render_template, request

from app.data.mock_marketplace import CATEGORIES
from app.services.booking_service import grouped_available_slots
from app.services.contact_service import (
    establishment_whatsapp_url,
    professional_whatsapp_url,
    record_contact_click,
)
from app.services.experience_service import (
    get_database_experience_by_slug,
    get_experience_by_slug,
    list_experiences,
    list_locations,
)
from app.services.google_calendar_service import sync_professional_if_stale
from app.services.home_stats_service import get_home_stats
from app.services.professional_service import (
    get_establishment_public_view,
    get_professional_public_view,
    list_establishments,
    list_professionals,
)
from app.services.reputation_service import reputation_summary


public_bp = Blueprint("public", __name__)


# ============================================================
# HOME — PRESENTATION DATA
# ============================================================

HOME_CATEGORIES = [
    {
        "name": "Cabelo",
        "subtitle": "Cortes, coloração, tratamentos",
        "image": "img/category-hair.jpg",
        "value": "cabelo",
        "position": "50% 44%",
    },
    {
        "name": "Unhas",
        "subtitle": "Manicure, nail art, alongamento",
        "image": "img/category-nails.jpg",
        "value": "unhas",
        "position": "50% 50%",
    },
    {
        "name": "Barbearia",
        "subtitle": "Corte, barba, visagismo",
        "image": "img/category-barber.jpg",
        "value": "barbearia",
        "position": "50% 45%",
    },
    {
        "name": "Estética",
        "subtitle": "Facial, corporal, bem-estar",
        "image": "img/exp-hair.jpg",
        "value": "estetica",
        "position": "50% 38%",
    },
    {
        "name": "Tatuagem",
        "subtitle": "Arte na pele, expressão",
        "image": "img/category-tattoo.svg",
        "value": "tatuagem",
        "position": "50% 50%",
    },
    {
        "name": "Sobrancelhas",
        "subtitle": "Design, henna, laminação",
        "image": "img/hero-woman-v3.webp",
        "value": "sobrancelhas",
        "position": "79% 27%",
    },
]


# ============================================================
# TEMPORARY HOME FALLBACKS
#
# These entries exist only to preserve the prototype presentation
# while the production catalog is still being populated.
#
# They must not become the long-term production source of truth.
# ============================================================

HOME_ESTABLISHMENT_FALLBACKS = [
    {
        "name": "Lume Beauty Studio",
        "slug": None,
        "rating": "4,9",
        "reviews": "412",
        "location": "Batel · Curitiba",
        "image": "img/hero-model.png",
        "image_position": "70% 52%",
        "tags": [
            "Cabelo",
            "Estética",
            "Unhas",
        ],
    },
    {
        "name": "Verve Estúdio",
        "slug": None,
        "rating": "4,8",
        "reviews": "320",
        "location": "Água Verde · Curitiba",
        "image": "img/category-hair.jpg",
        "image_position": "50% 45%",
        "tags": [
            "Cabelo",
            "Barbearia",
            "Estética",
        ],
    },
    {
        "name": "Alma Concept",
        "slug": None,
        "rating": "4,9",
        "reviews": "278",
        "location": "Juvevê · Curitiba",
        "image": "img/hero-woman-v3.webp",
        "image_position": "72% 55%",
        "tags": [
            "Estética",
            "Sobrancelhas",
            "Bem-estar",
        ],
    },
    {
        "name": "Raiz Estúdio",
        "slug": None,
        "rating": "4,7",
        "reviews": "198",
        "location": "Cabral · Curitiba",
        "image": "img/category-barber.jpg",
        "image_position": "50% 48%",
        "tags": [
            "Cabelo",
            "Unhas",
            "Estética",
        ],
    },
]


# ============================================================
# HOME HELPERS
# ============================================================

def _establishment_location(establishment):
    parts = [
        establishment.neighborhood,
        establishment.city,
    ]

    location = " · ".join(
        part
        for part in parts
        if part
    )

    return location or "Brasil"


def _establishment_home_card(establishment):
    reputation = reputation_summary(
        establishment.reviews_received
    )

    return {
        "name": establishment.name,
        "slug": establishment.slug,
        "rating": reputation["average_label"],
        "reviews": str(reputation["count"]),
        "location": _establishment_location(
            establishment
        ),
        "image": (
            establishment.cover_url
            or establishment.logo_url
            or "img/hero-model.png"
        ),
        "image_position": (
            f"{establishment.cover_focus_x}% "
            f"{establishment.cover_focus_y}%"
        ),
        "tags": [
            establishment.category
            or "Beleza",
            "Curadoria IDDUN",
        ],
    }


def _home_establishments(limit=4):
    establishments = list_establishments()[:limit]

    cards = [
        _establishment_home_card(
            establishment
        )
        for establishment in establishments
    ]

    if current_app.config["APP_ENV"] == "production":
        return cards

    # --------------------------------------------------------
    # Temporary prototype fallback.
    #
    # Real database records always have priority.
    # Fallback items only complete the visual section while
    # fewer than `limit` establishments exist in the database.
    # --------------------------------------------------------

    used_names = {
        item["name"]
        for item in cards
    }

    for fallback in HOME_ESTABLISHMENT_FALLBACKS:
        if len(cards) >= limit:
            break

        if fallback["name"] in used_names:
            continue

        cards.append(
            fallback.copy()
        )

        used_names.add(
            fallback["name"]
        )

    return cards[:limit]


def _home_data():
    professionals = (
        list_professionals()[:4]
    )

    establishments = (
        _home_establishments(
            limit=4
        )
    )

    return (
        HOME_CATEGORIES,
        professionals,
        establishments,
    )


# ============================================================
# HOME
# ============================================================

@public_bp.get("/")
def home():
    (
        categories,
        professionals,
        studios,
    ) = _home_data()

    return render_template(
        "public/home.html",
        categories=categories,
        professionals=professionals,
        studios=studios,
        home_stats=get_home_stats(),
        current_page="home",
    )


# ============================================================
# HOW IT WORKS
# ============================================================

@public_bp.get("/como-funciona")
def how_it_works():
    return render_template(
        "public/how-it-works.html",
        current_page="how-it-works",
    )


# ============================================================
# DISCOVERY / EXPERIENCES
# ============================================================

@public_bp.get("/experiencias")
def experiences():
    search = request.args.get(
        "q",
        "",
    )

    category = request.args.get(
        "categoria",
        "",
    )

    location = request.args.get(
        "bairro",
        "",
    )

    sort = request.args.get(
        "ordem",
        "recommended",
    )

    # --------------------------------------------------------
    # A single source feeds both results and category counters.
    #
    # Category filtering happens afterwards so the category
    # pills can continue showing totals for the current search.
    # --------------------------------------------------------

    available_items = list_experiences(
        search=search,
        location=location,
        sort=sort,
    )

    category_counts = {
        item["value"]: sum(
            1
            for experience
            in available_items
            if experience[
                "category"
            ].casefold()
            == item[
                "value"
            ].casefold()
        )
        for item
        in CATEGORIES
    }

    normalized_category = (
        category
        .strip()
        .casefold()
    )

    if normalized_category:
        items = [
            item
            for item
            in available_items
            if item[
                "category"
            ].casefold()
            == normalized_category
        ]
    else:
        items = available_items

    featured_experience = next(
        (
            item
            for item
            in items
            if item.get(
                "featured"
            )
        ),
        items[0]
        if items
        else None,
    )

    regular_experiences = [
        item
        for item
        in items
        if (
            featured_experience
            is None
            or item["slug"]
            != featured_experience[
                "slug"
            ]
        )
    ]

    return render_template(
        "public/experiences.html",
        experiences=items,
        featured_experience=(
            featured_experience
        ),
        regular_experiences=(
            regular_experiences
        ),
        categories=CATEGORIES,
        category_counts=(
            category_counts
        ),
        available_count=len(
            available_items
        ),
        locations=list_locations(),
        filters={
            "q": search,
            "categoria": category,
            "bairro": location,
            "ordem": sort,
        },
        current_page="experiences",
    )


# ============================================================
# EXPERIENCE DETAIL
# ============================================================

@public_bp.get(
    "/experiencias/<slug>"
)
def experience_detail(slug):
    item = get_experience_by_slug(
        slug
    )

    if item is None:
        abort(404)

    db_experience = (
        get_database_experience_by_slug(
            slug
        )
    )

    if db_experience is not None:
        sync_professional_if_stale(
            db_experience.professional_id
        )

        slot_groups = (
            grouped_available_slots(
                db_experience
            )
        )

    else:
        # Prototype catalog entries do not have real slots.
        slot_groups = []

    return render_template(
        "public/experience-detail.html",
        experience=item,
        db_experience=db_experience,
        slot_groups=slot_groups,
        current_page="experiences",
    )


# ============================================================
# PROFESSIONALS
# ============================================================

@public_bp.get("/profissionais")
def professionals():
    return render_template(
        "public/professionals.html",
        professionals=(
            list_professionals()
        ),
        current_page="professionals",
    )


@public_bp.get(
    "/profissionais/<slug>"
)
def professional_detail(slug):
    professional = (
        get_professional_public_view(
            slug
        )
    )

    if professional is None:
        abort(404)

    return render_template(
        "public/professional-detail.html",
        professional=professional,
        current_page="professionals",
    )


# ============================================================
# PROFESSIONAL ACQUISITION
# ============================================================

@public_bp.get(
    "/para-profissionais"
)
def for_professionals():
    return render_template(
        "public/for-professionals.html",
        current_page=(
            "for-professionals"
        ),
    )


# ============================================================
# ESTABLISHMENTS
# ============================================================

@public_bp.get(
    "/estabelecimentos"
)
def establishments():
    return render_template(
        "public/establishments.html",
        establishments=(
            list_establishments()
        ),
        current_page=(
            "establishments"
        ),
    )


@public_bp.get(
    "/estabelecimentos/<slug>"
)
def establishment_detail(slug):
    business = (
        get_establishment_public_view(
            slug
        )
    )

    if business is None:
        abort(404)

    return render_template(
        "public/establishment-detail.html",
        business=business,

        # Important:
        # This used to be "professionals", which caused the
        # wrong navigation item to be highlighted.
        current_page="establishments",
    )


# ============================================================
# CONTACT / WHATSAPP
# ============================================================

@public_bp.get(
    "/contato/profissional/<slug>/whatsapp"
)
def professional_whatsapp(slug):
    professional = (
        get_professional_public_view(
            slug
        )
    )

    # Mock/prototype professionals must not generate
    # real contact-tracking entries.
    if (
        professional is None
        or professional.get(
            "source"
        ) != "database"
    ):
        abort(404)

    profile = professional[
        "profile"
    ]

    target = professional_whatsapp_url(
        profile
    )

    if not target:
        abort(404)

    record_contact_click(
        professional=profile
    )

    return redirect(
        target
    )


@public_bp.get(
    "/contato/estabelecimento/<slug>/whatsapp"
)
def establishment_whatsapp(slug):
    business = (
        get_establishment_public_view(
            slug
        )
    )

    if business is None:
        abort(404)

    establishment = business[
        "establishment"
    ]

    target = (
        establishment_whatsapp_url(
            establishment
        )
    )

    if not target:
        abort(404)

    record_contact_click(
        establishment=(
            establishment
        )
    )

    return redirect(
        target
    )