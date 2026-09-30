"""Criação de rascunhos de perfis pelo aplicativo móvel.

O onboarding web exige mídia e outros campos antes de publicar um perfil.
O mobile pode criar o mesmo registro como rascunho inativo; os catálogos
públicos do projeto filtram ``is_active``. A etapa de publicação poderá
ativar o rascunho quando os demais requisitos forem cumpridos.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.platform import BUSINESS_CATEGORY_CHOICES
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.professional import ProfessionalProfile, utcnow
from app.services.slug_service import unique_public_handle


class MobileOnboardingError(ValueError):
    """Dados inválidos ou perfil que não pôde ser criado."""


PROFESSIONAL_CATEGORIES = {
    "cabelo": "Cabelo",
    "unhas": "Unhas",
    "barbearia": "Barbearia",
    "estetica": "Estética",
    "maquiagem": "Maquiagem",
    "sobrancelhas": "Sobrancelhas",
    "tatuagem": "Tatuagem",
    "massagem": "Massagem",
}

BUSINESS_CATEGORIES = {
    value for value, _ in BUSINESS_CATEGORY_CHOICES
}


def _text(value, label, *, minimum=0, maximum, required=False):
    if not isinstance(value, str):
        raise MobileOnboardingError(
            f"{label}: informe um texto válido."
        )

    clean = value.strip()

    if required and not clean:
        raise MobileOnboardingError(
            f"{label}: preenchimento obrigatório."
        )

    if clean and len(clean) < minimum:
        raise MobileOnboardingError(
            f"{label}: use pelo menos {minimum} caracteres."
        )

    if len(clean) > maximum:
        raise MobileOnboardingError(
            f"{label}: use no máximo {maximum} caracteres."
        )

    return clean


def _active_user(user):
    if user is None or user.id is None or not user.is_active:
        raise MobileOnboardingError(
            "Entre em uma conta ativa para criar seu perfil."
        )


def _location(city, state):
    clean_city = _text(
        city,
        "Cidade",
        minimum=2,
        maximum=100,
        required=True,
    )

    clean_state = _text(
        state,
        "UF",
        minimum=2,
        maximum=2,
        required=True,
    ).upper()

    if len(clean_state) != 2 or not clean_state.isalpha():
        raise MobileOnboardingError(
            "UF: informe duas letras."
        )

    return clean_city, clean_state


def _professional_categories(categories):
    if not isinstance(categories, (list, tuple)) or not categories:
        raise MobileOnboardingError(
            "Selecione ao menos uma área de atuação."
        )

    selected = []

    for category in categories:
        if (
            not isinstance(category, str)
            or category not in PROFESSIONAL_CATEGORIES
        ):
            raise MobileOnboardingError(
                "Área de atuação inválida."
            )

        label = PROFESSIONAL_CATEGORIES[category]

        if label not in selected:
            selected.append(label)

    return ", ".join(selected)


def create_professional_draft(
    *,
    user,
    display_name,
    primary_specialty,
    categories,
    city,
    state,
    bio="",
    phone="",
):
    """Cria no máximo um perfil profissional por usuário, sem publicá-lo."""
    _active_user(user)

    existing = db.session.scalar(
        select(ProfessionalProfile).where(
            ProfessionalProfile.user_id == user.id
        )
    )

    if existing is not None:
        return existing

    clean_name = _text(
        display_name,
        "Nome profissional",
        minimum=2,
        maximum=140,
        required=True,
    )

    clean_specialty = _text(
        primary_specialty,
        "Especialidade",
        minimum=2,
        maximum=120,
        required=True,
    )

    clean_city, clean_state = _location(city, state)
    clean_bio = _text(bio, "Apresentação", maximum=2000)
    clean_phone = _text(phone, "Telefone", maximum=32)
    specialties = _professional_categories(categories)

    profile = ProfessionalProfile(
        user_id=user.id,
        display_name=clean_name,
        slug=unique_public_handle(
            clean_name,
            resource_type="professional",
        ),
        primary_specialty=clean_specialty,
        specialties_text=specialties,
        bio=clean_bio or None,
        phone=clean_phone or None,
        whatsapp_enabled=bool(clean_phone),
        city=clean_city,
        state=clean_state,
        plan_tier="free",
        onboarding_completed=False,
        published_at=None,
        is_active=False,
        claimed_at=utcnow(),
    )

    db.session.add(profile)

    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()

        existing = db.session.scalar(
            select(ProfessionalProfile).where(
                ProfessionalProfile.user_id == user.id
            )
        )

        if existing is not None:
            return existing

        raise MobileOnboardingError(
            "Não foi possível criar o perfil. Tente novamente."
        ) from exc

    return profile


def create_establishment_draft(
    *,
    user,
    name,
    category,
    city,
    state,
    description="",
    phone="",
    neighborhood="",
):
    """Cria estabelecimento privado com o solicitante como proprietário."""
    _active_user(user)

    clean_name = _text(
        name,
        "Nome do estabelecimento",
        minimum=2,
        maximum=160,
        required=True,
    )

    clean_city, clean_state = _location(city, state)

    clean_category = _text(
        category,
        "Categoria",
        maximum=64,
        required=True,
    )

    if clean_category not in BUSINESS_CATEGORIES:
        raise MobileOnboardingError(
            "Categoria do estabelecimento inválida."
        )

    clean_description = _text(
        description,
        "Apresentação",
        maximum=2000,
    )

    clean_phone = _text(
        phone,
        "Telefone",
        maximum=32,
    )

    clean_neighborhood = _text(
        neighborhood,
        "Bairro",
        maximum=100,
    )

    existing = db.session.scalar(
        select(Establishment)
        .join(EstablishmentUserAccess)
        .where(
            EstablishmentUserAccess.user_id == user.id,
            EstablishmentUserAccess.role
            == EstablishmentAccessRole.OWNER,
            func.lower(Establishment.name)
            == clean_name.lower(),
            func.lower(Establishment.city)
            == clean_city.lower(),
            Establishment.state == clean_state,
        )
        .order_by(Establishment.id)
    )

    if existing is not None:
        return existing

    establishment = Establishment(
        name=clean_name,
        slug=unique_public_handle(
            clean_name,
            resource_type="establishment",
        ),
        description=clean_description or None,
        category=clean_category,
        visual_theme=(
            "barber"
            if clean_category == "barbearia"
            else "tattoo"
            if clean_category == "tatuagem"
            else "beauty"
        ),
        plan_tier="free",
        onboarding_completed=False,
        published_at=None,
        is_active=False,
        phone=clean_phone or None,
        whatsapp_enabled=bool(clean_phone),
        email=user.email,
        neighborhood=clean_neighborhood or None,
        city=clean_city,
        state=clean_state,
    )

    db.session.add(establishment)

    try:
        db.session.flush()

        db.session.add(
            EstablishmentUserAccess(
                user_id=user.id,
                establishment_id=establishment.id,
                role=EstablishmentAccessRole.OWNER,
                status=EstablishmentAccessStatus.ACTIVE,
            )
        )

        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()

        raise MobileOnboardingError(
            "Não foi possível criar o estabelecimento. Tente novamente."
        ) from exc

    return establishment