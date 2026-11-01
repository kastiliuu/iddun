"""Identidade profissional e rascunhos do onboarding (Expo e, a partir da
PR 2, Web).

O serviço reaproveita os mesmos modelos do web. Um rascunho é privado, pode
ser salvo por etapa e retomado depois; só vai ao ar por publicação explícita,
quando o servidor confirma os requisitos.

Contrato de salvamento parcial (PR 1 do onboarding, 01/11/2026):

- campo ausente no envio: o valor salvo é preservado;
- ``null`` ou texto vazio em campo opcional: limpeza explícita, validada;
- campo obrigatório (nome, tipo, cidade, UF) não pode ser limpo;
- num registro publicado, nenhuma edição pode remover um requisito de
  publicação que hoje está cumprido (resposta 409); legados incompletos
  continuam publicados e editáveis nos demais campos.
"""

from datetime import date
import re

from flask import current_app
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
from app.models.professional import ProfessionalProfile, ProfileTheme, utcnow
from app.models.professional_experience import (
    ProfessionalExperience,
    ProfessionalExperienceVerification,
)
from app.services.slug_service import unique_public_handle
from app.services.establishment_readiness_service import (
    DESCRIPTION_MIN_LENGTH, HOURS_MODES, OPERATION_MODES,
    evaluate_establishment_readiness,
    valid_business_hours,
)
from app.services.onboarding_steps import (
    BIO_MIN_LENGTH,
    BUSINESS_REQUIREMENT_LABELS,
    PROFESSIONAL_CATEGORIES,
    PROFESSIONAL_REQUIREMENT_LABELS,
    professional_missing_requirements,
)


class MobileOnboardingError(ValueError):
    """Dados inválidos ou operação de onboarding não permitida."""


class OnboardingNotFound(MobileOnboardingError):
    """Registro inexistente ou de outra conta (mesma resposta, sem enumerar)."""


class OnboardingConflict(MobileOnboardingError):
    """Operação válida no formato, mas incompatível com o estado atual."""

    def __init__(self, code, message, *, missing=()):
        super().__init__(message)
        self.code = code
        self.missing = tuple(missing)


# Ausência de um campo no envio: preservar o valor salvo.
UNSET = object()


PROFESSIONAL_ATTENDANCE_MODALITIES = {
    "establishment",
    "own_space",
    "client_location",
}


def _attendance_modalities(values):
    if values is None:
        return None
    if not isinstance(values, list) or len(values) > 3:
        raise MobileOnboardingError("Modalidades de atendimento inválidas.")
    if any(not isinstance(value, str) or value not in PROFESSIONAL_ATTENDANCE_MODALITIES for value in values):
        raise MobileOnboardingError("Modalidade de atendimento inválida.")
    return ",".join(sorted(set(values))) or None


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


def _optional_text(value, label, *, minimum=0, maximum):
    """Campo opcional: ``None`` ou vazio limpam; outro tipo é inválido."""
    if value is None:
        return None
    return _text(value, label, minimum=minimum, maximum=maximum) or None


def _state(value):
    clean = _text(value, "UF", minimum=2, maximum=2, required=True).upper()
    if len(clean) != 2 or not clean.isalpha():
        raise MobileOnboardingError("UF: informe duas letras.")
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
    bio=UNSET,
    phone=UNSET,
    attendance_modalities=None,
):
    """Cria ou atualiza o único perfil profissional da conta.

    Contrato completo usado pelo app desde a V0: nome, especialidade,
    áreas, cidade e UF são sempre enviados. Bio e telefone ausentes são
    preservados (antes eram apagados).
    """
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
    clean_bio = UNSET if bio is UNSET else _optional_text(bio, "Apresentação", maximum=2000)
    clean_phone = UNSET if phone is UNSET else _optional_text(phone, "Telefone", maximum=32)
    specialties = _professional_categories(categories)

    profile = db.session.scalar(
        select(ProfessionalProfile).where(
            ProfessionalProfile.user_id == user.id
        )
    )
    is_new = profile is None
    before = None if is_new else set(professional_missing_requirements(profile))

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
    if clean_bio is not UNSET:
        profile.bio = clean_bio
    if clean_phone is not UNSET:
        profile.phone = clean_phone
        profile.whatsapp_enabled = bool(clean_phone)
    profile.city = clean_city
    profile.state = clean_state
    if attendance_modalities is not None:
        profile.attendance_modalities = _attendance_modalities(attendance_modalities)

    if before is not None:
        _guard_professional_publication(profile, before)

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


def _guard_professional_publication(profile, before_missing):
    """Perfil no ar não pode perder um requisito que hoje cumpre."""
    if not profile.is_active:
        return
    removed = [key for key in professional_missing_requirements(profile)
               if key not in before_missing]
    if removed:
        db.session.rollback()
        raise OnboardingConflict(
            "publication_requirement_removed",
            "Seu perfil está publicado. Para manter a página no ar, "
            "estes dados não podem ficar vazios: "
            + " ".join(PROFESSIONAL_REQUIREMENT_LABELS[key] for key in removed),
            missing=removed,
        )


def update_professional_draft(*, user, changes, commit=True):
    """Salva uma etapa do perfil profissional (atualização parcial).

    Só as chaves presentes em ``changes`` mudam. Sem perfil, cria um
    rascunho privado a partir do nome profissional (única coluna exigida
    pelo banco); as demais etapas completam depois.
    """
    _active_user(user)
    allowed = {
        "display_name", "headline", "primary_specialty", "categories", "city",
        "state", "bio", "phone", "whatsapp_enabled", "instagram",
        "attendance_modalities", "visual_theme",
    }
    unknown = set(changes) - allowed
    if unknown:
        raise MobileOnboardingError("Campo não permitido nesta etapa.")

    values = {}
    if "display_name" in changes:
        values["display_name"] = _text(
            changes["display_name"], "Nome profissional",
            minimum=2, maximum=140, required=True,
        )
    if "headline" in changes:
        values["headline"] = _optional_text(changes["headline"], "Chamada", maximum=180)
    if "primary_specialty" in changes:
        values["primary_specialty"] = _optional_text(
            changes["primary_specialty"], "Especialidade", minimum=2, maximum=120,
        )
    if "categories" in changes:
        categories = changes["categories"]
        values["specialties_text"] = (
            None if categories in (None, []) else _professional_categories(categories)
        )
    if "city" in changes:
        values["city"] = _optional_text(changes["city"], "Cidade", minimum=2, maximum=100)
    if "state" in changes:
        values["state"] = None if changes["state"] in (None, "") else _state(changes["state"])
    if "bio" in changes:
        values["bio"] = _optional_text(
            changes["bio"], "Apresentação", minimum=BIO_MIN_LENGTH, maximum=2000,
        )
    if "phone" in changes:
        values["phone"] = _optional_text(changes["phone"], "Telefone", maximum=32)
    if "instagram" in changes:
        values["instagram"] = _optional_text(changes["instagram"], "Instagram", maximum=120)
    if "whatsapp_enabled" in changes:
        if not isinstance(changes["whatsapp_enabled"], bool):
            raise MobileOnboardingError("WhatsApp: informe sim ou não.")
        values["whatsapp_enabled"] = changes["whatsapp_enabled"]
    if "visual_theme" in changes:
        # D-ONB-03: opcional; vazio volta ao padrão Beleza.
        theme = changes["visual_theme"]
        if theme in (None, ""):
            theme = ProfileTheme.BEAUTY
        if theme not in {value for value, _ in ProfileTheme.CHOICES}:
            raise MobileOnboardingError("Universo visual inválido.")
        values["visual_theme"] = theme
    if "attendance_modalities" in changes:
        modalities = changes["attendance_modalities"]
        values["attendance_modalities"] = (
            None if modalities in (None, []) else _attendance_modalities(modalities)
        )

    profile = db.session.scalar(
        select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id)
    )
    if profile is None:
        if "display_name" not in values:
            raise MobileOnboardingError(
                "Nome profissional: preenchimento obrigatório."
            )
        profile = ProfessionalProfile(
            user_id=user.id,
            display_name=values["display_name"],
            slug=unique_public_handle(values["display_name"], resource_type="professional"),
            plan_tier="free",
            onboarding_completed=False,
            published_at=None,
            is_active=False,
            claimed_at=utcnow(),
        )
        db.session.add(profile)
        before = None
    else:
        before = set(professional_missing_requirements(profile))

    for field, value in values.items():
        setattr(profile, field, value)
    if "phone" in values and not values["phone"]:
        profile.whatsapp_enabled = False

    if before is not None:
        _guard_professional_publication(profile, before)

    if not commit:
        # Etapa com arquivos: quem chama confirma banco e uploads juntos.
        db.session.flush()
        return profile

    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        existing = db.session.scalar(
            select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id)
        )
        if before is None and existing is not None:
            # Duas abas criando ao mesmo tempo: aplica a etapa no perfil vencedor.
            return update_professional_draft(user=user, changes=changes)
        raise MobileOnboardingError(
            "Não foi possível salvar o perfil. Tente novamente."
        ) from exc
    return profile


# The absence of an optional field on retry must not erase a previously
# recorded business setting (particularly for historically published firms).
_BUSINESS_UNSET = UNSET


def _optional_business_choice(value, allowed, label):
    if value is None or value == "":
        return None
    if not isinstance(value, str) or value not in allowed:
        raise MobileOnboardingError(f"{label}: opção inválida.")
    return value


def _optional_business_hours(value):
    if value is None:
        return None
    if not isinstance(value, dict) or len(value) > 7:
        raise MobileOnboardingError("Horários de funcionamento inválidos.")
    if any(not isinstance(periods, list) or len(periods) > 4 for periods in value.values()):
        raise MobileOnboardingError("Informe no máximo quatro períodos por dia.")
    if not valid_business_hours(value):
        raise MobileOnboardingError("Horários de funcionamento inválidos.")
    return value


def _business_optional_values(*, operation_mode, business_hours_mode,
                              business_hours, address_line1, commercial_email):
    values = {}
    if operation_mode is not _BUSINESS_UNSET:
        values["operation_mode"] = _optional_business_choice(
            operation_mode, OPERATION_MODES, "Modalidade de atendimento"
        )
    if business_hours_mode is not _BUSINESS_UNSET:
        values["business_hours_mode"] = _optional_business_choice(
            business_hours_mode, HOURS_MODES, "Tipo de funcionamento"
        )
    if business_hours is not _BUSINESS_UNSET:
        values["business_hours"] = _optional_business_hours(business_hours)
    if address_line1 is not _BUSINESS_UNSET:
        if address_line1 is None:
            values["address_line1"] = None
        else:
            values["address_line1"] = _text(
                address_line1, "Endereço comercial", maximum=180
            ) or None
    if commercial_email is not _BUSINESS_UNSET:
        if commercial_email is None or commercial_email == "":
            values["email"] = None
        else:
            email = _text(commercial_email, "E-mail comercial", maximum=255).lower()
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
                raise MobileOnboardingError("E-mail comercial inválido.")
            values["email"] = email
    return values


_BUSINESS_FIELDS = {
    "name", "category", "city", "state", "description", "phone",
    "neighborhood", "address_line1", "address_line2", "postal_code",
    "commercial_email", "operation_mode", "business_hours_mode",
    "business_hours", "whatsapp_enabled",
}


def _business_values(changes, *, legacy=False):
    """Valida só as chaves presentes. Ausência preserva; vazio limpa.

    ``legacy``: contrato do POST antigo do app, que grava rascunho com
    apresentação curta (a regra de 40 caracteres vale para publicar).
    """
    unknown = set(changes) - _BUSINESS_FIELDS
    if unknown:
        raise MobileOnboardingError("Campo não permitido nesta etapa.")

    values = {}
    if "name" in changes:
        values["name"] = _text(
            changes["name"], "Nome do estabelecimento",
            minimum=2, maximum=160, required=True,
        )
    if "category" in changes:
        category = _text(changes["category"], "Categoria", maximum=64, required=True)
        if category not in BUSINESS_CATEGORIES:
            raise MobileOnboardingError("Categoria do estabelecimento inválida.")
        values["category"] = category
    if "city" in changes:
        values["city"] = _text(
            changes["city"], "Cidade", minimum=2, maximum=100, required=True,
        )
    if "state" in changes:
        values["state"] = _state(changes["state"])
    if "description" in changes:
        values["description"] = _optional_text(
            changes["description"], "Apresentação",
            minimum=0 if legacy else DESCRIPTION_MIN_LENGTH, maximum=2000,
        )
    for key, label, maximum in (
        ("phone", "Telefone", 32),
        ("neighborhood", "Bairro", 100),
        ("address_line2", "Complemento", 120),
        ("postal_code", "CEP", 16),
    ):
        if key in changes:
            values[key] = _optional_text(changes[key], label, maximum=maximum)
    if "phone" in values:
        values["whatsapp_enabled"] = bool(values["phone"])
    if "whatsapp_enabled" in changes:
        if not isinstance(changes["whatsapp_enabled"], bool):
            raise MobileOnboardingError("WhatsApp: informe sim ou não.")
        # Sem telefone salvo ou enviado, o botão do WhatsApp fica desligado.
        has_phone = values.get("phone", UNSET)
        values["whatsapp_enabled"] = changes["whatsapp_enabled"] and bool(
            has_phone if has_phone is not UNSET else True
        )
    values.update(_business_optional_values(
        operation_mode=changes.get("operation_mode", UNSET),
        business_hours_mode=changes.get("business_hours_mode", UNSET),
        business_hours=changes.get("business_hours", UNSET),
        address_line1=changes.get("address_line1", UNSET),
        commercial_email=changes.get("commercial_email", UNSET),
    ))
    return values


def _owned_establishment_query(user):
    return (
        select(Establishment)
        .join(EstablishmentUserAccess)
        .where(
            EstablishmentUserAccess.user_id == user.id,
            EstablishmentUserAccess.role == EstablishmentAccessRole.OWNER,
            EstablishmentUserAccess.status == EstablishmentAccessStatus.ACTIVE,
        )
    )


def owned_establishments(user):
    """Estabelecimentos em que a conta é proprietária ativa (retomada)."""
    _active_user(user)
    return db.session.scalars(
        _owned_establishment_query(user).order_by(Establishment.id)
    ).all()


def owned_establishment(user, establishment_id, *, lock=False):
    """Busca por id estável com autorização de proprietário ativo.

    Inexistente e de outra conta têm a mesma resposta, para não revelar ids.
    """
    _active_user(user)
    if (
        isinstance(establishment_id, bool)
        or not isinstance(establishment_id, int)
        or not 0 < establishment_id <= 2_147_483_647  # limite de INTEGER
    ):
        raise OnboardingNotFound("Estabelecimento não encontrado.")
    query = _owned_establishment_query(user).where(Establishment.id == establishment_id)
    if lock:
        query = query.with_for_update(of=Establishment).execution_options(
            populate_existing=True,
        )
    establishment = db.session.scalar(query)
    if establishment is None:
        raise OnboardingNotFound("Estabelecimento não encontrado.")
    return establishment


def _guard_business_publication(establishment, before_missing):
    if not establishment.is_active:
        return
    after = evaluate_establishment_readiness(establishment).missing_requirements
    removed = [key for key in after if key not in before_missing]
    if removed:
        db.session.rollback()
        raise OnboardingConflict(
            "publication_requirement_removed",
            "Este estabelecimento está publicado. Para manter a página no ar, "
            "estes dados não podem ficar vazios: "
            + " ".join(BUSINESS_REQUIREMENT_LABELS[key] for key in removed),
            missing=removed,
        )


def _apply_business_values(establishment, values):
    before = set(evaluate_establishment_readiness(establishment).missing_requirements)
    for field, value in values.items():
        setattr(establishment, field, value)
    _guard_business_publication(establishment, before)
    db.session.commit()
    return establishment


def update_establishment_draft(*, user, establishment_id, changes, legacy=False):
    """Salva uma etapa de um estabelecimento do dono, pelo id estável.

    Não altera ``is_active``, ``published_at`` nem ``onboarding_completed``.
    O slug público não muda ao renomear.
    """
    establishment = owned_establishment(user, establishment_id)
    values = _business_values(changes, legacy=legacy)
    return _apply_business_values(establishment, values)


def create_establishment_draft(
    *,
    user,
    name,
    category,
    city,
    state,
    description=UNSET,
    phone=UNSET,
    neighborhood=UNSET,
    operation_mode=UNSET,
    business_hours_mode=UNSET,
    business_hours=UNSET,
    address_line1=UNSET,
    address_line2=UNSET,
    postal_code=UNSET,
    commercial_email=UNSET,
    whatsapp_enabled=UNSET,
    establishment_id=None,
):
    """Cria rascunho (nome, tipo, cidade e UF válidos) ou atualiza o do dono.

    Com ``establishment_id``: atualiza aquele estabelecimento, se a conta for
    proprietária ativa. Sem id (clientes antigos): só reaproveita um rascunho
    nunca publicado do próprio dono com o mesmo nome, cidade e UF; nunca
    altera estabelecimento publicado por essa compatibilidade.
    """
    _active_user(user)

    changes = {
        "name": name,
        "category": category,
        "city": city,
        "state": state,
    }
    for key, value in (
        ("description", description),
        ("phone", phone),
        ("neighborhood", neighborhood),
        ("operation_mode", operation_mode),
        ("business_hours_mode", business_hours_mode),
        ("business_hours", business_hours),
        ("address_line1", address_line1),
        ("address_line2", address_line2),
        ("postal_code", postal_code),
        ("commercial_email", commercial_email),
        ("whatsapp_enabled", whatsapp_enabled),
    ):
        if value is not UNSET:
            changes[key] = value

    if establishment_id is not None:
        return update_establishment_draft(
            user=user, establishment_id=establishment_id, changes=changes,
            legacy=True,
        )

    values = _business_values(changes, legacy=True)

    same_name = (
        _owned_establishment_query(user)
        .where(
            func.lower(Establishment.name) == values["name"].lower(),
            func.lower(Establishment.city) == values["city"].lower(),
            Establishment.state == values["state"],
        )
        .order_by(Establishment.id)
    )
    matches = db.session.scalars(same_name).all()
    draft = next(
        (item for item in matches
         if not item.is_active and item.published_at is None),
        None,
    )
    if draft is not None:
        return _apply_business_values(draft, values)
    if matches:
        raise OnboardingConflict(
            "establishment_exists",
            "Você já tem um estabelecimento com este nome nesta cidade. "
            "Edite-o pelo painel da empresa.",
        )

    establishment = Establishment(
        name=values["name"],
        slug=unique_public_handle(
            values["name"],
            resource_type="establishment",
        ),
        category=values["category"],
        visual_theme=(
            "barber"
            if values["category"] == "barbearia"
            else "tattoo"
            if values["category"] == "tatuagem"
            else "beauty"
        ),
        plan_tier="free",
        onboarding_completed=False,
        published_at=None,
        is_active=False,
        whatsapp_enabled=False,
        # D-ONB-05: o e-mail da conta só vira e-mail comercial (público)
        # quando a pessoa confirma na etapa de contato.
        email=None,
        city=values["city"],
        state=values["state"],
    )
    for field, value in values.items():
        setattr(establishment, field, value)

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


def publish_establishment(*, user, establishment_id):
    """Publicação explícita, transacional e idempotente (DEC-ID-100/108).

    Retorna ``(estabelecimento, ja_publicado)``. Um segundo clique não muda
    nada. Página desativada pela moderação (``published_at`` preenchido e
    ``is_active`` falso) não é reativada pelo dono. Publicar não torna nada
    reservável: isso depende de serviço, executor e horário reais.
    """
    establishment = owned_establishment(user, establishment_id, lock=True)

    if establishment.is_active:
        db.session.rollback()
        return establishment, True
    if establishment.published_at is not None:
        db.session.rollback()
        raise OnboardingConflict(
            "publication_locked",
            "Esta página foi desativada e não pode ser publicada por aqui. "
            "Fale com o suporte do IDDUN.",
        )

    readiness = evaluate_establishment_readiness(establishment)
    if not readiness.ready_to_publish:
        db.session.rollback()
        raise OnboardingConflict(
            "establishment_incomplete",
            "Complete os requisitos obrigatórios antes de publicar.",
            missing=readiness.missing_requirements,
        )

    establishment.is_active = True
    establishment.onboarding_completed = True
    establishment.published_at = utcnow()
    db.session.commit()
    current_app.logger.info(
        "onboarding.establishment_published id=%s user=%s",
        establishment.id, user.id,
    )
    return establishment, False


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
        # Mesma regra da publicação (onboarding_steps), inclusive os 40
        # caracteres da apresentação (D-ONB-02); quem já está no ar segue apto.
        "readyToPublish": bool(profile.is_active)
        or not professional_missing_requirements(profile),
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

    # Publicação explícita, transacional e idempotente: a linha fica travada
    # até o commit (PostgreSQL) e um segundo clique não altera nada.
    profile = db.session.scalar(
        select(ProfessionalProfile)
        .where(ProfessionalProfile.id == profile.id)
        .with_for_update()
        # Relê a linha travada mesmo que o objeto já esteja na sessão.
        .execution_options(populate_existing=True)
    )

    if profile.is_active:
        db.session.rollback()
        return profile

    if profile.published_at is not None:
        # Desativado pela moderação: o dono não reativa por aqui.
        db.session.rollback()
        raise OnboardingConflict(
            "publication_locked",
            "Este perfil foi desativado e não pode ser publicado por aqui. "
            "Fale com o suporte do IDDUN.",
        )

    missing = professional_missing_requirements(profile)
    if missing:
        db.session.rollback()
        raise OnboardingConflict(
            "profile_incomplete",
            "Complete os requisitos obrigatórios antes de publicar.",
            missing=missing,
        )

    profile.onboarding_completed = True
    profile.is_active = True
    profile.published_at = utcnow()

    db.session.commit()
    current_app.logger.info(
        "onboarding.professional_published id=%s user=%s",
        profile.id, profile.user_id,
    )

    return profile
