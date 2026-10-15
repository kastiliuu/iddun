from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from app.extensions import db
from app.forms.reputation import BookingReviewForm
from app.models.booking import Booking, BookingStatus, ExperienceSlot
from app.models.reputation import ReviewTarget
from app.models.experience import Experience, ExperienceStatus
from app.services.booking_service import (
    BookingStateError,
    SlotUnavailableError,
    cancel_booking,
    confirm_booking,
    hold_slot,
    release_expired_holds,
)
from app.services.cancellation_request_service import (
    request_cancellation, withdraw_cancellation, execute_cancellation, pending_cancellation,
)
from app.services.reschedule_service import (
    pending_reschedule, eligible_reschedule_slots, request_reschedule,
    withdraw_reschedule, resolve_reschedule,
)
from app.models.no_show_dispute import NoShowDispute
from app.services.no_show_dispute_service import submit_dispute, pending_dispute
from app.services.profile_service import ensure_client_profile
from app.services.google_calendar_service import create_booking_event, delete_booking_event
from app.services.time_service import to_local, utcnow, as_utc
from app.services.reputation_service import ReviewError, get_review, save_booking_reviews


bookings_bp = Blueprint("bookings", __name__)


@bookings_bp.post("/experiencias/<slug>/slots/<int:slot_id>/reservar")
def start_booking(slug, slot_id):
    experience = db.session.scalar(
        select(Experience).where(
            Experience.slug == slug,
            Experience.status == ExperienceStatus.PUBLISHED,
        )
    )
    if experience is None:
        abort(404)

    # The slot ID is user-supplied. Never allow a reservation URL for one
    # experience to hold a slot belonging to another experience.
    slot_belongs_to_experience = db.session.scalar(
        select(ExperienceSlot.id).where(
            ExperienceSlot.id == slot_id,
            ExperienceSlot.experience_id == experience.id,
        )
    )
    if slot_belongs_to_experience is None:
        abort(404)

    if not current_user.is_authenticated:
        flash("Entre na sua conta para reservar esta experiência.", "info")
        return redirect(
            url_for(
                "auth.login",
                next=url_for("public.experience_detail", slug=slug),
            )
        )

    profile = ensure_client_profile(current_user)
    try:
        booking = hold_slot(slot_id, profile)
    except SlotUnavailableError as exc:
        flash(str(exc), "error")
        return redirect(
            url_for("public.experience_detail", slug=slug) + "#horarios"
        )

    return redirect(url_for("bookings.confirm", booking_id=booking.id))


@bookings_bp.route("/reserva/<int:booking_id>/confirmar", methods=["GET", "POST"])
@login_required
def confirm(booking_id):
    profile = ensure_client_profile(current_user)
    release_expired_holds()

    booking = db.session.scalar(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.client_id == profile.id,
        )
    )
    if booking is None:
        abort(404)
    if booking.status == BookingStatus.CONFIRMED:
        return redirect(url_for("bookings.mine"))
    if booking.status != BookingStatus.PENDING:
        flash("Este hold não está mais ativo. Escolha um novo horário.", "info")
        return redirect(url_for("public.experience_detail", slug=booking.experience.slug))

    if request.method == "POST":
        try:
            booking = confirm_booking(booking.id, profile)
        except BookingStateError as exc:
            flash(str(exc), "error")
            return redirect(url_for("public.experience_detail", slug=booking.experience.slug))

        try:
            create_booking_event(booking)
        except Exception:
            # A reserva continua válida mesmo se o provedor externo estiver indisponível.
            flash(
                "Reserva confirmada, mas o Google Calendar não pôde ser atualizado agora.",
                "info",
            )
        else:
            flash("Reserva confirmada. Seu horário está garantido no IDDUN.", "success")
        return redirect(url_for("bookings.mine", confirmada=booking.id))

    local_start = to_local(booking.slot.starts_at, booking.professional.timezone)
    local_end = to_local(booking.slot.ends_at, booking.professional.timezone)
    local_hold = to_local(booking.hold_expires_at, booking.professional.timezone)

    return render_template(
        "bookings/confirm.html",
        booking=booking,
        local_start=local_start,
        local_end=local_end,
        local_hold=local_hold,
        current_page="account",
    )


@bookings_bp.route("/minhas-reservas")
@login_required
def mine():
    profile = ensure_client_profile(current_user)
    release_expired_holds()
    items = db.session.scalars(
        select(Booking)
        .where(Booking.client_id == profile.id)
        .order_by(Booking.created_at.desc())
    ).all()
    from app.models.cancellation_request import CancellationRequest
    from app.models.reschedule_request import RescheduleRequest
    disputes = db.session.scalars(
        select(NoShowDispute)
        .where(NoShowDispute.booking_id.in_([item.id for item in items]))
        .order_by(NoShowDispute.created_at.asc(), NoShowDispute.id.asc())
    ).all() if items else []
    now = utcnow()
    tab = request.args.get("aba", "proximas")
    if tab not in {"proximas", "solicitacoes", "historico"}:
        tab = "proximas"
    status_filter = request.args.get("status", "todos")
    allowed_status = {"todos", "pending", "confirmed", "completed", "cancelled", "no_show"}
    if status_filter not in allowed_status:
        status_filter = "todos"

    cancellation_rows = db.session.scalars(
        select(CancellationRequest)
        .where(CancellationRequest.booking_id.in_([i.id for i in items]))
        .order_by(CancellationRequest.requested_at.asc(), CancellationRequest.id.asc())
    ).all() if items else []
    reschedule_rows = db.session.scalars(
        select(RescheduleRequest)
        .where(RescheduleRequest.booking_id.in_([i.id for i in items]))
        .order_by(RescheduleRequest.requested_at.asc(), RescheduleRequest.id.asc())
    ).all() if items else []
    events = {item.id: [] for item in items}
    for event in cancellation_rows:
        events[event.booking_id].append({
            "at": event.requested_at, "kind": "Cancelamento",
            "description": "Solicitação de cancelamento registrada",
            "status": "pending", "reason": event.reason,
        })
        if event.resolved_at:
            events[event.booking_id].append({
                "at": event.resolved_at, "kind": "Cancelamento",
                "description": {
                    "withdrawn": "Solicitação retirada pelo cliente",
                    "executed": "Cancelamento efetivado pelo executor",
                }.get(event.status, "Solicitação encerrada"),
                "status": event.status, "reason": event.resolution_reason,
            })
    for event in reschedule_rows:
        proposed = to_local(event.requested_slot.starts_at, event.booking.professional.timezone)
        events[event.booking_id].append({
            "at": event.requested_at, "kind": "Reagendamento",
            "description": "Novo horário solicitado: " + proposed.strftime("%d/%m/%Y %H:%M"),
            "status": "pending", "reason": event.reason,
        })
        if event.resolved_at:
            events[event.booking_id].append({
                "at": event.resolved_at, "kind": "Reagendamento",
                "description": {
                    "withdrawn": "Solicitação retirada pelo cliente",
                    "executed": "Novo horário confirmado pelo executor",
                    "rejected": "Solicitação recusada pelo executor",
                }.get(event.status, "Solicitação encerrada"),
                "status": event.status, "reason": event.resolution_reason,
            })
    for dispute in disputes:
        events[dispute.booking_id].append({
            "at": dispute.created_at, "kind": "Contestação de ausência",
            "description": "Contestação registrada — aguardando moderação",
            "status": "pending", "reason": dispute.justification,
        })
        if dispute.resolved_at:
            events[dispute.booking_id].append({
                "at": dispute.resolved_at, "kind": "Contestação de ausência",
                "description": ("Contestação acolhida pela moderação" if dispute.status == "accepted"
                                else "Contestação não acolhida pela moderação"),
                "status": dispute.status, "reason": dispute.resolution_note,
            })
    for item in items:
        events[item.id].append({
            "at": item.created_at, "kind": "Reserva",
            "description": "Reserva iniciada", "status": item.status, "reason": None,
        })
        if item.confirmed_at:
            events[item.id].append({
                "at": item.confirmed_at, "kind": "Reserva",
                "description": "Reserva confirmada", "status": "confirmed", "reason": None,
            })
        if item.cancelled_at:
            events[item.id].append({
                "at": item.cancelled_at, "kind": "Reserva",
                "description": "Reserva cancelada", "status": "cancelled",
                "reason": item.cancellation_reason,
            })
        if item.completed_at:
            events[item.id].append({
                "at": item.completed_at, "kind": "Reserva",
                "description": "Atendimento concluído", "status": "completed", "reason": None,
            })
        if item.no_show_at:
            events[item.id].append({
                "at": item.no_show_at, "kind": "Reserva",
                "description": "Ausência registrada", "status": "no_show", "reason": None,
            })
    for item in items:
        events[item.id].sort(key=lambda entry: as_utc(entry["at"]))

    def _section(item):
        if item.status in {BookingStatus.COMPLETED, BookingStatus.CANCELLED, BookingStatus.NO_SHOW}:
            return "historico"
        if as_utc(item.slot.starts_at) <= now:
            return "historico"
        return "proximas"

    pending_cancel = {i.id: pending_cancellation(i.id) for i in items}
    pending_change = {i.id: pending_reschedule(i.id) for i in items}
    sections = {
        "proximas": [i for i in items if _section(i) == "proximas"],
        "solicitacoes": [i for i in items if pending_cancel[i.id] or pending_change[i.id] or any(d.booking_id == i.id and d.status == "pending" for d in disputes)],
        "historico": [i for i in items if _section(i) == "historico"],
    }
    visible = [
        item for item in sections[tab]
        if status_filter == "todos" or item.status == status_filter
    ]
    rows = [
        {
            "booking": item,
            "local_start": to_local(item.slot.starts_at, item.professional.timezone),
            "local_end": to_local(item.slot.ends_at, item.professional.timezone),
            "timeline": [
                {**event, "local_at": to_local(event["at"], item.professional.timezone)}
                for event in events[item.id]
            ],
            "has_professional_review": any(review.target_type == ReviewTarget.PROFESSIONAL for review in item.reviews),
            "has_establishment_review": any(review.target_type == ReviewTarget.ESTABLISHMENT for review in item.reviews),
        }
        for item in visible
    ]
    confirmed_id = request.args.get("confirmada", type=int)
    confirmed_booking = next(
        (
            item for item in items
            if item.id == confirmed_id and item.status == BookingStatus.CONFIRMED
        ),
        None,
    )
    available_slots = {
        item.id: eligible_reschedule_slots(item)
        for item in visible if item.status == BookingStatus.CONFIRMED
    }
    return render_template(
        "bookings/mine.html",
        confirmed_booking=confirmed_booking,
        rows=rows,
        tab=tab,
        status_filter=status_filter,
        section_counts={key: len(value) for key, value in sections.items()},
        total_bookings=len(items),
        local_alternative_labels={
            slot.id: to_local(slot.starts_at, item.professional.timezone).strftime('%d/%m/%Y %H:%M')
            for item in visible if item.id in available_slots
            for slot in available_slots[item.id]
        },
        BookingStatus=BookingStatus,
        pending_cancellations=pending_cancel,
        pending_reschedules=pending_change,
        disputes_by_booking={item.id: [d for d in disputes if d.booking_id == item.id] for item in visible},
        available_reschedule_slots=available_slots,
        current_page="account",
    )


@bookings_bp.post("/reserva/<int:booking_id>/no-show/contestar")
@login_required
def contest_no_show(booking_id):
    profile = ensure_client_profile(current_user)
    booking = db.session.scalar(
        select(Booking).where(Booking.id == booking_id, Booking.client_id == profile.id)
    )
    if booking is None:
        abort(404)
    try:
        submit_dispute(
            booking, current_user, request.form.get("justificativa"),
            request.form.get("evidencia"),
        )
    except BookingStateError as exc:
        flash(str(exc), "error")
    else:
        flash("Contestação registrada para análise. O status original foi preservado.", "info")
    return redirect(url_for("bookings.mine", aba="solicitacoes"))


@bookings_bp.post("/reserva/<int:booking_id>/cancelar")
@login_required
def cancel(booking_id):
    """Compatibility URL: it requests cancellation, never cancels directly."""
    profile = ensure_client_profile(current_user)
    booking = db.session.scalar(
        select(Booking).where(Booking.id == booking_id, Booking.client_id == profile.id)
    )
    if booking is None:
        abort(404)
    try:
        request_cancellation(booking, current_user, request.form.get("motivo"))
    except BookingStateError as exc:
        flash(str(exc), "error")
    else:
        flash("Solicitação enviada ao profissional. Sua reserva permanece confirmada até a análise.", "info")
    return redirect(url_for("bookings.mine"))


@bookings_bp.post("/reserva/<int:booking_id>/cancelamento/retirar")
@login_required
def withdraw_cancel_request(booking_id):
    profile = ensure_client_profile(current_user)
    booking = db.session.scalar(
        select(Booking).where(Booking.id == booking_id, Booking.client_id == profile.id)
    )
    if booking is None:
        abort(404)
    try:
        withdraw_cancellation(booking, current_user)
    except BookingStateError as exc:
        flash(str(exc), "error")
    else:
        flash("Solicitação retirada. A reserva permanece ativa.", "success")
    return redirect(url_for("bookings.mine"))


@bookings_bp.post("/reserva/<int:booking_id>/cancelamento/efetivar")
@login_required
def execute_cancel_request(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking is None or booking.professional.user_id != current_user.id:
        abort(404)
    try:
        execute_cancellation(booking, current_user, request.form.get("motivo"))
    except BookingStateError as exc:
        flash(str(exc), "error")
    else:
        try:
            delete_booking_event(booking)
        except Exception:
            current_app.logger.warning("Falha ao remover evento booking_id=%s", booking.id, exc_info=True)
        flash("Cancelamento efetivado e registrado.", "success")
    return redirect(url_for("professional.dashboard"))


@bookings_bp.post("/reserva/<int:booking_id>/reagendar")
@login_required
def request_booking_reschedule(booking_id):
    profile = ensure_client_profile(current_user)
    booking = db.session.scalar(
        select(Booking).where(Booking.id == booking_id, Booking.client_id == profile.id)
    )
    if booking is None:
        abort(404)
    try:
        slot_id = int(request.form.get("slot_id") or 0)
        request_reschedule(booking, current_user, slot_id, request.form.get("motivo"))
    except (BookingStateError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        flash("Reagendamento solicitado. Seu horário original continua confirmado até a análise.", "info")
    return redirect(url_for("bookings.mine"))


@bookings_bp.post("/reserva/<int:booking_id>/reagendamento/retirar")
@login_required
def withdraw_booking_reschedule(booking_id):
    profile = ensure_client_profile(current_user)
    booking = db.session.scalar(
        select(Booking).where(Booking.id == booking_id, Booking.client_id == profile.id)
    )
    if booking is None:
        abort(404)
    try:
        withdraw_reschedule(booking, current_user)
    except BookingStateError as exc:
        flash(str(exc), "error")
    else:
        flash("Solicitação retirada. A reserva original não foi alterada.", "success")
    return redirect(url_for("bookings.mine"))


@bookings_bp.post("/reserva/<int:booking_id>/reagendamento/decidir")
@login_required
def decide_booking_reschedule(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking is None or booking.professional.user_id != current_user.id:
        abort(404)
    approve = request.form.get("decision") == "approve"
    try:
        record = resolve_reschedule(
            booking_id, current_user, approve=approve,
            reason=request.form.get("motivo"),
        )
    except BookingStateError as exc:
        flash(str(exc), "error")
    else:
        if record.status == "executed":
            try:
                delete_booking_event(booking, slot=record.original_slot)
                create_booking_event(booking)
            except Exception:
                current_app.logger.warning(
                    "Falha na sincronização do calendário após reagendamento booking_id=%s",
                    booking.id, exc_info=True,
                )
            flash("Reagendamento efetivado com novo horário confirmado.", "success")
        else:
            flash("Solicitação recusada. A reserva original foi mantida.", "info")
    return redirect(url_for("professional.dashboard") + "#solicitacoes-reagendamento")


@bookings_bp.route("/reserva/<int:booking_id>/avaliar", methods=["GET", "POST"])
@login_required
def review(booking_id):
    profile = ensure_client_profile(current_user)
    booking = db.session.scalar(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.client_id == profile.id,
        )
    )
    if booking is None:
        abort(404)
    if booking.status != BookingStatus.COMPLETED:
        flash("A avaliação fica disponível depois que o atendimento for concluído.", "info")
        return redirect(url_for("bookings.mine"))

    form = BookingReviewForm()
    professional_review = get_review(booking.id, ReviewTarget.PROFESSIONAL)
    establishment_review = get_review(booking.id, ReviewTarget.ESTABLISHMENT)

    if request.method == "GET":
        if professional_review:
            form.professional_rating.data = str(professional_review.rating)
            form.professional_recommended.data = "yes" if professional_review.recommended else "no"
            form.professional_comment.data = professional_review.comment
        if establishment_review:
            form.establishment_rating.data = str(establishment_review.rating)
            form.establishment_recommended.data = "yes" if establishment_review.recommended else "no"
            form.establishment_comment.data = establishment_review.comment

    if form.validate_on_submit():
        if booking.establishment is not None:
            establishment_started = bool(
                form.establishment_rating.data
                or form.establishment_recommended.data
                or (form.establishment_comment.data or "").strip()
            )
            if establishment_started and not (form.establishment_rating.data and form.establishment_recommended.data):
                form.establishment_rating.errors.append("Para avaliar o local, escolha estrelas e recomendação.")
            else:
                try:
                    save_booking_reviews(
                        booking=booking,
                        client_profile=profile,
                        professional_rating=form.professional_rating.data,
                        professional_recommended=form.professional_recommended.data,
                        professional_comment=form.professional_comment.data,
                        establishment_rating=form.establishment_rating.data,
                        establishment_recommended=form.establishment_recommended.data,
                        establishment_comment=form.establishment_comment.data,
                    )
                except ReviewError as exc:
                    flash(str(exc), "error")
                else:
                    flash("Sua avaliação verificada foi publicada. Obrigado por fortalecer a comunidade IDDUN.", "success")
                    return redirect(url_for("bookings.mine"))
        else:
            try:
                save_booking_reviews(
                    booking=booking,
                    client_profile=profile,
                    professional_rating=form.professional_rating.data,
                    professional_recommended=form.professional_recommended.data,
                    professional_comment=form.professional_comment.data,
                )
            except ReviewError as exc:
                flash(str(exc), "error")
            else:
                flash("Sua avaliação verificada foi publicada. Obrigado por fortalecer a comunidade IDDUN.", "success")
                return redirect(url_for("bookings.mine"))

    return render_template(
        "bookings/review.html",
        form=form,
        booking=booking,
        professional_review=professional_review,
        establishment_review=establishment_review,
        current_page="account",
    )
