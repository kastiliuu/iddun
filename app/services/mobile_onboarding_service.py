"""Identidade profissional e rascunhos usados pelo aplicativo móvel.

O serviço reaproveita os mesmos modelos do web. O app pode criar e atualizar
um rascunho privado, retomá-lo depois e só publicar quando os requisitos
centrais do perfil estiverem completos.
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.platform import BUSINESS_CATEGORY_CHOICES
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.professional import ProfessionalProfile, utcnow
from app.models.professional_experience import (
    ProfessionalExperience,
    ProfessionalExperienceVerification,
)
from app.services.slug_service import unique_public_handle


class MobileOnboardingError(ValueError):
    """Dados inválidos ou operação de onboarding não permitida."""


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
            "Entre em uma conta ativa para continuar."
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
    """Cria ou atualiza o único perfil profissional da conta."""
    _active_user(user)

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

    profile = db.session.scalar(
        select(ProfessionalProfile).where(
            ProfessionalProfile.user_id == user.id
        )
    )
    is_new = profile is None

    if is_new:
        profile = ProfessionalProfile(
            user_id=user.id,
            display_name=clean_name,
            slug=unique_public_handle(
                clean_name,
                resource_type="professional",
            ),
            plan_tier="free",
            onboarding_completed=False,
            published_at=None,
            is_active=False,
            claimed_at=utcnow(),
        )
        db.session.add(profile)

    profile.display_name = clean_name
    profile.primary_specialty = clean_specialty
    profile.specialties_text = specialties
    profile.bio = clean_bio or None
    profile.phone = clean_phone or None
    profile.whatsapp_enabled = bool(clean_phone)
    profile.city = clean_city
    profile.state = clean_state

    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()

        existing = db.session.scalar(
            select(ProfessionalProfile).where(
                ProfessionalProfile.user_id == user.id
            )
        )

        if is_new and existing is not None:
            return existing

        raise MobileOnboardingError(
            "Não foi possível salvar o perfil. Tente novamente."
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
        existing.description = clean_description or None
        existing.phone = clean_phone or None
        existing.whatsapp_enabled = bool(clean_phone)
        existing.neighborhood = clean_neighborhood or None
        existing.category = clean_category
        db.session.commit()
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


def professional_completion(profile):
    steps = [
        {
            "key": "avatar",
            "label": "Adicionar foto de perfil",
            "complete": bool(profile.avatar_url),
        },
        {
            "key": "identity",
            "label": "Definir nome profissional",
            "complete": bool(profile.display_name),
        },
        {
            "key": "specialty",
            "label": "Informar especialidade",
            "complete": bool(profile.primary_specialty),
        },
        {
            "key": "bio",
            "label": "Escrever sua bio",
            "complete": bool(profile.bio),
        },
        {
            "key": "location",
            "label": "Informar cidade e UF",
            "complete": bool(profile.city and profile.state),
        },
        {
            "key": "portfolio",
            "label": "Adicionar pelo menos 3 trabalhos",
            "complete": len(profile.portfolio_items) >= 3,
        },
    ]

    recommended = []

    if not profile.professional_experiences:
        recommended.append(
            {
                "key": "experience",
                "label": "Adicionar experiência profissional",
            }
        )

    if not profile.active_memberships:
        recommended.append(
            {
                "key": "establishment",
                "label": "Conectar um estabelecimento",
            }
        )

    return {
        "percentage": profile.profile_completion,
        "readyToPublish": profile.ready_to_publish,
        "steps": steps,
        "recommendedActions": recommended,
    }


def add_professional_experience(
    *,
    profile,
    company_name,
    role_title,
    started_at,
    ended_at=None,
    is_current=False,
    description="",
    establishment_id=None,
):
    if profile is None or profile.id is None:
        raise MobileOnboardingError(
            "Crie seu perfil profissional antes de adicionar experiência."
        )

    if not isinstance(started_at, date):
        raise MobileOnboardingError(
            "Data inicial inválida."
        )

    if ended_at is not None and not isinstance(ended_at, date):
        raise MobileOnboardingError(
            "Data final inválida."
        )

    clean_company = _text(
        company_name,
        "Empresa",
        minimum=2,
        maximum=160,
        required=not bool(establishment_id),
    )
    clean_role = _text(
        role_title,
        "Cargo",
        minimum=2,
        maximum=140,
        required=True,
    )
    clean_description = _text(
        description,
        "Descrição",
        maximum=1200,
    )

    establishment = None
    verification_status = (
        ProfessionalExperienceVerification.UNVERIFIED
    )

    if establishment_id:
        establishment = db.session.get(
            Establishment,
            establishment_id,
        )

        if establishment is None:
            raise MobileOnboardingError(
                "Estabelecimento não encontrado."
            )

        membership = db.session.scalar(
            select(ProfessionalEstablishmentMembership).where(
                ProfessionalEstablishmentMembership.professional_id
                == profile.id,
                ProfessionalEstablishmentMembership.establishment_id
                == establishment.id,
                ProfessionalEstablishmentMembership.status
                == MembershipStatus.ACTIVE,
            )
        )

        if membership is None:
            raise MobileOnboardingError(
                "O vínculo com este estabelecimento precisa estar confirmado."
            )

        clean_company = establishment.name
        verification_status = (
            ProfessionalExperienceVerification.VERIFIED_MEMBERSHIP
        )

    experience = ProfessionalExperience(
        professional_id=profile.id,
        establishment_id=(
            establishment.id if establishment else None
        ),
        company_name=clean_company,
        role_title=clean_role,
        description=clean_description or None,
        started_at=started_at,
        ended_at=ended_at,
        is_current=bool(is_current),
        verification_status=verification_status,
    )

    try:
        experience.normalize_dates()
    except ValueError as exc:
        raise MobileOnboardingError(str(exc)) from exc

    db.session.add(experience)
    db.session.commit()

    return experience


def delete_professional_experience(*, profile, experience_id):
    experience = db.session.get(
        ProfessionalExperience,
        experience_id,
    )

    if (
        experience is None
        or profile is None
        or experience.professional_id != profile.id
    ):
        raise MobileOnboardingError(
            "Experiência profissional não encontrada."
        )

    db.session.delete(experience)
    db.session.commit()


def publish_professional_profile(profile):
    if profile is None:
        raise MobileOnboardingError(
            "Crie seu perfil profissional antes de publicar."
        )

    if not profile.ready_to_publish:
        raise MobileOnboardingError(
            "Complete os requisitos obrigatórios antes de publicar."
        )

    profile.onboarding_completed = True
    profile.is_active = True

    if profile.published_at is None:
        profile.published_at = utcnow()

    db.session.commit()

    return profile
