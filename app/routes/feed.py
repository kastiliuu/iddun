from flask import (
    Blueprint,
    render_template,
    request,
)
from flask_login import (
    current_user,
    login_required,
)

from app.services.client_feed_service import (
    client_feed_context,
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
