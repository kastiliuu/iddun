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
from app.services.job_service import (
    JobError,
    apply_to_job,
    close_job,
    create_job,
    managed_job_applications,
    managed_jobs,
    my_applications,
    public_job,
    public_jobs,
    publish_job,
    serialize_application,
    serialize_job,
    update_job,
    withdraw_application,
)


api_jobs_bp = Blueprint(
    "api_jobs",
    __name__,
    url_prefix="/api/v1",
)

MAX_BODY_BYTES = 32_768


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
                "20",
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


@api_jobs_bp.get(
    "/jobs"
)
def list_public_jobs():
    page = _page()

    if page is None:
        return api_error(
            "invalid_query_parameter",
            "Paginação inválida.",
            400,
        )

    offset, limit = page

    items, total = public_jobs(
        search=request.args.get(
            "q"
        ),
        city=request.args.get(
            "city"
        ),
        specialty=request.args.get(
            "specialty"
        ),
        offset=offset,
        limit=limit,
    )

    return api_json(
        {
            "items": [
                serialize_job(
                    item
                )
                for item in items
            ],
            "pagination":
                pagination_payload(
                    total=total,
                    offset=offset,
                    limit=limit,
                ),
        },
        cache_control=(
            "public, max-age=30"
        ),
    )


@api_jobs_bp.get(
    "/jobs/<int:job_id>"
)
def job_detail(
    job_id,
):
    try:
        job = public_job(
            job_id
        )
    except JobError as exc:
        return api_error(
            "job_not_found",
            str(exc),
            404,
        )

    return api_json(
        {
            "job":
                serialize_job(
                    job
                )
        },
        cache_control=(
            "public, max-age=30"
        ),
    )


@api_jobs_bp.get(
    "/jobs/applications/mine"
)
def list_my_applications():
    user, error = _require_user()

    if error is not None:
        return error

    try:
        items = my_applications(
            user
        )
    except JobError as exc:
        return api_error(
            "applications_unavailable",
            str(exc),
            400,
        )

    return api_json(
        {
            "items": [
                serialize_application(
                    item
                )
                for item in items
            ]
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_jobs_bp.post(
    "/jobs/<int:job_id>/apply"
)
@csrf.exempt
@limiter.limit(
    "60 per hour"
)
def apply_job(
    job_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    payload, error = _json_body()

    if error is not None:
        return error

    try:
        application = (
            apply_to_job(
                user=user,
                job_id=job_id,
                message=payload.get(
                    "message"
                ),
            )
        )
    except JobError as exc:
        message = str(exc)
        status = (
            409
            if "já se candidatou"
            in message
            else 400
        )

        return api_error(
            "job_application_failed",
            message,
            status,
        )

    return api_json(
        {
            "application":
                serialize_application(
                    application
                )
        },
        201,
        cache_control=(
            "private, no-store"
        ),
    )


@api_jobs_bp.delete(
    "/jobs/<int:job_id>/apply"
)
@csrf.exempt
@limiter.limit(
    "60 per hour"
)
def withdraw_job_application(
    job_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        application = (
            withdraw_application(
                user=user,
                job_id=job_id,
            )
        )
    except JobError as exc:
        return api_error(
            "job_application_withdraw_failed",
            str(exc),
            400,
        )

    return api_json(
        {
            "application":
                serialize_application(
                    application
                ),
            "withdrawn": True,
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_jobs_bp.get(
    "/establishments/<establishment_reference>/jobs"
)
def list_managed_jobs(
    establishment_reference,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        establishment, access, items = (
            managed_jobs(
                user=user,
                establishment_reference=(
                    establishment_reference
                ),
            )
        )
    except JobError as exc:
        return api_error(
            "jobs_access_denied",
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
                serialize_job(
                    item,
                    applications_count=(
                        len(
                            [
                                application
                                for application
                                in item.applications
                                if application.status
                                == "submitted"
                            ]
                        )
                    ),
                )
                for item in items
            ],
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_jobs_bp.post(
    "/establishments/<establishment_reference>/jobs"
)
@csrf.exempt
@limiter.limit(
    "60 per hour"
)
def create_managed_job(
    establishment_reference,
):
    user, error = _require_user()

    if error is not None:
        return error

    payload, error = _json_body()

    if error is not None:
        return error

    try:
        job = create_job(
            user=user,
            establishment_reference=(
                establishment_reference
            ),
            payload=payload,
        )
    except JobError as exc:
        return api_error(
            "invalid_job",
            str(exc),
            400,
        )

    return api_json(
        {
            "job":
                serialize_job(
                    job
                )
        },
        201,
        cache_control=(
            "private, no-store"
        ),
    )


@api_jobs_bp.put(
    "/establishments/<establishment_reference>/jobs/<int:job_id>"
)
@csrf.exempt
@limiter.limit(
    "120 per hour"
)
def update_managed_job(
    establishment_reference,
    job_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    payload, error = _json_body()

    if error is not None:
        return error

    try:
        job = update_job(
            user=user,
            establishment_reference=(
                establishment_reference
            ),
            job_id=job_id,
            payload=payload,
        )
    except JobError as exc:
        return api_error(
            "job_update_failed",
            str(exc),
            400,
        )

    return api_json(
        {
            "job":
                serialize_job(
                    job
                )
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_jobs_bp.put(
    "/establishments/<establishment_reference>/jobs/<int:job_id>/publish"
)
@csrf.exempt
@limiter.limit(
    "60 per hour"
)
def publish_managed_job(
    establishment_reference,
    job_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        job = publish_job(
            user=user,
            establishment_reference=(
                establishment_reference
            ),
            job_id=job_id,
        )
    except JobError as exc:
        return api_error(
            "job_publish_failed",
            str(exc),
            400,
        )

    return api_json(
        {
            "job":
                serialize_job(
                    job
                )
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_jobs_bp.put(
    "/establishments/<establishment_reference>/jobs/<int:job_id>/close"
)
@csrf.exempt
@limiter.limit(
    "60 per hour"
)
def close_managed_job(
    establishment_reference,
    job_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        job = close_job(
            user=user,
            establishment_reference=(
                establishment_reference
            ),
            job_id=job_id,
        )
    except JobError as exc:
        return api_error(
            "job_close_failed",
            str(exc),
            400,
        )

    return api_json(
        {
            "job":
                serialize_job(
                    job
                )
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_jobs_bp.get(
    "/establishments/<establishment_reference>/jobs/<int:job_id>/applications"
)
def list_job_applications(
    establishment_reference,
    job_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        job, items = (
            managed_job_applications(
                user=user,
                establishment_reference=(
                    establishment_reference
                ),
                job_id=job_id,
            )
        )
    except JobError as exc:
        return api_error(
            "job_applications_access_denied",
            str(exc),
            403,
        )

    return api_json(
        {
            "job":
                serialize_job(
                    job,
                    include_description=False,
                ),
            "items": [
                serialize_application(
                    item,
                    include_professional=True,
                )
                for item in items
            ],
        },
        cache_control=(
            "private, no-store"
        ),
    )
