from flask import Blueprint, request
from flask_login import current_user

from app.extensions import csrf, limiter
from app.services.api_auth import (
    get_user_by_access_token,
)
from app.services.api_contract import (
    api_error,
    api_json,
    pagination_payload,
)
from app.models.notification import NotificationCategory
from app.services.notification_center import category_counts, context_label
from app.services.notification_service import (
    NotificationError,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    notification_preferences,
    serialize_notification,
    serialize_preference,
    update_notification_preferences,
)
from app.services.api_csrf import protect_cookie_mutation


api_notifications_bp = Blueprint(
    "api_notifications",
    __name__,
    url_prefix="/api/v1/notifications",
)

# Sessão por cookie da Web exige token CSRF nas mutações (AUD-04).
api_notifications_bp.before_request(protect_cookie_mutation)

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


def _page():
    try:
        offset = int(
            request.args.get(
                "offset",
                "0",
            )
        )
        limit = int(
            request.args.get(
                "limit",
                "30",
            )
        )
    except ValueError:
        return None

    if (
        offset < 0
        or limit < 1
        or limit > 50
    ):
        return None

    return offset, limit


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


@api_notifications_bp.get("")
@api_notifications_bp.get("/")
def notifications():
    user, error = _require_user()

    if error is not None:
        return error

    page = _page()

    if page is None:
        return api_error(
            "invalid_query_parameter",
            "Paginação inválida.",
            400,
        )

    unread_only = (
        request.args.get(
            "unreadOnly",
            "false",
        ).strip().lower()
        in {
            "1",
            "true",
            "yes",
        }
    )

    offset, limit = page

    # PR 6a (DEC-ID-216): abas por categoria; sem categoria = Todas.
    category = (request.args.get("category") or "").strip() or None
    if category is not None and category not in NotificationCategory.VALUES:
        return api_error(
            "invalid_query_parameter",
            "Categoria de notificação inválida.",
            400,
        )

    rows, total, unread_count = (
        list_notifications(
            user,
            offset=offset,
            limit=limit,
            unread_only=unread_only,
            category=category,
        )
    )

    counts = category_counts(user, unread_only=unread_only)

    return api_json(
        {
            "items": [
                {
                    **serialize_notification(item),
                    "contextLabel": context_label(user, item),
                }
                for item in rows
            ],
            # Total por aba com o mesmo filtro de lidas (bookings, social,
            # work e all).
            "counts": {
                "all": counts["todas"],
                "bookings": counts["reservas"],
                "social": counts["social"],
                "work": counts["profissional"],
            },
            "unreadCount":
                unread_count,
            "pagination":
                pagination_payload(
                    total=total,
                    offset=offset,
                    limit=limit,
                ),
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_notifications_bp.put(
    "/<int:notification_id>/read"
)
@csrf.exempt
@limiter.limit("240 per hour")
def read_notification(
    notification_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        notification = (
            mark_notification_read(
                user,
                notification_id,
            )
        )
    except NotificationError as exc:
        return api_error(
            "notification_not_found",
            str(exc),
            404,
        )

    return api_json(
        {
            "notification":
                serialize_notification(
                    notification
                )
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_notifications_bp.put(
    "/read-all"
)
@csrf.exempt
@limiter.limit("120 per hour")
def read_all_notifications():
    user, error = _require_user()

    if error is not None:
        return error

    changed = (
        mark_all_notifications_read(
            user
        )
    )

    return api_json(
        {
            "updated": changed,
            "unreadCount": 0,
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_notifications_bp.get(
    "/preferences"
)
def get_preferences():
    user, error = _require_user()

    if error is not None:
        return error

    preference = (
        notification_preferences(
            user
        )
    )

    return api_json(
        {
            "preferences":
                serialize_preference(
                    preference
                )
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_notifications_bp.put(
    "/preferences"
)
@csrf.exempt
@limiter.limit("120 per hour")
def put_preferences():
    user, error = _require_user()

    if error is not None:
        return error

    payload, error = _json_body()

    if error is not None:
        return error

    try:
        preference = (
            update_notification_preferences(
                user,
                payload,
            )
        )
    except NotificationError as exc:
        return api_error(
            "invalid_notification_preferences",
            str(exc),
            400,
        )

    return api_json(
        {
            "preferences":
                serialize_preference(
                    preference
                )
        },
        cache_control=(
            "private, no-store"
        ),
    )
