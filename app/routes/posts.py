"""
Publicações na Web (PR 3; D-SOC-08 a 11).

Formulários comuns, com CSRF do Flask-WTF; o JavaScript melhora a
experiência mas nada depende dele. As regras ficam nos serviços, iguais às
da API do app.
"""

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db, limiter
from app.models.work_post import (
    MAX_POST_IMAGES,
    ModerationActionType,
    ReportCategory,
    ReportStatus,
    ReportTarget,
    WorkPost,
    WorkPostStatus,
)
from app.services.feed_service import (
    interaction_counts,
    public_post_record,
    serialize_work_post,
)
from app.services.media_service import UploadBatch, delete_uploaded_file
from app.services.post_interactions import (
    InteractionError,
    add_comment,
    decide_report,
    delete_comment,
    hide_comment,
    is_moderator,
    list_comments,
    moderation_history,
    moderation_queue,
    report_content,
    set_like,
)
from app.services.work_post_service import (
    WorkPostError,
    create_work_post,
    delete_work_post,
)
from app.utils.admin import admin_required


posts_bp = Blueprint("posts", __name__)


def _safe_next(default):
    target = request.form.get("next") or request.args.get("next") or ""
    if target.startswith("/") and not target.startswith("//"):
        return target
    return default


def _wants_json():
    return request.accept_mimetypes.best == "application/json"


def _go(target):
    """Com JavaScript o compositor recebe o destino; sem ele, redireciona.
    Assim a mensagem (flash) aparece na página certa, não no fetch."""
    if _wants_json():
        return {"redirect": target}
    return redirect(target)


def _parse_author(value):
    try:
        kind, raw_id = (value or "").split(":", 1)
        return kind, int(raw_id)
    except (TypeError, ValueError):
        raise WorkPostError("Escolha como publicar.")


@posts_bp.post("/publicacoes/nova")
@login_required
@limiter.limit("40 per hour")
@limiter.limit("30 per day")
def create():
    """Compositor do feed: texto, foto única ou carrossel até 10 (DEC-ID-225)."""
    files = [
        item for item in request.files.getlist("images") if getattr(item, "filename", "")
    ]
    alt_texts = request.form.getlist("alt_texts")

    try:
        if len(files) > MAX_POST_IMAGES:
            raise WorkPostError(f"Uma publicação pode ter até {MAX_POST_IMAGES} imagens.")

        author_type, author_id = _parse_author(request.form.get("author"))

        with UploadBatch() as uploads:
            images = [
                {
                    "image_url": uploads.save_image(item, "work-posts"),
                    "alt_text": alt_texts[index] if index < len(alt_texts) else None,
                }
                for index, item in enumerate(files)
            ]
            post = create_work_post(
                user=current_user,
                author_type=author_type,
                author_id=author_id,
                images=images,
                caption=request.form.get("caption"),
                experience_id=request.form.get("experience_id") or None,
            )
            uploads.commit()
    except (WorkPostError, ValueError) as exc:
        db.session.rollback()
        flash(str(exc), "error")
        return _go(url_for("feed.home") + "#post-composer")
    except (OSError, SQLAlchemyError):
        db.session.rollback()
        flash("Não foi possível publicar agora. Tente de novo.", "error")
        return _go(url_for("feed.home") + "#post-composer")

    flash("Sua publicação está no ar.", "success")
    return _go(url_for("feed.home") + f"#post-{post.id}")


def _viewable_post(post_id):
    """Público para todos; ocultado pela moderação só para a equipe."""
    post = public_post_record(post_id)
    if post is not None:
        return post, False

    post = db.session.get(WorkPost, post_id)
    if post is not None and post.status == WorkPostStatus.HIDDEN and is_moderator(current_user):
        return post, True

    abort(404)


@posts_bp.get("/publicacoes/<int:post_id>")
def detail(post_id):
    """Página pública da publicação, com comentários (DEC-ID-230)."""
    post, under_review = _viewable_post(post_id)
    viewer = current_user if current_user.is_authenticated else None
    payload = serialize_work_post(post, counts=interaction_counts([post.id], viewer))

    comments = {"items": [], "total": 0, "canModerate": False}
    if not under_review:
        comments = list_comments(post.id, viewer)

    return render_template(
        "posts/detail.html",
        post=payload,
        comments=comments,
        under_review=under_review,
        report_categories=ReportCategory.LABELS,
        current_page="feed",
    )


@posts_bp.post("/publicacoes/<int:post_id>/remover")
@login_required
def remove(post_id):
    """D-SOC-09: remoção lógica; as imagens saem do armazenamento."""
    try:
        paths = delete_work_post(user=current_user, post_id=post_id)
    except WorkPostError:
        abort(404)

    for path in paths:
        delete_uploaded_file(path)

    flash("Publicação removida.", "success")
    return redirect(url_for("feed.home"))


@posts_bp.post("/publicacoes/<int:post_id>/curtida")
@login_required
@limiter.limit("300 per hour")
def toggle_like(post_id):
    """Sem JavaScript: alterna a curtida e volta para onde estava."""
    try:
        set_like(current_user, post_id, request.form.get("liked") == "true")
    except InteractionError as exc:
        abort(exc.status)
    return redirect(_safe_next(url_for("posts.detail", post_id=post_id)))


@posts_bp.post("/publicacoes/<int:post_id>/comentarios")
@login_required
@limiter.limit("30 per hour")
def comment(post_id):
    try:
        created = add_comment(
            current_user,
            post_id,
            request.form.get("body"),
            request.form.get("parent_id"),
        )
    except InteractionError as exc:
        if exc.status == 404 and exc.code == "post_not_found":
            abort(404)
        flash(str(exc), "error")
        return redirect(url_for("posts.detail", post_id=post_id) + "#comentarios")

    return redirect(url_for("posts.detail", post_id=post_id) + f"#comentario-{created.id}")


@posts_bp.post("/comentarios/<int:comment_id>/apagar")
@login_required
def delete_own_comment(comment_id):
    try:
        removed = delete_comment(current_user, comment_id)
    except InteractionError:
        abort(404)
    return redirect(url_for("posts.detail", post_id=removed.post_id) + "#comentarios")


@posts_bp.post("/comentarios/<int:comment_id>/ocultar")
@login_required
def hide_post_comment(comment_id):
    try:
        hidden = hide_comment(current_user, comment_id)
    except InteractionError:
        abort(404)
    return redirect(url_for("posts.detail", post_id=hidden.post_id) + "#comentarios")


@posts_bp.post("/denuncias")
@login_required
@limiter.limit("20 per hour")
def report():
    """
    DEC-ID-275 B: sem protocolo nem confirmação. Com JavaScript a janela só
    fecha; sem ele, a pessoa volta para a página de onde veio.
    """
    target_type = request.form.get("target_type")
    try:
        report_content(
            current_user,
            target_type,
            request.form.get("target_id"),
            request.form.get("category"),
            request.form.get("description"),
        )
    except InteractionError as exc:
        if _wants_json():
            return {"error": {"code": exc.code, "message": str(exc)}}, exc.status
        abort(exc.status if exc.status in (400, 404) else 400)

    if _wants_json():
        return "", 204
    return redirect(_safe_next(url_for("feed.home")))


# ----------------------------------------------------------- moderação


@posts_bp.get("/admin/moderacao")
@admin_required
def moderation():
    """Fila da equipe IDDUN (DEC-ID-231, 276): Abertas e Decididas."""
    tab = request.args.get("aba", "abertas")
    return render_template(
        "admin/moderation.html",
        tab=tab,
        groups=moderation_queue(ReportStatus.OPEN) if tab != "decididas" else [],
        history=moderation_history() if tab == "decididas" else [],
        admin_section="moderation",
        actions=ModerationActionType,
        targets=ReportTarget,
    )


@posts_bp.post("/admin/moderacao/<int:report_id>")
@admin_required
def moderation_decide(report_id):
    try:
        decide_report(
            current_user,
            report_id,
            request.form.get("action"),
            request.form.get("note"),
        )
    except InteractionError as exc:
        flash(str(exc), "error")
    else:
        flash("Decisão registrada.", "success")
    return redirect(url_for("posts.moderation", aba=request.form.get("aba", "abertas")))
