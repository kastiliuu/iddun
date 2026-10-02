from datetime import date

from flask import Blueprint, request

from app.extensions import csrf, limiter
from app.services.api_auth import get_user_by_access_token
from app.services.api_contract import api_error, api_json
from app.services.media_storage import resolve_media_url
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
        "avatarUrl": (
            resolve_media_url(
                profile.avatar_url,
                external=True,
            )
            if profile.avatar_url
            else None
        ),
        "coverUrl": (
            resolve_media_url(
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
                "imageUrl": resolve_media_url(
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
