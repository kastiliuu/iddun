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

from app.services.beauty_graph_service import (
    following_page,
    saved_items,
)
from app.services.client_feed_service import (
    client_feed_context,
    client_feed_page,
)
from app.models.work_post import ReportCategory
from app.services.work_post_service import creator_options


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
        # PR 3: compositor e janela de denúncia.
        composer=creator_options(current_user),
        report_categories=ReportCategory.LABELS,
        **context,
    )



@feed_bp.get("/favoritos")
@login_required
def favorites():
    """Favoritos: quem você segue e o que você salvou (D-SOC-05, 07)."""
    tab = request.args.get("aba", "seguindo")
    if tab not in {"seguindo", "salvos"}:
        tab = "seguindo"

    cursor = request.args.get("cursor", "")
    before = int(cursor) if cursor.isdigit() else None

    following = following_page(
        current_user,
        limit=20,
        before=before if tab == "seguindo" else None,
    )

    # Só itens que continuam públicos entram na lista e na contagem.
    saved = saved_items(current_user)
    saved_total = sum(len(items) for items in saved.values())

    return render_template(
        "feed/favorites.html",
        current_page="favorites",
        tab=tab,
        following=following,
        saved=saved,
        saved_total=saved_total,
        continuing=before is not None and tab == "seguindo",
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
