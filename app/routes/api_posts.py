from flask import Blueprint, request
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import csrf, db, limiter
from app.models.work_post import (
    WorkPostStatus,
)
from app.services.api_auth import (
    get_user_by_access_token,
)
from app.services.api_contract import (
    api_error,
    api_json,
)
from app.services.feed_service import (
    FeedError,
    feed_page,
    public_post,
    serialize_work_post,
)
from app.services.media_service import (
    MAX_IMAGE_BYTES,
    UploadBatch,
    delete_uploaded_file,
)
from app.services.work_post_service import (
    WorkPostError,
    create_work_post,
    creator_options,
    delete_work_post,
    owned_work_post,
    owned_posts_query,
    replace_work_post_image,
    update_work_post,
)


api_posts_bp = Blueprint(
    "api_posts",
    __name__,
    url_prefix="/api/v1",
)

MAX_POST_BODY_BYTES = 32_768
MAX_POST_MULTIPART_BYTES = (
    MAX_IMAGE_BYTES
    + (512 * 1024)
)


def _optional_user():
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
    user = _optional_user()

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
        > MAX_POST_BODY_BYTES
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


def _multipart_file():
    if (
        request.content_length
        is not None
        and request.content_length
        > MAX_POST_MULTIPART_BYTES
    ):
        return (
            None,
            api_error(
                "request_too_large",
                "A imagem deve ter no máximo 5 MB.",
                413,
            ),
        )

    if (
        not request.content_type
        or "multipart/form-data"
        not in request.content_type.lower()
    ):
        return (
            None,
            api_error(
                "multipart_required",
                "Envie a publicação como multipart/form-data.",
                415,
            ),
        )

    file_storage = request.files.get(
        "file"
    )

    if (
        file_storage is None
        or not getattr(
            file_storage,
            "filename",
            "",
        )
    ):
        return (
            None,
            api_error(
                "image_required",
                "Selecione uma imagem.",
                400,
            ),
        )

    return file_storage, None


def _optional_int(value, label):
    if value in (
        None,
        "",
    ):
        return None

    try:
        parsed = int(value)
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise WorkPostError(
            f"{label} inválido."
        ) from exc

    if parsed <= 0:
        raise WorkPostError(
            f"{label} inválido."
        )

    return parsed


def _creator_payload(post):
    payload = (
        serialize_work_post(
            post
        )
    )
    payload.update(
        {
            "status": post.status,
            "experienceId": (
                str(
                    post.experience_id
                )
                if post.experience_id
                is not None
                else None
            ),
            "createdAt": (
                post.created_at.isoformat()
                if post.created_at
                else None
            ),
            "updatedAt": (
                post.updated_at.isoformat()
                if post.updated_at
                else None
            ),
        }
    )
    return payload


@api_posts_bp.get(
    "/feed"
)
def get_feed():
    mode = request.args.get(
        "mode",
        "for-you",
    )
    cursor = request.args.get(
        "cursor"
    )
    limit = request.args.get(
        "limit",
        "20",
    )

    user = _optional_user()

    try:
        result = feed_page(
            mode=mode,
            user=user,
            cursor=cursor,
            limit=limit,
        )
    except FeedError as exc:
        status = (
            401
            if (
                mode == "following"
                and user is None
            )
            else 400
        )

        return api_error(
            (
                "authentication_required"
                if status == 401
                else "invalid_feed_request"
            ),
            str(exc),
            status,
        )

    return api_json(
        result,
        cache_control=(
            "private, no-store"
            if user is not None
            else "public, max-age=30"
        ),
    )


@api_posts_bp.get(
    "/posts/<int:post_id>"
)
def get_post(
    post_id,
):
    user = _optional_user()
    payload = public_post(
        post_id
    )

    if payload is not None:
        can_manage = False

        if user is not None:
            try:
                owned = (
                    owned_work_post(
                        user=user,
                        post_id=post_id,
                    )
                )
                can_manage = True
                payload["status"] = (
                    owned.status
                )
            except WorkPostError:
                pass

        payload[
            "canManage"
        ] = can_manage

        return api_json(
            payload,
            cache_control=(
                "private, no-store"
                if user is not None
                else "public, max-age=30"
            ),
        )

    if user is None:
        return api_error(
            "post_not_found",
            "Publicação não encontrada.",
            404,
        )

    try:
        post = owned_work_post(
            user=user,
            post_id=post_id,
        )
    except WorkPostError:
        return api_error(
            "post_not_found",
            "Publicação não encontrada.",
            404,
        )

    private_payload = (
        _creator_payload(
            post
        )
    )
    private_payload[
        "canManage"
    ] = True

    return api_json(
        private_payload,
        cache_control=(
            "private, no-store"
        ),
    )


@api_posts_bp.get(
    "/posts/options"
)
def get_post_options():
    user, error = _require_user()

    if error is not None:
        return error

    return api_json(
        creator_options(
            user
        ),
        cache_control=(
            "private, no-store"
        ),
    )


@api_posts_bp.get(
    "/posts/mine"
)
def get_my_posts():
    user, error = _require_user()

    if error is not None:
        return error

    items = db.session.scalars(
        owned_posts_query(
            user
        )
    ).all()

    return api_json(
        {
            "items": [
                _creator_payload(
                    post
                )
                for post in items
            ]
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_posts_bp.post(
    "/posts"
)
@csrf.exempt
@limiter.limit("40 per hour")
def create_post():
    user, error = _require_user()

    if error is not None:
        return error

    file_storage, error = (
        _multipart_file()
    )

    if error is not None:
        return error

    try:
        author_type = (
            request.form.get(
                "authorType",
                "",
            )
            or ""
        ).strip()

        author_id = _optional_int(
            request.form.get(
                "authorId"
            ),
            "Autor",
        )

        experience_id = (
            _optional_int(
                request.form.get(
                    "experienceId"
                ),
                "Serviço",
            )
        )

        status = (
            request.form.get(
                "status",
                WorkPostStatus.PUBLISHED,
            )
            or WorkPostStatus.PUBLISHED
        ).strip()

        with UploadBatch() as uploads:
            stored_path = (
                uploads.save_image(
                    file_storage,
                    "work-posts",
                )
            )

            post = create_work_post(
                user=user,
                author_type=author_type,
                author_id=author_id,
                image_url=stored_path,
                caption=request.form.get(
                    "caption"
                ),
                experience_id=experience_id,
                status=status,
                image_focus_x=(
                    request.form.get(
                        "focusX",
                        50,
                    )
                ),
                image_focus_y=(
                    request.form.get(
                        "focusY",
                        50,
                    )
                ),
            )

            uploads.commit()

    except WorkPostError as exc:
        db.session.rollback()
        return api_error(
            "invalid_post",
            str(exc),
            400,
        )
    except ValueError as exc:
        db.session.rollback()
        return api_error(
            "invalid_image",
            str(exc),
            400,
        )
    except (
        OSError,
        SQLAlchemyError,
    ):
        db.session.rollback()
        return api_error(
            "post_create_failed",
            "Não foi possível publicar agora.",
            503,
        )

    return api_json(
        {
            "post": (
                _creator_payload(
                    post
                )
            )
        },
        201,
        cache_control=(
            "private, no-store"
        ),
    )


@api_posts_bp.put(
    "/posts/<int:post_id>"
)
@csrf.exempt
@limiter.limit("80 per hour")
def edit_post(
    post_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    payload, error = _json_body()

    if error is not None:
        return error

    try:
        post = update_work_post(
            user=user,
            post_id=post_id,
            caption=payload.get(
                "caption"
            ),
            caption_supplied=(
                "caption"
                in payload
            ),
            experience_id=payload.get(
                "experienceId"
            ),
            experience_supplied=(
                "experienceId"
                in payload
            ),
            status=payload.get(
                "status"
            ),
            image_focus_x=payload.get(
                "focusX"
            ),
            image_focus_y=payload.get(
                "focusY"
            ),
        )
    except WorkPostError as exc:
        return api_error(
            "invalid_post_update",
            str(exc),
            400,
        )
    except SQLAlchemyError:
        db.session.rollback()
        return api_error(
            "post_update_failed",
            "Não foi possível atualizar agora.",
            503,
        )

    return api_json(
        {
            "post": (
                _creator_payload(
                    post
                )
            )
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_posts_bp.post(
    "/posts/<int:post_id>/image"
)
@csrf.exempt
@limiter.limit("40 per hour")
def replace_post_image(
    post_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    file_storage, error = (
        _multipart_file()
    )

    if error is not None:
        return error

    previous = None

    try:
        with UploadBatch() as uploads:
            stored_path = (
                uploads.save_image(
                    file_storage,
                    "work-posts",
                )
            )

            post, previous = (
                replace_work_post_image(
                    user=user,
                    post_id=post_id,
                    image_url=stored_path,
                    image_focus_x=(
                        request.form.get(
                            "focusX",
                            50,
                        )
                    ),
                    image_focus_y=(
                        request.form.get(
                            "focusY",
                            50,
                        )
                    ),
                )
            )

            uploads.commit()

    except WorkPostError as exc:
        db.session.rollback()
        return api_error(
            "post_not_found",
            str(exc),
            404,
        )
    except ValueError as exc:
        db.session.rollback()
        return api_error(
            "invalid_image",
            str(exc),
            400,
        )
    except (
        OSError,
        SQLAlchemyError,
    ):
        db.session.rollback()
        return api_error(
            "post_update_failed",
            "Não foi possível atualizar a imagem agora.",
            503,
        )

    if (
        previous
        and previous
        != post.image_url
    ):
        delete_uploaded_file(
            previous
        )

    return api_json(
        {
            "post": (
                _creator_payload(
                    post
                )
            )
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_posts_bp.delete(
    "/posts/<int:post_id>"
)
@csrf.exempt
@limiter.limit("80 per hour")
def remove_post(
    post_id,
):
    user, error = _require_user()

    if error is not None:
        return error

    try:
        image_url = delete_work_post(
            user=user,
            post_id=post_id,
        )
    except WorkPostError as exc:
        return api_error(
            "post_not_found",
            str(exc),
            404,
        )
    except SQLAlchemyError:
        db.session.rollback()
        return api_error(
            "post_delete_failed",
            "Não foi possível excluir agora.",
            503,
        )

    delete_uploaded_file(
        image_url
    )

    return api_json(
        {
            "success": True,
        },
        cache_control=(
            "private, no-store"
        ),
    )
