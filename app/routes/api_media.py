from sqlalchemy.exc import SQLAlchemyError
from flask import Blueprint, request

from app.extensions import csrf, db, limiter
from app.models.professional import (
    ProfessionalPortfolioItem,
)
from app.services.api_auth import (
    get_user_by_access_token,
)
from app.services.api_contract import (
    api_error,
    api_json,
)
from app.services.media_service import (
    MAX_IMAGE_BYTES,
    UploadBatch,
    delete_uploaded_file,
)
from app.services.media_storage import (
    resolve_media_url,
)


api_media_bp = Blueprint(
    "api_media",
    __name__,
    url_prefix="/api/v1/media",
)

MAX_MULTIPART_BYTES = (
    MAX_IMAGE_BYTES
    + (512 * 1024)
)


def _bearer_user():
    authorization = request.headers.get(
        "Authorization",
        "",
    )
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


def _authenticated_profile():
    user = _bearer_user()

    if user is None:
        return (
            None,
            api_error(
                "authentication_required",
                "Entre na sua conta para continuar.",
                401,
            ),
        )

    profile = user.professional_profile

    if profile is None:
        return (
            None,
            api_error(
                "professional_profile_required",
                (
                    "Crie seu perfil profissional "
                    "antes de enviar mídia."
                ),
                409,
            ),
        )

    return profile, None


def _multipart_file():
    if (
        request.content_length
        is not None
        and request.content_length
        > MAX_MULTIPART_BYTES
    ):
        return (
            None,
            api_error(
                "request_too_large",
                "A imagem deve ter no máximo 5 MB.",
                413,
            ),
        )

    if not request.content_type or (
        "multipart/form-data"
        not in request.content_type.lower()
    ):
        return (
            None,
            api_error(
                "multipart_required",
                (
                    "Envie a imagem como "
                    "multipart/form-data."
                ),
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


def _focus_value(value):
    if value in (None, ""):
        return 50

    try:
        return max(
            0,
            min(
                100,
                int(value),
            ),
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            (
                "O ponto focal deve ser "
                "um número entre 0 e 100."
            )
        ) from exc


def _image_payload(
    stored_path,
    *,
    focus_x=None,
    focus_y=None,
):
    return {
        "storedPath": stored_path,
        "url": resolve_media_url(
            stored_path,
            external=True,
        ),
        "focusX": focus_x,
        "focusY": focus_y,
    }


def _portfolio_payload(item):
    return {
        "id": item.id,
        "imageUrl": resolve_media_url(
            item.image_url,
            external=True,
        ),
        "storedPath": item.image_url,
        "caption": item.caption,
        "sortOrder": item.sort_order,
    }


def _completion_payload(profile):
    return {
        "percentage": (
            profile.profile_completion
        ),
        "readyToPublish": (
            profile.ready_to_publish
        ),
        "portfolioCount": len(
            profile.portfolio_items
        ),
        "isActive": profile.is_active,
    }


def _deactivate_if_incomplete(
    profile,
):
    profile.onboarding_completed = (
        profile.ready_to_publish
    )

    if (
        profile.is_active
        and not profile.ready_to_publish
    ):
        profile.is_active = False
        profile.published_at = None


@api_media_bp.post(
    "/professional/avatar"
)
@csrf.exempt
@limiter.limit("30 per hour")
def upload_professional_avatar():
    profile, error = (
        _authenticated_profile()
    )

    if error is not None:
        return error

    file_storage, error = (
        _multipart_file()
    )

    if error is not None:
        return error

    replaced_media = (
        profile.avatar_url
    )

    try:
        focus_x = _focus_value(
            request.form.get(
                "focusX"
            )
        )
        focus_y = _focus_value(
            request.form.get(
                "focusY"
            )
        )

        with UploadBatch() as uploads:
            stored_path = (
                uploads.save_image(
                    file_storage,
                    "professionals",
                )
            )

            profile.avatar_url = (
                stored_path
            )
            profile.avatar_focus_x = (
                focus_x
            )
            profile.avatar_focus_y = (
                focus_y
            )
            profile.onboarding_completed = (
                profile.ready_to_publish
            )

            db.session.commit()
            uploads.commit()

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
            "media_upload_failed",
            (
                "Não foi possível salvar "
                "a imagem agora."
            ),
            503,
        )

    if (
        replaced_media
        and replaced_media
        != stored_path
    ):
        delete_uploaded_file(
            replaced_media
        )

    return api_json(
        {
            "avatar": _image_payload(
                stored_path,
                focus_x=focus_x,
                focus_y=focus_y,
            ),
            "completion": (
                _completion_payload(
                    profile
                )
            ),
        },
        cache_control="no-store",
    )


@api_media_bp.post(
    "/professional/cover"
)
@csrf.exempt
@limiter.limit("30 per hour")
def upload_professional_cover():
    profile, error = (
        _authenticated_profile()
    )

    if error is not None:
        return error

    file_storage, error = (
        _multipart_file()
    )

    if error is not None:
        return error

    replaced_media = (
        profile.cover_url
    )

    try:
        focus_x = _focus_value(
            request.form.get(
                "focusX"
            )
        )
        focus_y = _focus_value(
            request.form.get(
                "focusY"
            )
        )

        with UploadBatch() as uploads:
            stored_path = (
                uploads.save_image(
                    file_storage,
                    "professionals/covers",
                )
            )

            profile.cover_url = (
                stored_path
            )
            profile.cover_focus_x = (
                focus_x
            )
            profile.cover_focus_y = (
                focus_y
            )

            db.session.commit()
            uploads.commit()

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
            "media_upload_failed",
            (
                "Não foi possível salvar "
                "a imagem agora."
            ),
            503,
        )

    if (
        replaced_media
        and replaced_media
        != stored_path
    ):
        delete_uploaded_file(
            replaced_media
        )

    return api_json(
        {
            "cover": _image_payload(
                stored_path,
                focus_x=focus_x,
                focus_y=focus_y,
            ),
            "completion": (
                _completion_payload(
                    profile
                )
            ),
        },
        cache_control="no-store",
    )


@api_media_bp.put(
    "/professional/cover/focus"
)
@csrf.exempt
@limiter.limit("60 per hour")
def update_professional_cover_focus():
    profile, error = (
        _authenticated_profile()
    )

    if error is not None:
        return error

    if not request.is_json:
        return api_error(
            "json_required",
            "Envie os dados em formato JSON.",
            415,
        )

    payload = request.get_json(
        silent=True
    )

    if not isinstance(payload, dict):
        return api_error(
            "invalid_json",
            "Não foi possível ler os dados enviados.",
            400,
        )

    if not profile.cover_url:
        return api_error(
            "cover_required",
            "Adicione uma capa antes de ajustar o enquadramento.",
            409,
        )

    try:
        focus_x = _focus_value(
            payload.get(
                "focusX"
            )
        )
        focus_y = _focus_value(
            payload.get(
                "focusY"
            )
        )

        profile.cover_focus_x = (
            focus_x
        )
        profile.cover_focus_y = (
            focus_y
        )
        db.session.commit()

    except ValueError as exc:
        db.session.rollback()
        return api_error(
            "invalid_focus",
            str(exc),
            400,
        )
    except SQLAlchemyError:
        db.session.rollback()
        return api_error(
            "cover_update_failed",
            (
                "Não foi possível ajustar "
                "a capa agora."
            ),
            503,
        )

    return api_json(
        {
            "focusX": focus_x,
            "focusY": focus_y,
        },
        cache_control="no-store",
    )


@api_media_bp.post(
    "/professional/portfolio"
)
@csrf.exempt
@limiter.limit("60 per hour")
def upload_professional_portfolio():
    profile, error = (
        _authenticated_profile()
    )

    if error is not None:
        return error

    file_storage, error = (
        _multipart_file()
    )

    if error is not None:
        return error

    if len(
        profile.portfolio_items
    ) >= 8:
        return api_error(
            "portfolio_limit_reached",
            (
                "Seu portfólio pode ter "
                "no máximo 8 imagens."
            ),
            409,
        )

    caption = (
        request.form.get(
            "caption",
            "",
        )
        or ""
    ).strip()

    if len(caption) > 180:
        return api_error(
            "invalid_caption",
            (
                "A legenda deve ter "
                "no máximo 180 caracteres."
            ),
            400,
        )

    try:
        with UploadBatch() as uploads:
            stored_path = (
                uploads.save_image(
                    file_storage,
                    "professionals/portfolio",
                )
            )

            item = (
                ProfessionalPortfolioItem(
                    professional=profile,
                    image_url=stored_path,
                    caption=(
                        caption or None
                    ),
                    sort_order=(
                        len(
                            profile.portfolio_items
                        )
                    ),
                )
            )

            db.session.add(item)
            db.session.flush()

            profile.onboarding_completed = (
                profile.ready_to_publish
            )

            db.session.commit()
            uploads.commit()

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
            "media_upload_failed",
            (
                "Não foi possível salvar "
                "a imagem agora."
            ),
            503,
        )

    return api_json(
        {
            "item": _portfolio_payload(
                item
            ),
            "completion": (
                _completion_payload(
                    profile
                )
            ),
        },
        201,
        cache_control="no-store",
    )


@api_media_bp.delete(
    "/professional/portfolio/"
    "<int:item_id>"
)
@csrf.exempt
@limiter.limit("60 per hour")
def delete_professional_portfolio(
    item_id,
):
    profile, error = (
        _authenticated_profile()
    )

    if error is not None:
        return error

    item = db.session.get(
        ProfessionalPortfolioItem,
        item_id,
    )

    if (
        item is None
        or item.professional_id
        != profile.id
    ):
        return api_error(
            "portfolio_item_not_found",
            "Imagem do portfólio não encontrada.",
            404,
        )

    stored_path = item.image_url

    try:
        profile.portfolio_items.remove(
            item
        )
        db.session.flush()

        for index, current in enumerate(
            profile.portfolio_items
        ):
            current.sort_order = index

        _deactivate_if_incomplete(
            profile
        )
        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        return api_error(
            "portfolio_update_failed",
            (
                "Não foi possível atualizar "
                "o portfólio agora."
            ),
            503,
        )

    delete_uploaded_file(
        stored_path
    )

    return api_json(
        {
            "completion": (
                _completion_payload(
                    profile
                )
            ),
            "portfolio": [
                _portfolio_payload(
                    current
                )
                for current
                in profile.portfolio_items
            ],
        },
        cache_control="no-store",
    )


@api_media_bp.put(
    "/professional/portfolio/order"
)
@csrf.exempt
@limiter.limit("60 per hour")
def reorder_professional_portfolio():
    profile, error = (
        _authenticated_profile()
    )

    if error is not None:
        return error

    if not request.is_json:
        return api_error(
            "json_required",
            "Envie os dados em formato JSON.",
            415,
        )

    payload = request.get_json(
        silent=True
    )

    if not isinstance(payload, dict):
        return api_error(
            "invalid_json",
            "Não foi possível ler os dados enviados.",
            400,
        )

    item_ids = payload.get(
        "itemIds"
    )

    if (
        not isinstance(
            item_ids,
            list,
        )
        or any(
            not isinstance(
                item_id,
                int,
            )
            for item_id
            in item_ids
        )
    ):
        return api_error(
            "invalid_portfolio_order",
            (
                "Informe a ordem completa "
                "dos itens do portfólio."
            ),
            400,
        )

    current_items = list(
        profile.portfolio_items
    )
    current_ids = {
        item.id
        for item
        in current_items
    }

    if (
        len(item_ids)
        != len(current_items)
        or len(set(item_ids))
        != len(item_ids)
        or set(item_ids)
        != current_ids
    ):
        return api_error(
            "invalid_portfolio_order",
            (
                "A ordem deve conter todos "
                "os itens do seu portfólio "
                "uma única vez."
            ),
            400,
        )

    by_id = {
        item.id: item
        for item
        in current_items
    }

    try:
        for index, item_id in enumerate(
            item_ids
        ):
            by_id[
                item_id
            ].sort_order = index

        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        return api_error(
            "portfolio_update_failed",
            (
                "Não foi possível atualizar "
                "a ordem agora."
            ),
            503,
        )

    ordered = [
        by_id[item_id]
        for item_id
        in item_ids
    ]

    return api_json(
        {
            "portfolio": [
                _portfolio_payload(
                    item
                )
                for item in ordered
            ]
        },
        cache_control="no-store",
    )
