from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request
from sqlalchemy import select

from app.extensions import db
from app.models.experience import Experience, ExperienceCategory, ExperienceStatus
from app.models.booking import ExperienceSlot
from app.models.establishment import ProfessionalEstablishmentMembership, MembershipStatus
from app.services.slug_service import unique_slug
from app.services.admin_catalog_service import publish_experience
from app.services.availability_service import AvailabilityError, create_availability, create_availability_from_working_hours
from app.services.time_service import utcnow, to_local
from app.models.booking import SlotStatus
from app.services.booking_service import block_slot_manual, reopen_manual_slot, BookingStateError

from app.extensions import csrf, limiter
from app.services.api_auth import get_user_by_access_token
from app.services.api_contract import api_error, api_json
from app.services.media_storage import resolve_image_url
from app.services.mobile_onboarding_service import (
    MobileOnboardingError,
    PROFESSIONAL_CATEGORIES,
    add_professional_experience,
    create_establishment_draft,
    create_professional_draft,
    delete_professional_experience,
    professional_completion,
    publish_professional_profile,
)


api_onboarding_bp = Blueprint(
    "api_onboarding",
    __name__,
    url_prefix="/api/v1/onboarding",
)

MAX_ONBOARDING_BODY_BYTES = 32_768


def _bearer_user():
    authorization = request.headers.get(
        "Authorization",
        "",
    )
    parts = authorization.split()

    if (
        len(parts) != 2
        or parts[0].lower() != "bearer"
    ):
        return None

    return get_user_by_access_token(
        parts[1]
    )


def _authenticated_user():
    user = _bearer_user()

    if user is None:
        return None, api_error(
            "authentication_required",
            "Entre na sua conta para continuar.",
            401,
        )

    return user, None


def _json_body():
    if (
        request.content_length is not None
        and request.content_length
        > MAX_ONBOARDING_BODY_BYTES
    ):
        return None, api_error(
            "request_too_large",
            "A solicitação é muito grande.",
            413,
        )

    if not request.is_json:
        return None, api_error(
            "json_required",
            "Envie os dados em formato JSON.",
            415,
        )

    payload = request.get_json(
        silent=True
    )

    if not isinstance(payload, dict):
        return None, api_error(
            "invalid_json",
            "Não foi possível ler os dados enviados.",
            400,
        )

    return payload, None


def _iso_date(value, label, *, required=False):
    if value in (None, ""):
        if required:
            raise MobileOnboardingError(
                f"{label}: preenchimento obrigatório."
            )

        return None

    if not isinstance(value, str):
        raise MobileOnboardingError(
            f"{label}: use o formato AAAA-MM-DD."
        )

    try:
        return date.fromisoformat(
            value.strip()
        )
    except ValueError as exc:
        raise MobileOnboardingError(
            f"{label}: use o formato AAAA-MM-DD."
        ) from exc


def _category_ids(profile):
    selected_labels = {
        item.strip().lower()
        for item in (
            profile.specialties_text
            or ""
        ).split(",")
        if item.strip()
    }

    return [
        key
        for key, label
        in PROFESSIONAL_CATEGORIES.items()
        if label.lower() in selected_labels
    ]


def _experience_payload(item):
    return {
        "id": item.id,
        "companyName": item.company_name,
        "roleTitle": item.role_title,
        "description": item.description,
        "startedAt": (
            item.started_at.isoformat()
            if item.started_at
            else None
        ),
        "endedAt": (
            item.ended_at.isoformat()
            if item.ended_at
            else None
        ),
        "isCurrent": item.is_current,
        "verified": item.verified,
        "verificationStatus": (
            item.verification_status
        ),
        "establishment": (
            {
                "id": item.establishment.id,
                "slug": item.establishment.slug,
                "name": item.establishment.name,
            }
            if item.establishment is not None
            else None
        ),
    }


def _membership_payload(item):
    return {
        "id": item.id,
        "status": item.status,
        "isPrimary": item.is_primary,
        "roleName": item.role_name,
        "establishment": {
            "id": item.establishment.id,
            "slug": item.establishment.slug,
            "name": item.establishment.name,
        },
    }


def _professional_payload(profile):
    return {
        "id": str(profile.id),
        "slug": profile.slug,
        "displayName": profile.display_name,
        "primarySpecialty": (
            profile.primary_specialty
        ),
        "categories": _category_ids(
            profile
        ),
        "bio": profile.bio or "",
        "phone": profile.phone or "",
        "city": profile.city or "",
        "state": profile.state or "",
        "attendanceModalities": (profile.attendance_modalities or "").split(",") if profile.attendance_modalities else [],
        "avatarUrl": (
            resolve_image_url(
                profile.avatar_url,
                external=True,
            )
            if profile.avatar_url
            else None
        ),
        "coverUrl": (
            resolve_image_url(
                profile.cover_url,
                external=True,
            )
            if profile.cover_url
            else None
        ),
        "avatarFocusX": profile.avatar_focus_x,
        "avatarFocusY": profile.avatar_focus_y,
        "coverFocusX": profile.cover_focus_x,
        "coverFocusY": profile.cover_focus_y,
        "portfolioCount": len(
            profile.portfolio_items
        ),
        "portfolio": [
            {
                "id": item.id,
                "imageUrl": resolve_image_url(
                    item.image_url,
                    external=True,
                ),
                "caption": item.caption,
                "sortOrder": item.sort_order,
            }
            for item in profile.portfolio_items
        ],
        "isActive": profile.is_active,
        "onboardingCompleted": (
            profile.onboarding_completed
        ),
        "publishedAt": (
            profile.published_at.isoformat()
            if profile.published_at
            else None
        ),
        "completion": professional_completion(
            profile
        ),
        "experiences": [
            _experience_payload(item)
            for item
            in profile.professional_experiences
        ],
        "memberships": [
            _membership_payload(item)
            for item in profile.memberships
        ],
    }


def _establishment_payload(item):
    return {
        "id": str(item.id),
        "slug": item.slug,
        "name": item.name,
        "category": item.category,
        "description": (
            item.description or ""
        ),
        "phone": item.phone or "",
        "neighborhood": (
            item.neighborhood or ""
        ),
        "city": item.city or "",
        "state": item.state or "",
        "isActive": item.is_active,
        "onboardingCompleted": (
            item.onboarding_completed
        ),
        "profileCompletion": (
            item.profile_completion
        ),
    }


@api_onboarding_bp.get(
    "/professional"
)
def get_professional_onboarding():
    user, error = (
        _authenticated_user()
    )

    if error is not None:
        return error

    profile = user.professional_profile

    return api_json(
        {
            "profile": (
                _professional_payload(
                    profile
                )
                if profile is not None
                else None
            )
        },
        cache_control="no-store",
    )


@api_onboarding_bp.post(
    "/professional"
)
@csrf.exempt
@limiter.limit("30 per hour")
def save_professional_onboarding():
    user, error = (
        _authenticated_user()
    )

    if error is not None:
        return error

    payload, error = _json_body()

    if error is not None:
        return error

    try:
        profile = (
            create_professional_draft(
                user=user,
                display_name=payload.get(
                    "displayName",
                    "",
                ),
                primary_specialty=(
                    payload.get(
                        "primarySpecialty",
                        "",
                    )
                ),
                categories=payload.get(
                    "categories"
                ),
                city=payload.get(
                    "city",
                    "",
                ),
                state=payload.get(
                    "state",
                    "",
                ),
                bio=payload.get(
                    "bio",
                    "",
                ),
                phone=payload.get(
                    "phone",
                    "",
                ),
                attendance_modalities=payload.get("attendanceModalities"),
            )
        )
    except MobileOnboardingError as exc:
        return api_error(
            "invalid_onboarding_data",
            str(exc),
            400,
        )

    return api_json(
        {
            "profile": (
                _professional_payload(
                    profile
                )
            )
        },
        201
        if profile.created_at
        == profile.updated_at
        else 200,
        cache_control="no-store",
    )


@api_onboarding_bp.post(
    "/establishment"
)
@csrf.exempt
@limiter.limit("20 per hour")
def save_establishment_onboarding():
    user, error = (
        _authenticated_user()
    )

    if error is not None:
        return error

    payload, error = _json_body()

    if error is not None:
        return error

    try:
        establishment = (
            create_establishment_draft(
                user=user,
                name=payload.get(
                    "name",
                    "",
                ),
                category=payload.get(
                    "category",
                    "",
                ),
                city=payload.get(
                    "city",
                    "",
                ),
                state=payload.get(
                    "state",
                    "",
                ),
                description=payload.get(
                    "description",
                    "",
                ),
                phone=payload.get(
                    "phone",
                    "",
                ),
                neighborhood=payload.get(
                    "neighborhood",
                    "",
                ),
            )
        )
    except MobileOnboardingError as exc:
        return api_error(
            "invalid_onboarding_data",
            str(exc),
            400,
        )

    return api_json(
        {
            "establishment": (
                _establishment_payload(
                    establishment
                )
            )
        },
        201,
        cache_control="no-store",
    )


@api_onboarding_bp.post(
    "/professional/experiences"
)
@csrf.exempt
@limiter.limit("40 per hour")
def create_professional_experience():
    user, error = (
        _authenticated_user()
    )

    if error is not None:
        return error

    profile = user.professional_profile

    if profile is None:
        return api_error(
            "professional_profile_required",
            "Crie seu perfil profissional antes de adicionar experiência.",
            409,
        )

    payload, error = _json_body()

    if error is not None:
        return error

    try:
        establishment_id = (
            payload.get(
                "establishmentId"
            )
        )

        if establishment_id not in (
            None,
            "",
        ):
            establishment_id = int(
                establishment_id
            )

        experience = (
            add_professional_experience(
                profile=profile,
                company_name=(
                    payload.get(
                        "companyName",
                        "",
                    )
                ),
                role_title=payload.get(
                    "roleTitle",
                    "",
                ),
                description=payload.get(
                    "description",
                    "",
                ),
                started_at=_iso_date(
                    payload.get(
                        "startedAt"
                    ),
                    "Início",
                    required=True,
                ),
                ended_at=_iso_date(
                    payload.get(
                        "endedAt"
                    ),
                    "Fim",
                ),
                is_current=bool(
                    payload.get(
                        "isCurrent",
                        False,
                    )
                ),
                establishment_id=(
                    establishment_id
                ),
            )
        )
    except (
        MobileOnboardingError,
        TypeError,
        ValueError,
    ) as exc:
        return api_error(
            "invalid_professional_experience",
            str(exc),
            400,
        )

    return api_json(
        {
            "experience": (
                _experience_payload(
                    experience
                )
            ),
            "completion": (
                professional_completion(
                    profile
                )
            ),
        },
        201,
        cache_control="no-store",
    )


@api_onboarding_bp.delete(
    "/professional/experiences/"
    "<int:experience_id>"
)
@csrf.exempt
@limiter.limit("40 per hour")
def remove_professional_experience(
    experience_id,
):
    user, error = (
        _authenticated_user()
    )

    if error is not None:
        return error

    try:
        delete_professional_experience(
            profile=(
                user.professional_profile
            ),
            experience_id=experience_id,
        )
    except MobileOnboardingError as exc:
        return api_error(
            "professional_experience_not_found",
            str(exc),
            404,
        )

    return "", 204


@api_onboarding_bp.post(
    "/professional/publish"
)
@csrf.exempt
@limiter.limit("10 per hour")
def publish_professional():
    user, error = (
        _authenticated_user()
    )

    if error is not None:
        return error

    profile = user.professional_profile

    if profile is None:
        return api_error(
            "professional_profile_required",
            "Crie seu perfil profissional antes de publicar.",
            409,
        )

    try:
        publish_professional_profile(
            profile
        )
    except MobileOnboardingError as exc:
        return api_error(
            "profile_incomplete",
            str(exc),
            409,
            details={
                "completion": (
                    professional_completion(
                        profile
                    )
                )
            },
        )

    return api_json(
        {
            "profile": (
                _professional_payload(
                    profile
                )
            )
        },
        cache_control="no-store",
    )


@api_onboarding_bp.get("/professional/services")
def list_professional_services():
    """Private catalog, including drafts and paused services.

    Never return services belonging to other professionals.
    """
    user, error = _authenticated_user()
    if error is not None:
        return error

    profile = user.professional_profile
    if profile is None:
        return api_error(
            "professional_profile_required",
            "Crie seu perfil profissional para gerenciar serviços.",
            409,
        )

    items = db.session.scalars(
        select(Experience)
        .where(Experience.professional_id == profile.id)
        .order_by(Experience.created_at.desc(), Experience.id.desc())
    ).all()

    return api_json(
        {"items": [
            {
                "id": item.id,
                "title": item.title,
                "category": item.category,
                "status": item.status,
                "price": float(item.price),
                "durationMinutes": item.duration_minutes,
                "establishmentId": item.establishment_id,
            }
            for item in items
        ]},
        cache_control="private, no-store",
    )


@api_onboarding_bp.post("/professional/services")
@limiter.limit("20 per hour")
def create_professional_service_draft():
    user, error = _authenticated_user()
    if error is not None:
        return error

    profile = user.professional_profile
    if profile is None:
        return api_error(
            "professional_profile_required",
            "Crie seu perfil profissional antes de cadastrar serviços.",
            409,
        )

    payload, error = _json_body()
    if error is not None:
        return error

    title = payload.get("name")
    category = payload.get("category")
    description = payload.get("description")
    short_description = payload.get("shortDescription") or description
    duration = payload.get("durationMinutes")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 160:
        return api_error("invalid_title", "Informe um nome de serviço válido (até 160 caracteres).", 400)
    if category not in ExperienceCategory.LABELS:
        return api_error("invalid_category", "Selecione uma categoria válida.", 400)
    if not isinstance(short_description, str) or not 1 <= len(short_description.strip()) <= 220:
        return api_error("invalid_description", "Informe uma descrição resumida (até 220 caracteres).", 400)
    if description is not None and (not isinstance(description, str) or len(description) > 4000):
        return api_error("invalid_description", "A descrição completa deve ter até 4000 caracteres.", 400)
    if isinstance(duration, bool) or not isinstance(duration, int) or not 10 <= duration <= 720:
        return api_error("invalid_duration", "A duração deve estar entre 10 e 720 minutos.", 400)

    def parse_money(value):
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            return None
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
        if not number.is_finite() or number < 0 or number > Decimal("99999999.99"):
            return None
        if number != number.quantize(Decimal("0.01")):
            return None
        return number

    price = parse_money(payload.get("price"))
    regular = parse_money(payload.get("regularPrice", payload.get("price")))
    if price is None or regular is None or price > regular:
        return api_error("invalid_price", "Informe preços válidos; o preço regular não pode ser menor que o preço atual.", 400)

    establishment_id = payload.get("establishmentId")
    if establishment_id is not None:
        if isinstance(establishment_id, bool) or not isinstance(establishment_id, int) or establishment_id <= 0:
            return api_error("invalid_establishment", "Estabelecimento inválido.", 400)
        if establishment_id not in _owned_active_establishments(profile):
            return api_error("establishment_not_allowed", "Vínculo ativo com o estabelecimento necessário.", 403)

    # Service starts as draft with no slots or automatic availability.
    item = Experience(
        professional_id=profile.id,
        establishment_id=establishment_id,
        title=title.strip(),
        slug=unique_slug(Experience, title.strip()),
        category=category,
        short_description=short_description.strip(),
        description=description.strip() or None if isinstance(description, str) else None,
        regular_price=regular,
        price=price,
        duration_minutes=duration,
        status=ExperienceStatus.DRAFT,
    )
    try:
        db.session.add(item)
        db.session.commit()
    except Exception:
        db.session.rollback()
        from flask import current_app
        current_app.logger.exception("Erro ao salvar rascunho de serviço")
        return api_error("service_save_failed", "Não foi possível salvar o rascunho.", 500)

    return api_json({
        "service": {
            "id": item.id,
            "title": item.title,
            "status": item.status,
            "category": item.category,
            "price": float(item.price),
            "durationMinutes": item.duration_minutes,
        }
    }, status=201, cache_control="private, no-store")


@api_onboarding_bp.get("/professional/services/<int:service_id>")
def get_professional_service_draft(service_id):
    user, error = _authenticated_user()
    if error is not None:
        return error
    profile = user.professional_profile
    if profile is None:
        return api_error("professional_profile_required", "Perfil profissional necessário.", 409)
    item = db.session.scalar(select(Experience).where(
        Experience.id == service_id,
        Experience.professional_id == profile.id,
    ))
    if item is None:
        return api_error("service_not_found", "Serviço não encontrado.", 404)
    return api_json({"service": {
        "id": item.id,
        "name": item.title,
        "category": item.category,
        "shortDescription": item.short_description,
        "description": item.description or "",
        "regularPrice": float(item.regular_price),
        "price": float(item.price),
        "durationMinutes": item.duration_minutes,
        "status": item.status,
        "establishmentId": item.establishment_id,
    }}, cache_control="private, no-store")


@api_onboarding_bp.patch("/professional/services/<int:service_id>")
@limiter.limit("30 per hour")
def update_professional_service_draft(service_id):
    user, error = _authenticated_user()
    if error is not None:
        return error
    profile = user.professional_profile
    if profile is None:
        return api_error("professional_profile_required", "Perfil profissional necessário.", 409)
    item = db.session.scalar(select(Experience).where(
        Experience.id == service_id,
        Experience.professional_id == profile.id,
    ))
    if item is None:
        return api_error("service_not_found", "Serviço não encontrado.", 404)
    if item.status not in (ExperienceStatus.DRAFT, ExperienceStatus.PAUSED):
        return api_error("service_not_editable", "Somente rascunhos e serviços pausados podem ser editados.", 409)
    payload, error = _json_body()
    if error is not None:
        return error
    allowed = {"name", "category", "shortDescription", "description",
               "regularPrice", "price", "durationMinutes", "establishmentId"}
    if not payload or set(payload) - allowed:
        return api_error("invalid_fields", "Envie apenas campos editáveis do serviço.", 400)

    title = payload.get("name", item.title)
    category = payload.get("category", item.category)
    short = payload.get("shortDescription", item.short_description)
    description = payload.get("description", item.description or "")
    duration = payload.get("durationMinutes", item.duration_minutes)
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 160:
        return api_error("invalid_title", "Nome inválido.", 400)
    if not isinstance(category, str) or category not in ExperienceCategory.LABELS:
        return api_error("invalid_category", "Categoria inválida.", 400)
    if not isinstance(short, str) or not 1 <= len(short.strip()) <= 220:
        return api_error("invalid_description", "Descrição resumida inválida.", 400)
    if not isinstance(description, str) or len(description) > 4000:
        return api_error("invalid_description", "Descrição completa inválida.", 400)
    if isinstance(duration, bool) or not isinstance(duration, int) or not 10 <= duration <= 720:
        return api_error("invalid_duration", "Duração inválida.", 400)

    def money(value):
        if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
            return None
        try:
            amount = Decimal(str(value))
            if (not amount.is_finite() or amount < 0 or amount > Decimal("99999999.99")
                    or amount != amount.quantize(Decimal("0.01"))):
                return None
            return amount
        except (InvalidOperation, ValueError):
            return None

    regular = money(payload.get("regularPrice", item.regular_price))
    price = money(payload.get("price", item.price))
    if regular is None or price is None or price > regular:
        return api_error("invalid_price", "Preço inválido ou maior que o preço regular.", 400)

    establishment_id = payload.get("establishmentId", item.establishment_id)
    if establishment_id is not None:
        if isinstance(establishment_id, bool) or not isinstance(establishment_id, int) or establishment_id <= 0:
            return api_error("invalid_establishment", "Estabelecimento inválido.", 400)
        if establishment_id not in _owned_active_establishments(profile):
            return api_error("establishment_not_allowed", "Vínculo ativo com o estabelecimento necessário.", 403)
    if establishment_id != item.establishment_id:
        has_slots = db.session.scalar(
            select(ExperienceSlot.id).where(ExperienceSlot.experience_id == item.id).limit(1)
        ) is not None
        if has_slots:
            return api_error("service_has_slots", "Não é possível mudar o local com horários existentes.", 409)

    # Preserve immutable slug, ownership, slots and publication state.
    item.establishment_id = establishment_id
    item.title = title.strip()
    item.category = category
    item.short_description = short.strip()
    item.description = description.strip() or None
    item.regular_price = regular
    item.price = price
    item.duration_minutes = duration
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        from flask import current_app
        current_app.logger.exception("Falha ao editar serviço via mobile")
        return api_error("service_save_failed", "Não foi possível atualizar o serviço.", 500)
    return api_json({"service": {
        "id": item.id, "title": item.title, "category": item.category,
        "status": item.status, "price": float(item.price),
        "durationMinutes": item.duration_minutes,
    }}, cache_control="private, no-store")


@api_onboarding_bp.post("/professional/services/<int:service_id>/status")
@limiter.limit("30 per hour")
def change_professional_service_status(service_id):
    user, error = _authenticated_user()
    if error is not None:
        return error
    profile = user.professional_profile
    if profile is None:
        return api_error("professional_profile_required", "Perfil profissional necessário.", 409)
    item = db.session.scalar(select(Experience).where(
        Experience.id == service_id,
        Experience.professional_id == profile.id,
    ))
    if item is None:
        return api_error("service_not_found", "Serviço não encontrado.", 404)
    payload, error = _json_body()
    if error is not None:
        return error
    if set(payload) != {"action"} or payload["action"] not in ("publish", "pause"):
        return api_error("invalid_action", "Informe uma ação válida: publish ou pause.", 400)
    action = payload["action"]
    if action == "publish":
        if item.status not in (ExperienceStatus.DRAFT, ExperienceStatus.PAUSED):
            return api_error("invalid_state", "Serviço não pode ser publicado neste estado.", 409)
        try:
            publish_experience(item)
        except ValueError as exc:
            db.session.rollback()
            return api_error("publication_ineligible", str(exc), 409)
    else:
        if item.status != ExperienceStatus.PUBLISHED:
            return api_error("invalid_state", "Somente serviços publicados podem ser pausados.", 409)
        item.status = ExperienceStatus.PAUSED
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        from flask import current_app
        current_app.logger.exception("Falha ao atualizar status do serviço")
        return api_error("service_save_failed", "Não foi possível atualizar o serviço.", 500)
    return api_json({"service": {
        "id": item.id, "title": item.title, "status": item.status,
        "category": item.category, "price": float(item.price),
        "durationMinutes": item.duration_minutes,
    }}, cache_control="private, no-store")

def _owned_active_establishments(profile):
    memberships = db.session.scalars(
        select(ProfessionalEstablishmentMembership).where(
            ProfessionalEstablishmentMembership.professional_id == profile.id,
            ProfessionalEstablishmentMembership.status == MembershipStatus.ACTIVE,
        )
    ).all()
    return {
        m.establishment_id: m.establishment.name
        for m in memberships
        if m.establishment is not None and m.establishment.is_active
    }


@api_onboarding_bp.get("/professional/service-establishments")
def list_professional_service_establishments():
    user, error = _authenticated_user()
    if error is not None:
        return error
    profile = user.professional_profile
    if profile is None:
        return api_error("professional_profile_required", "Perfil profissional necessário.", 409)
    choices = _owned_active_establishments(profile)
    return api_json({"items": [
        {"id": key, "name": name}
        for key, name in sorted(choices.items(), key=lambda entry: entry[1].lower())
    ]}, cache_control="private, no-store")



@api_onboarding_bp.route("/professional/services/<int:service_id>/availability", methods=["GET", "POST"])
@limiter.limit("60 per hour")
def professional_service_availability(service_id):
    """Manage own service slots using the same booking safeguards as Web."""
    user, error = _authenticated_user()
    if error is not None:
        return error
    profile = user.professional_profile
    if profile is None:
        return api_error("professional_profile_required", "Perfil profissional necessário.", 409)
    item = db.session.scalar(select(Experience).where(
        Experience.id == service_id, Experience.professional_id == profile.id,
    ))
    if item is None:
        return api_error("service_not_found", "Serviço não encontrado.", 404)

    if request.method == "POST":
        payload, error = _json_body()
        if error is not None:
            return error
        if set(payload) != {"date", "time"} or not all(
            isinstance(payload[k], str) for k in ("date", "time")
        ):
            return api_error("invalid_fields", "Informe data e horário.", 400)
        try:
            create_availability(
                user=user, experience_reference=str(item.id),
                slot_date=payload["date"], slot_time=payload["time"],
            )
        except AvailabilityError as exc:
            db.session.rollback()
            return api_error("availability_invalid", str(exc), 409)

    slots = db.session.scalars(
        select(ExperienceSlot).where(
            ExperienceSlot.experience_id == item.id,
            ExperienceSlot.professional_id == profile.id,
            ExperienceSlot.starts_at >= utcnow(),
        ).order_by(ExperienceSlot.starts_at.asc()).limit(100)
    ).all()
    return api_json({
        "items": [
            {
                "id": slot.id,
                "startsAt": to_local(slot.starts_at, profile.timezone).isoformat(),
                "endsAt": to_local(slot.ends_at, profile.timezone).isoformat(),
                "status": slot.status,
            }
            for slot in slots
        ],
    }, status=201 if request.method == "POST" else 200,
        cache_control="private, no-store")


@api_onboarding_bp.post("/professional/services/<int:service_id>/availability/<int:slot_id>/status")
@limiter.limit("30 per hour")
def change_professional_slot_status(service_id, slot_id):
    user, error = _authenticated_user()
    if error is not None:
        return error
    profile = user.professional_profile
    if profile is None:
        return api_error("professional_profile_required", "Perfil profissional necessário.", 409)
    slot = db.session.scalar(select(ExperienceSlot).where(
        ExperienceSlot.id == slot_id,
        ExperienceSlot.experience_id == service_id,
        ExperienceSlot.professional_id == profile.id,
    ).with_for_update())
    if slot is None:
        return api_error("slot_not_found", "Horário não encontrado.", 404)
    payload, error = _json_body()
    if error is not None:
        return error
    if set(payload) != {"action"} or payload["action"] not in ("block", "reopen"):
        return api_error("invalid_action", "Ação inválida.", 400)
    if payload["action"] == "block":
        # Do not silently cancel pending holds or confirmed bookings.
        if slot.status != SlotStatus.AVAILABLE:
            return api_error("invalid_slot_state", "Somente horários disponíveis podem ser bloqueados.", 409)
        if not block_slot_manual(slot):
            return api_error("invalid_slot_state", "Horário não pode ser bloqueado.", 409)
    else:
        if slot.status != SlotStatus.BLOCKED_MANUAL:
            return api_error("invalid_slot_state", "Somente bloqueios manuais podem ser liberados.", 409)
        try:
            reopen_manual_slot(slot)
        except BookingStateError as exc:
            db.session.rollback()
            return api_error("invalid_slot_state", str(exc), 409)
    return api_json({"slot": {
        "id": slot.id,
        "status": slot.status,
        "startsAt": to_local(slot.starts_at, profile.timezone).isoformat(),
    }}, cache_control="private, no-store")


@api_onboarding_bp.post("/professional/services/<int:service_id>/availability/from-schedule")
@limiter.limit("20 per hour")
def create_professional_slots_from_schedule(service_id):
    user, error = _authenticated_user()
    if error is not None:
        return error
    profile = user.professional_profile
    if profile is None:
        return api_error("professional_profile_required", "Perfil profissional necessário.", 409)
    item = db.session.scalar(select(Experience.id).where(
        Experience.id == service_id, Experience.professional_id == profile.id,
    ))
    if item is None:
        return api_error("service_not_found", "Serviço não encontrado.", 404)
    payload, error = _json_body()
    if error is not None:
        return error
    if set(payload) != {"date"} or not isinstance(payload["date"], str):
        return api_error("invalid_fields", "Informe somente a data AAAA-MM-DD.", 400)
    try:
        created = create_availability_from_working_hours(
            user=user, experience_reference=str(service_id), slot_date=payload["date"],
        )
    except AvailabilityError as exc:
        db.session.rollback()
        return api_error("availability_invalid", str(exc), 409)
    return api_json({"createdCount": len(created)}, status=201, cache_control="private, no-store")
