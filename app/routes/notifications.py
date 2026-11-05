"""Central de notificações na Web (PR 6a; DEC-ID-215–223; D-SOC-22).

- /notificacoes: abas Todas, Reservas, Social e Profissional e Empresa,
  filtro Só não lidas e Ver mais.
- Abrir um aviso marca como lido e leva ao destino só se o acesso ainda
  vale (DEC-ID-220, 221). Abrir a central não marca nada.
- Marcar como lida (um) e Marcar todas como lidas são ações explícitas.
"""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.notification import Notification
from app.services.time_service import to_local
from app.services.notification_center import TABS, category_counts, context_label, destination
from app.services.notification_service import (
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    notification_preferences,
)

notifications_bp = Blueprint("notifications", __name__)

PAGE = 20
MAX_PAGES = 10


def _own(notification_id):
    notification = db.session.get(Notification, notification_id)
    if notification is None or notification.user_id != current_user.id:
        abort(404)
    return notification


def _back():
    """Volta para a mesma aba e filtro, se vierem do formulário."""
    params = {}
    tab = request.form.get("aba") or request.args.get("aba")
    if tab in TABS and tab != "todas":
        params["aba"] = tab
    if (request.form.get("nao_lidas") or request.args.get("nao_lidas")) == "1":
        params["nao_lidas"] = "1"
    return url_for("notifications.center", **params)


@notifications_bp.get("/notificacoes")
@login_required
def center():
    tab = request.args.get("aba", "todas")
    if tab not in TABS:
        tab = "todas"
    unread_only = request.args.get("nao_lidas") == "1"
    pages = max(1, min(request.args.get("mais", 1, type=int) or 1, MAX_PAGES))

    rows, total, unread_count = list_notifications(
        current_user,
        limit=PAGE * pages,
        unread_only=unread_only,
        category=TABS[tab][0],
    )
    items = [
        {
            "notification": item,
            "context": context_label(current_user, item),
            "when": to_local(item.created_at).strftime("%d/%m · %H:%M"),
        }
        for item in rows
    ]

    def center_url(**changes):
        params = {"aba": tab, "nao_lidas": "1" if unread_only else ""}
        params.update(changes)
        params = {
            key: value
            for key, value in params.items()
            if value not in (None, "", "todas", 1)
        }
        return url_for("notifications.center", **params)

    return render_template(
        "notifications/center.html",
        tabs=TABS,
        tab=tab,
        unread_only=unread_only,
        items=items,
        total=total,
        unread_count=unread_count,
        counts=category_counts(current_user, unread_only=unread_only),
        has_more=total > len(rows) and pages < MAX_PAGES,
        pages=pages,
        preference=notification_preferences(current_user),
        center_url=center_url,
        current_page="notifications",
    )


@notifications_bp.get("/notificacoes/<int:notification_id>/abrir")
@login_required
def open_notification(notification_id):
    """DEC-ID-220: abrir marca como lido; o destino é revalidado agora."""
    notification = _own(notification_id)
    mark_notification_read(current_user, notification.id)
    target = destination(current_user, notification)
    if target is None:
        flash("Este aviso não leva a um conteúdo disponível para você agora.", "info")
        return redirect(url_for("notifications.center"))
    return redirect(target)


@notifications_bp.post("/notificacoes/<int:notification_id>/lida")
@login_required
def mark_read(notification_id):
    notification = _own(notification_id)
    mark_notification_read(current_user, notification.id)
    return redirect(_back())


@notifications_bp.post("/notificacoes/lidas")
@login_required
def mark_all_read():
    changed = mark_all_notifications_read(current_user)
    flash(
        "Todas as notificações foram marcadas como lidas." if changed else "Não havia notificações novas.",
        "success",
    )
    return redirect(_back())


@notifications_bp.post("/notificacoes/preferencias")
@login_required
def preferences():
    """DEC-ID-218: Social e Profissional/Empresa opcionais; Reservas essenciais."""
    preference = notification_preferences(current_user)
    preference.social_enabled = request.form.get("social") == "1"
    preference.work_enabled = request.form.get("profissional") == "1"
    db.session.commit()
    flash("Preferências de notificação salvas.", "success")
    return redirect(url_for("notifications.center", _anchor="preferencias"))
