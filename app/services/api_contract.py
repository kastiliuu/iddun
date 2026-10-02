from flask import jsonify


def api_json(
    payload,
    status=200,
    *,
    cache_control=None,
):
    response = jsonify(payload)
    response.status_code = status

    if cache_control:
        response.headers[
            "Cache-Control"
        ] = cache_control

    return response


def api_error(
    code,
    message,
    status,
    *,
    details=None,
    cache_control="no-store",
):
    error = {
        "code": code,
        "message": message,
    }

    if details is not None:
        error["details"] = details

    return api_json(
        {
            "message": message,
            "error": error,
        },
        status,
        cache_control=cache_control,
    )


def pagination_payload(
    *,
    total,
    offset,
    limit,
):
    next_offset = (
        offset + limit
        if offset + limit < total
        else None
    )

    return {
        "offset": offset,
        "limit": limit,
        "total": total,
        "nextOffset": next_offset,
        "hasMore": next_offset is not None,
    }
