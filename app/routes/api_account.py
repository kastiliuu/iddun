from flask import Blueprint, request

from app.extensions import csrf, limiter
from app.services.account_privacy import (
    AccountDeletionBlocked,
    anonymize_account,
)
from app.services.api_auth import (
    get_user_by_access_token,
)
from app.services.api_contract import (
    api_error,
    api_json,
)


api_account_bp = Blueprint(
    "api_account",
    __name__,
    url_prefix="/api/v1/account",
)


def _bearer_user():
    authorization = (
        request.headers.get(
            "Authorization",
            "",
        )
    )
    parts = authorization.split()

    if (
        len(parts) != 2
        or parts[0].lower()
        != "bearer"
    ):
        return None

    return (
        get_user_by_access_token(
            parts[1]
        )
    )


@api_account_bp.post("/delete")
@csrf.exempt
@limiter.limit("3 per hour")
def delete_account():
    user = _bearer_user()

    if user is None:
        return api_error(
            "authentication_required",
            (
                "Entre na sua conta "
                "para continuar."
            ),
            401,
        )

    payload = request.get_json(
        silent=True
    )

    if not isinstance(
        payload,
        dict,
    ):
        return api_error(
            "invalid_json",
            (
                "Não foi possível ler "
                "os dados enviados."
            ),
            400,
        )

    password = payload.get(
        "password"
    )

    if (
        not isinstance(
            password,
            str,
        )
        or not user.check_password(
            password
        )
    ):
        return api_error(
            "invalid_credentials",
            "Senha atual incorreta.",
            401,
        )

    try:
        anonymize_account(
            user
        )
    except AccountDeletionBlocked as exc:
        return api_error(
            "ownership_transfer_required",
            str(exc),
            409,
            details={
                "establishments": list(
                    exc.establishments
                ),
            },
        )

    return api_json(
        {
            "deleted": True,
            "anonymized": True,
        },
        cache_control="no-store",
    )
