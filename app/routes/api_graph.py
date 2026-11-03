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
from app.services.beauty_graph_service import (
    MAX_LEGACY_SLUGS,
    BeautyGraphError,
    OwnProfileError,
    follow_target,
    following_page,
    graph_state,
    reconcile_graph,
    saved_items,
    save_target,
    unfollow_target,
    unsave_target,
)
from app.services.api_csrf import protect_cookie_mutation


api_graph_bp = Blueprint(
    "api_graph",
    __name__,
    url_prefix="/api/v1/graph",
)

# Sessão por cookie da Web exige token CSRF nas mutações (AUD-04).
api_graph_bp.before_request(protect_cookie_mutation)

MAX_GRAPH_BODY_BYTES = 65_536
MAX_RECONCILE_ITEMS = 500


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
        > MAX_GRAPH_BODY_BYTES
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


def _references(
    payload,
    key,
):
    value = payload.get(
        key,
        [],
    )

    if not isinstance(
        value,
        list,
    ):
        raise BeautyGraphError(
            f"{key}: envie uma lista."
        )

    if (
        len(value)
        > MAX_RECONCILE_ITEMS
    ):
        raise BeautyGraphError(
            (
                f"{key}: envie no máximo "
                f"{MAX_RECONCILE_ITEMS} itens."
            )
        )

    references = []

    for item in value:
        if not isinstance(
            item,
            dict,
        ):
            raise BeautyGraphError(
                f"{key}: item inválido."
            )

        target_type = item.get(
            "targetType"
        )
        target_id = item.get(
            "targetId"
        )

        if (
            not isinstance(
                target_type,
                str,
            )
            or not isinstance(
                target_id,
                int,
            )
            or target_id <= 0
        ):
            raise BeautyGraphError(
                f"{key}: referência inválida."
            )

        references.append(
            {
                "targetType":
                    target_type,
                "targetId":
                    target_id,
            }
        )

    return references


@api_graph_bp.get("")
@api_graph_bp.get("/")
def get_graph():
    user, error = _require_user()

    if error is not None:
        return error

    return api_json(
        graph_state(user),
        cache_control=(
            "private, no-store"
        ),
    )


@api_graph_bp.put(
    "/follows/<target_type>/"
    "<int:target_id>"
)
@csrf.exempt
@limiter.limit("120 per hour")
def put_follow(
    target_type,
    target_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        follow_target(
            user=user,
            target_type=target_type,
            target_id=target_id,
        )
    except OwnProfileError as exc:
        return api_error(
            "own_profile",
            str(exc),
            400,
        )
    except BeautyGraphError as exc:
        return api_error(
            "invalid_follow_target",
            str(exc),
            404,
        )

    return api_json(
        {
            "following": True,
            "targetType": target_type,
            "targetId": target_id,
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_graph_bp.delete(
    "/follows/<target_type>/"
    "<int:target_id>"
)
@csrf.exempt
@limiter.limit("120 per hour")
def delete_follow(
    target_type,
    target_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        removed = unfollow_target(
            user=user,
            target_type=target_type,
            target_id=target_id,
        )
    except BeautyGraphError as exc:
        return api_error(
            "invalid_follow_target",
            str(exc),
            400,
        )

    return api_json(
        {
            "following": False,
            "removed": removed,
            "targetType": target_type,
            "targetId": target_id,
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_graph_bp.put(
    "/saves/<target_type>/"
    "<int:target_id>"
)
@csrf.exempt
@limiter.limit("120 per hour")
def put_save(
    target_type,
    target_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        save_target(
            user=user,
            target_type=target_type,
            target_id=target_id,
        )
    except BeautyGraphError as exc:
        return api_error(
            "invalid_save_target",
            str(exc),
            404,
        )

    return api_json(
        {
            "saved": True,
            "targetType": target_type,
            "targetId": target_id,
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_graph_bp.delete(
    "/saves/<target_type>/"
    "<int:target_id>"
)
@csrf.exempt
@limiter.limit("120 per hour")
def delete_save(
    target_type,
    target_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        removed = unsave_target(
            user=user,
            target_type=target_type,
            target_id=target_id,
        )
    except BeautyGraphError as exc:
        return api_error(
            "invalid_save_target",
            str(exc),
            400,
        )

    return api_json(
        {
            "saved": False,
            "removed": removed,
            "targetType": target_type,
            "targetId": target_id,
        },
        cache_control=(
            "private, no-store"
        ),
    )


def _legacy_slugs(payload):
    """Favoritos antigos da Web: slugs de experiência guardados no navegador."""
    value = payload.get("experienceSlugs", [])

    if not isinstance(value, list):
        raise BeautyGraphError("experienceSlugs: envie uma lista.")

    if len(value) > MAX_LEGACY_SLUGS:
        raise BeautyGraphError(
            f"experienceSlugs: envie no máximo {MAX_LEGACY_SLUGS} itens."
        )

    slugs = []

    for item in value:
        if not isinstance(item, str) or not 0 < len(item) <= 200:
            raise BeautyGraphError("experienceSlugs: item inválido.")
        if item not in slugs:
            slugs.append(item)

    return slugs


@api_graph_bp.get("/following")
def get_following():
    user, error = _require_user()

    if error is not None:
        return error

    limit = request.args.get("limit", type=int) or 20
    cursor = request.args.get("cursor")

    if cursor is not None and not cursor.isdigit():
        return api_error(
            "invalid_cursor",
            "Não foi possível continuar a lista.",
            400,
        )

    return api_json(
        following_page(
            user,
            limit=limit,
            before=int(cursor) if cursor else None,
        ),
        cache_control=(
            "private, no-store"
        ),
    )


@api_graph_bp.post(
    "/reconcile"
)
@csrf.exempt
@limiter.limit("20 per hour")
def reconcile():
    user, error = _require_user()

    if error is not None:
        return error

    payload, error = _json_body()

    if error is not None:
        return error

    try:
        follows = _references(
            payload,
            "follows",
        )
        saves = _references(
            payload,
            "saves",
        )
        experience_slugs = _legacy_slugs(payload)

        result = reconcile_graph(
            user=user,
            follows=follows,
            saves=saves,
            experience_slugs=experience_slugs,
        )
    except BeautyGraphError as exc:
        return api_error(
            "invalid_graph_payload",
            str(exc),
            400,
        )

    return api_json(
        result,
        cache_control=(
            "private, no-store"
        ),
    )



@api_graph_bp.get(
    "/saved-items"
)
def get_saved_items():
    user, error = _require_user()

    if error is not None:
        return error

    return api_json(
        saved_items(user),
        cache_control=(
            "private, no-store"
        ),
    )
