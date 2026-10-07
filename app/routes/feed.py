from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
)
from flask_login import (
    current_user,
    login_required,
)

from app.services.client_feed_service import (
    client_feed_context,
    client_feed_page,
)


feed_bp = Blueprint(
    "feed",
    __name__,
)


@feed_bp.get("/feed")
@login_required
def home():
    mode = request.args.get(
        "mode",
        "for-you",
    )

    if mode not in {
        "for-you",
        "following",
    }:
        mode = "for-you"

    context = client_feed_context(
        current_user,
        mode=mode,
    )

    return render_template(
        "feed/index.html",
        current_page="feed",
        **context,
    )



@feed_bp.get("/feed/mais")
@login_required
def more():
    mode = request.args.get(
        "mode",
        "for-you",
    )

    if mode not in {
        "for-you",
        "following",
    }:
        mode = "for-you"

    cursor = request.args.get(
        "cursor"
    )

    page = client_feed_page(
        current_user,
        mode=mode,
        cursor=cursor,
        limit=20,
    )

    html = render_template(
        "feed/_cards.html",
        feed_items=page[
            "feed_items"
        ],
        followed_keys=page[
            "followed_keys"
        ],
        saved_keys=page[
            "saved_keys"
        ],
    )

    response = jsonify(
        {
            "html": html,
            "nextCursor":
                page[
                    "next_cursor"
                ],
        }
    )
    response.headers[
        "Cache-Control"
    ] = "private, no-store"

    return response
