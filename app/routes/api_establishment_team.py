from flask import Blueprint, request
from flask_login import current_user

from app.extensions import csrf, limiter
from app.services.api_auth import (
    get_user_by_access_token,
)
from app.services.api_contract import (
    api_error,
    api_json,
)
from app.services.establishment_team_service import (
    EstablishmentTeamError,
    accept_invitation,
    establishment_team,
    invite_professional,
    professional_membership_invites,
    reject_invitation,
    remove_team_member,
    require_establishment_manager,
    serialize_membership,
)


api_establishment_team_bp = Blueprint(
    "api_establishment_team",
    __name__,
    url_prefix="/api/v1",
)

MAX_BODY_BYTES = 16_384


def _authenticated_user():
    authorization = request.headers.get(
        "Authorization"
    )

    if authorization is not None:
        parts = authorization.split()

        if (
            len(parts) != 2
            or parts[0].lower()
            != "bearer"
        ):
            return None

        return get_user_by_access_token(
            parts[1]
        )

    if (
        current_user.is_authenticated
        and current_user.is_active
    ):
        return current_user

    return None


def _require_user():
    user = _authenticated_user()

    if user is None:
        return (
            None,
            api_error(
                "authentication_required",
                "Entre na sua conta para continuar.",
                401,
            ),
        )

    return user, None


def _json_body():
    if (
        request.content_length
        is not None
        and request.content_length
        > MAX_BODY_BYTES
    ):
        return (
            None,
            api_error(
                "request_too_large",
                "A solicitação é muito grande.",
                413,
            ),
        )

    if not request.is_json:
        return (
            None,
            api_error(
                "json_required",
                "Envie os dados em formato JSON.",
                415,
            ),
        )

    payload = request.get_json(
        silent=True
    )

    if not isinstance(
        payload,
        dict,
    ):
        return (
            None,
            api_error(
                "invalid_json",
                "Não foi possível ler os dados enviados.",
                400,
            ),
        )

    return payload, None


@api_establishment_team_bp.get(
    "/team/invitations"
)
def membership_invitations():
    user, error = _require_user()

    if error is not None:
        return error

    try:
        memberships = (
            professional_membership_invites(
                user
            )
        )
    except EstablishmentTeamError as exc:
        return api_error(
            "team_invites_unavailable",
            str(exc),
            400,
        )

    return api_json(
        {
            "items": [
                serialize_membership(
                    item
                )
                for item in memberships
            ]
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_establishment_team_bp.put(
    "/team/invitations/<int:membership_id>/accept"
)
@csrf.exempt
@limiter.limit("120 per hour")
def accept_team_invitation(
    membership_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        membership = accept_invitation(
            user,
            membership_id,
        )
    except EstablishmentTeamError as exc:
        return api_error(
            "invalid_team_invitation",
            str(exc),
            400,
        )

    return api_json(
        {
            "membership":
                serialize_membership(
                    membership
                )
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_establishment_team_bp.put(
    "/team/invitations/<int:membership_id>/reject"
)
@csrf.exempt
@limiter.limit("120 per hour")
def reject_team_invitation(
    membership_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        membership = reject_invitation(
            user,
            membership_id,
        )
    except EstablishmentTeamError as exc:
        return api_error(
            "invalid_team_invitation",
            str(exc),
            400,
        )

    return api_json(
        {
            "membership":
                serialize_membership(
                    membership
                )
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_establishment_team_bp.get(
    "/establishments/<establishment_reference>/team"
)
def managed_establishment_team(
    establishment_reference,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        establishment, access = (
            require_establishment_manager(
                user,
                establishment_reference,
            )
        )
        memberships = establishment_team(
            establishment
        )
    except EstablishmentTeamError as exc:
        return api_error(
            "team_access_denied",
            str(exc),
            403,
        )

    return api_json(
        {
            "establishment": {
                "id": str(
                    establishment.id
                ),
                "routeId":
                    establishment.slug,
                "name":
                    establishment.name,
            },
            "accessRole":
                access.role,
            "items": [
                serialize_membership(
                    item
                )
                for item in memberships
            ],
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_establishment_team_bp.post(
    "/establishments/<establishment_reference>/team"
)
@csrf.exempt
@limiter.limit("60 per hour")
def invite_team_member(
    establishment_reference,
):
    user, error = _require_user()

    if error is not None:
        return error

    payload, error = _json_body()

    if error is not None:
        return error

    try:
        membership = invite_professional(
            user=user,
            establishment_reference=(
                establishment_reference
            ),
            email=payload.get(
                "email"
            ),
            role_name=payload.get(
                "roleName"
            ),
        )
    except EstablishmentTeamError as exc:
        return api_error(
            "invalid_team_invitation",
            str(exc),
            400,
        )

    return api_json(
        {
            "membership":
                serialize_membership(
                    membership
                )
        },
        201,
        cache_control=(
            "private, no-store"
        ),
    )


@api_establishment_team_bp.delete(
    "/establishments/<establishment_reference>/team/<int:membership_id>"
)
@csrf.exempt
@limiter.limit("120 per hour")
def remove_member(
    establishment_reference,
    membership_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        membership = remove_team_member(
            user=user,
            establishment_reference=(
                establishment_reference
            ),
            membership_id=(
                membership_id
            ),
        )
    except EstablishmentTeamError as exc:
        return api_error(
            "team_member_remove_failed",
            str(exc),
            400,
        )

    return api_json(
        {
            "membership":
                serialize_membership(
                    membership
                ),
            "removed": True,
        },
        cache_control=(
            "private, no-store"
        ),
    )
