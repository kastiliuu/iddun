"""
Curtir, comentar, denunciar e moderar publicações (PR 3).

- Curtida única por pessoa e post (DEC-ID-035; garantida pelo banco).
- Comentário com resposta em um nível; a autora do post oculta, quem
  comentou apaga o próprio (DEC-ID-229, D-SOC-02).
- Denúncia vai para a fila e não apaga nada; o denunciante não recebe
  protocolo nem confirmação (DEC-ID-231, 272, 275 B).
- Moderação pela equipe da plataforma, com histórico (DEC-ID-231, 276).
"""

from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.establishment import (
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.user import UserRole
from app.models.work_post import (
    CommentStatus,
    ContentReport,
    ModerationAction,
    ModerationActionType,
    ReportCategory,
    ReportStatus,
    ReportTarget,
    WorkPost,
    WorkPostAuthorType,
    WorkPostComment,
    WorkPostLike,
    WorkPostStatus,
    utcnow,
)
from app.services.feed_service import public_post_record
from app.services.media_storage import resolve_image_url


MAX_COMMENT_LENGTH = 1000
MAX_REPORT_DESCRIPTION = 1000
COMMENT_PAGE_SIZE = 50


class InteractionError(ValueError):
    """Erro de regra; `code` vira o código da API."""

    def __init__(self, message, code="invalid_request", status=400):
        super().__init__(message)
        self.code = code
        self.status = status


def _not_found():
    return InteractionError("Publicação não encontrada.", "post_not_found", 404)


def _require_user(user):
    if user is None or not getattr(user, "is_authenticated", False) or not user.is_active:
        raise InteractionError(
            "Entre na sua conta para continuar.", "authentication_required", 401
        )


def _visible_post(post_id):
    post = public_post_record(post_id)
    if post is None:
        raise _not_found()
    return post


def manages_post(user, post):
    """Quem pode ocultar comentários do post: a autoria dele (DEC-ID-229)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    if post.author_type == WorkPostAuthorType.CLIENT:
        return user.client_profile is not None and user.client_profile.id == post.client_profile_id

    if post.author_type == WorkPostAuthorType.PROFESSIONAL:
        profile = user.professional_profile
        return profile is not None and profile.id == post.professional_id

    access = db.session.scalar(
        select(EstablishmentUserAccess).where(
            EstablishmentUserAccess.user_id == user.id,
            EstablishmentUserAccess.establishment_id == post.establishment_id,
            EstablishmentUserAccess.status == EstablishmentAccessStatus.ACTIVE,
        )
    )
    return access is not None and (
        access.role == EstablishmentAccessRole.OWNER
        or (post.created_by_user_id is not None and post.created_by_user_id == user.id)
    )


# --------------------------------------------------------------- curtidas


def like_count(post_id):
    return db.session.scalar(
        select(func.count(WorkPostLike.id)).where(WorkPostLike.post_id == post_id)
    ) or 0


def set_like(user, post_id, liked):
    """Idempotente: curtir de novo não duplica; descurtir sem curtida é ok."""
    _require_user(user)
    post = _visible_post(post_id)

    existing = db.session.scalar(
        select(WorkPostLike).where(
            WorkPostLike.post_id == post.id,
            WorkPostLike.user_id == user.id,
        )
    )

    if liked and existing is None:
        db.session.add(WorkPostLike(post_id=post.id, user_id=user.id))
        try:
            db.session.commit()
        except IntegrityError:
            # Outra requisição da mesma pessoa gravou primeiro.
            db.session.rollback()
    elif not liked and existing is not None:
        db.session.delete(existing)
        db.session.commit()

    return {"liked": liked, "likesCount": like_count(post.id)}


# ------------------------------------------------------------ comentários


def _clean_body(value):
    if not isinstance(value, str):
        raise InteractionError("Escreva um comentário.", "invalid_comment")
    clean = value.strip()
    if not clean:
        raise InteractionError("Escreva um comentário.", "invalid_comment")
    if len(clean) > MAX_COMMENT_LENGTH:
        raise InteractionError(
            f"O comentário deve ter no máximo {MAX_COMMENT_LENGTH} caracteres.",
            "invalid_comment",
        )
    return clean


def _author_payload(user):
    profile = user.client_profile
    avatar = profile.avatar_url if profile is not None else None
    return {
        "name": user.name,
        "avatar": resolve_image_url(avatar, external=True) if avatar else None,
    }


def serialize_comment(comment, viewer=None, can_moderate=False, replies=None):
    mine = viewer is not None and getattr(viewer, "is_authenticated", False) and viewer.id == comment.user_id
    payload = {
        "id": str(comment.id),
        "body": comment.body,
        "author": _author_payload(comment.user),
        "createdAt": comment.created_at.isoformat() if comment.created_at else None,
        "parentId": str(comment.parent_id) if comment.parent_id else None,
        "mine": bool(mine),
        "canDelete": bool(mine),
        "canHide": bool(can_moderate and not mine),
    }
    if replies is not None:
        payload["replies"] = replies
    return payload


def list_comments(post_id, viewer=None):
    """Comentários visíveis em ordem de chegada, com as respostas dentro."""
    post = _visible_post(post_id)
    can_moderate = manages_post(viewer, post)

    rows = db.session.scalars(
        select(WorkPostComment)
        .where(
            WorkPostComment.post_id == post.id,
            WorkPostComment.status == CommentStatus.VISIBLE,
        )
        .order_by(WorkPostComment.created_at.asc(), WorkPostComment.id.asc())
    ).all()

    top = [item for item in rows if item.parent_id is None]
    replies = {}
    for item in rows:
        if item.parent_id is not None:
            replies.setdefault(item.parent_id, []).append(item)

    return {
        "items": [
            serialize_comment(
                item,
                viewer,
                can_moderate,
                replies=[
                    serialize_comment(reply, viewer, can_moderate)
                    for reply in replies.get(item.id, [])
                ],
            )
            for item in top
        ],
        "total": len(rows),
        "canModerate": can_moderate,
    }


def add_comment(user, post_id, body, parent_id=None):
    _require_user(user)
    post = _visible_post(post_id)
    clean = _clean_body(body)

    parent = None
    if parent_id not in (None, ""):
        try:
            parent = db.session.get(WorkPostComment, int(parent_id))
        except (TypeError, ValueError):
            parent = None
        if (
            parent is None
            or parent.post_id != post.id
            or parent.status != CommentStatus.VISIBLE
        ):
            raise InteractionError("Comentário não encontrado.", "comment_not_found", 404)
        if parent.parent_id is not None:
            # D-SOC-02: respostas em um nível só.
            raise InteractionError(
                "Responda ao comentário principal.", "reply_depth_exceeded"
            )

    comment = WorkPostComment(
        post_id=post.id,
        user_id=user.id,
        parent_id=parent.id if parent else None,
        body=clean,
        status=CommentStatus.VISIBLE,
    )
    db.session.add(comment)
    db.session.commit()
    return comment


def _comment_on_visible_post(comment_id):
    try:
        comment = db.session.get(WorkPostComment, int(comment_id))
    except (TypeError, ValueError):
        comment = None
    if comment is None or comment.status != CommentStatus.VISIBLE:
        raise InteractionError("Comentário não encontrado.", "comment_not_found", 404)
    post = public_post_record(comment.post_id)
    if post is None:
        raise InteractionError("Comentário não encontrado.", "comment_not_found", 404)
    return comment, post


def delete_comment(user, comment_id):
    """Quem comentou apaga o próprio comentário (as respostas somem junto)."""
    _require_user(user)
    comment, _post = _comment_on_visible_post(comment_id)
    if comment.user_id != user.id:
        raise InteractionError("Comentário não encontrado.", "comment_not_found", 404)
    comment.status = CommentStatus.DELETED
    db.session.commit()
    return comment


def hide_comment(user, comment_id):
    """A autoria do post oculta comentários na própria publicação."""
    _require_user(user)
    comment, post = _comment_on_visible_post(comment_id)
    if not manages_post(user, post):
        raise InteractionError("Comentário não encontrado.", "comment_not_found", 404)
    comment.status = CommentStatus.HIDDEN_BY_AUTHOR
    db.session.commit()
    return comment


def comment_count(post_id):
    return db.session.scalar(
        select(func.count(WorkPostComment.id)).where(
            WorkPostComment.post_id == post_id,
            WorkPostComment.status == CommentStatus.VISIBLE,
        )
    ) or 0


# -------------------------------------------------------------- denúncias


def report_content(user, target_type, target_id, category, description=None):
    """
    Registra a denúncia sem apagar nada. Repetir a mesma denúncia aberta não
    cria outra. Não devolve protocolo (DEC-ID-275 B).
    """
    _require_user(user)

    if target_type not in ReportTarget.VALUES:
        raise InteractionError("Denúncia inválida.", "invalid_report")
    if category not in ReportCategory.VALUES:
        raise InteractionError("Escolha um motivo.", "invalid_report")

    clean_description = None
    if description not in (None, ""):
        if not isinstance(description, str):
            raise InteractionError("Descrição inválida.", "invalid_report")
        clean_description = description.strip()[:MAX_REPORT_DESCRIPTION] or None

    if target_type == ReportTarget.POST:
        post = _visible_post(target_id)
        comment = None
        excerpt = (post.caption or "")[:500] or None
    else:
        comment, post = _comment_on_visible_post(target_id)
        excerpt = comment.body[:500]

    existing = db.session.scalar(
        select(ContentReport).where(
            ContentReport.reporter_user_id == user.id,
            ContentReport.target_type == target_type,
            ContentReport.post_id == post.id,
            (
                ContentReport.comment_id == comment.id
                if comment is not None
                else ContentReport.comment_id.is_(None)
            ),
            ContentReport.status == ReportStatus.OPEN,
        )
    )
    if existing is not None:
        return existing

    report = ContentReport(
        protocol=str(uuid4()),
        reporter_user_id=user.id,
        target_type=target_type,
        post_id=post.id,
        comment_id=comment.id if comment else None,
        target_excerpt=excerpt,
        category=category,
        description=clean_description,
        status=ReportStatus.OPEN,
    )
    db.session.add(report)
    db.session.commit()
    return report


# ------------------------------------------------------------- moderação


def is_moderator(user):
    """DEC-ID-276: moderação é da equipe da plataforma (admin)."""
    return bool(
        user is not None
        and getattr(user, "is_authenticated", False)
        and user.is_active
        and user.role == UserRole.ADMIN
    )


def moderation_queue(status=ReportStatus.OPEN):
    """Denúncias agrupadas por alvo: uma linha por post ou comentário."""
    reports = db.session.scalars(
        select(ContentReport)
        .where(ContentReport.status == status)
        .order_by(ContentReport.created_at.desc(), ContentReport.id.desc())
        .limit(500)
    ).all()

    groups = {}
    for report in reports:
        key = (report.target_type, report.post_id, report.comment_id)
        group = groups.get(key)
        if group is None:
            group = groups[key] = {
                "key": key,
                "target_type": report.target_type,
                "post": report.post,
                "comment": report.comment,
                "excerpt": report.target_excerpt,
                "reports": [],
                "categories": {},
                "latest": report.created_at,
                "lead": report,
            }
        group["reports"].append(report)
        label = ReportCategory.LABELS.get(report.category, report.category)
        group["categories"][label] = group["categories"].get(label, 0) + 1

    return list(groups.values())


def moderation_history(limit=100):
    return db.session.scalars(
        select(ModerationAction)
        .order_by(ModerationAction.created_at.desc(), ModerationAction.id.desc())
        .limit(limit)
    ).all()


def decide_report(moderator, report_id, action, note=None):
    """
    Ocultar, restaurar ou descartar. A decisão vale para todas as denúncias
    abertas do mesmo alvo e fica no histórico.
    """
    if not is_moderator(moderator):
        raise InteractionError("Acesso negado.", "forbidden", 403)
    if action not in (
        ModerationActionType.HIDE,
        ModerationActionType.RESTORE,
        ModerationActionType.DISMISS,
    ):
        raise InteractionError("Ação inválida.", "invalid_action")

    report = db.session.get(ContentReport, report_id)
    if report is None:
        raise InteractionError("Denúncia não encontrada.", "report_not_found", 404)

    clean_note = (note or "").strip()[:500] or None
    post = report.post
    comment = report.comment

    if action == ModerationActionType.HIDE:
        if report.target_type == ReportTarget.COMMENT and comment is not None:
            comment.status = CommentStatus.REMOVED_BY_MODERATION
            recorded = ModerationActionType.REMOVE_COMMENT
        elif post is not None and post.status == WorkPostStatus.PUBLISHED:
            post.status = WorkPostStatus.HIDDEN
            recorded = ModerationActionType.HIDE
        else:
            recorded = ModerationActionType.HIDE
        decided = ReportStatus.ACTIONED
    elif action == ModerationActionType.RESTORE:
        if report.target_type == ReportTarget.COMMENT and comment is not None:
            if comment.status == CommentStatus.REMOVED_BY_MODERATION:
                comment.status = CommentStatus.VISIBLE
        elif post is not None and post.status == WorkPostStatus.HIDDEN:
            post.status = WorkPostStatus.PUBLISHED
        recorded = ModerationActionType.RESTORE
        decided = ReportStatus.DISMISSED
    else:
        recorded = ModerationActionType.DISMISS
        decided = ReportStatus.DISMISSED

    same_target = select(ContentReport).where(
        ContentReport.status == ReportStatus.OPEN,
        ContentReport.target_type == report.target_type,
        ContentReport.post_id == report.post_id,
        (
            ContentReport.comment_id == report.comment_id
            if report.comment_id is not None
            else ContentReport.comment_id.is_(None)
        ),
    )
    now = utcnow()
    for item in db.session.scalars(same_target).all():
        item.status = decided
        item.decided_at = now
        item.decided_by_user_id = moderator.id
        item.decision_note = clean_note

    db.session.add(
        ModerationAction(
            report_id=report.id,
            target_type=report.target_type,
            post_id=report.post_id,
            comment_id=report.comment_id,
            action=recorded,
            moderator_user_id=moderator.id,
            note=clean_note,
        )
    )
    db.session.commit()
    return report

