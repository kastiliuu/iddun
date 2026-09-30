from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import func, select

from app.extensions import db
from app.forms.admin import (
    EstablishmentForm,
    ExperienceForm,
    MembershipForm,
    OpportunityBatchForm,
    ProfessionalForm,
)
from app.models.establishment import Establishment, ProfessionalEstablishmentMembership
from app.models.booking import Booking, BookingStatus, ExperienceSlot, SlotStatus
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.services.admin_catalog_service import (
    dashboard_counts,
    establishment_choices,
    experience_choices,
    publish_experience,
    professional_choices,
    save_membership,
    validate_experience_publication,
)
from app.services.slug_service import public_handle_available, unique_public_handle, unique_slug
from app.services.media_service import save_uploaded_image
from app.services.google_calendar_service import delete_booking_event, sync_professional_if_stale
from app.services.booking_service import (
    block_slot_manual,
    cancel_booking,
    clear_external_conflict,
    create_slots_batch,
    mark_external_conflict,
    refresh_slot,
)
from app.services.time_service import to_local, utcnow
from app.utils.admin import admin_required


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _clean(value):
    return (value or "").strip() or None


def _state(value):
    cleaned = _clean(value)
    return cleaned.upper() if cleaned else None


def _focus_percent(value, default=50):
    try:
        parsed = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(0, min(100, parsed))


def _public_handle(form_field, fallback, resource_type, current_id=None):
    raw = (form_field.data or "").strip()
    if not raw:
        return unique_public_handle(fallback, resource_type=resource_type, current_id=current_id)
    candidate = unique_public_handle(raw, resource_type=resource_type, current_id=current_id)
    # Manual choices should never be silently renamed.
    from app.services.slug_service import slugify
    normalized = slugify(raw)
    available, message = public_handle_available(
        normalized, resource_type=resource_type, current_id=current_id
    )
    if not available:
        form_field.errors.append(message or "Este endereço não está disponível.")
        return None
    return normalized


def _set_experience_choices(form):
    form.professional_id.choices = professional_choices()
    form.establishment_id.choices = establishment_choices(include_empty=True)


def _set_experience_cutoff_help(form):
    professional_id = form.professional_id.data
    professional = db.session.get(ProfessionalProfile, professional_id) if professional_id else None
    if professional:
        form.booking_cutoff_minutes.description = (
            f"Se ficar vazio, usa o padrão de {professional.default_booking_cutoff_minutes} min "
            f"de {professional.display_name}."
        )
    else:
        form.booking_cutoff_minutes.description = (
            "Opcional. Se ficar vazio, o IDDUN usa a antecedência padrão do profissional escolhido."
        )


def _experience_status_is_valid(form):
    """(a) Bloqueia no formulário uma publicação invisível no catálogo."""
    if form.status.data != ExperienceStatus.PUBLISHED:
        return True

    try:
        validate_experience_publication(
            professional_id=form.professional_id.data,
            establishment_id=form.establishment_id.data or None,
        )
    except ValueError as exc:
        form.status.errors.append(str(exc))
        return False

    return True


def _set_membership_choices(form):
    form.professional_id.choices = professional_choices()
    form.establishment_id.choices = establishment_choices()


@admin_bp.route("/")
@admin_required
def dashboard():
    recent_experiences = db.session.scalars(
        select(Experience).order_by(Experience.created_at.desc()).limit(6)
    ).all()
    recent_professionals = db.session.scalars(
        select(ProfessionalProfile).order_by(ProfessionalProfile.created_at.desc()).limit(5)
    ).all()
    return render_template(
        "admin/dashboard.html",
        counts=dashboard_counts(),
        recent_experiences=recent_experiences,
        recent_professionals=recent_professionals,
        admin_section="dashboard",
    )


@admin_bp.route("/estabelecimentos")
@admin_required
def establishments():
    items = db.session.scalars(
        select(Establishment).order_by(Establishment.created_at.desc())
    ).all()
    return render_template(
        "admin/establishments/list.html",
        establishments=items,
        admin_section="establishments",
    )


@admin_bp.route("/estabelecimentos/novo", methods=["GET", "POST"])
@admin_required
def establishment_create():
    form = EstablishmentForm()
    if request.method == "GET":
        form.is_active.data = True

    if form.validate_on_submit():
        handle = _public_handle(form.slug, form.name.data, "establishment")
        if handle is None:
            return render_template(
                "admin/establishments/form.html", form=form, item=None, admin_section="establishments"
            )
        try:
            logo_url = save_uploaded_image(form.logo_file.data, "establishments")
        except ValueError as exc:
            form.logo_file.errors.append(str(exc))
            return render_template(
                "admin/establishments/form.html", form=form, item=None, admin_section="establishments"
            )
        item = Establishment(
            name=form.name.data.strip(),
            slug=handle,
            description=_clean(form.description.data),
            phone=_clean(form.phone.data),
            email=_clean(form.email.data.lower() if form.email.data else None),
            instagram=_clean(form.instagram.data),
            address_line1=_clean(form.address_line1.data),
            address_line2=_clean(form.address_line2.data),
            neighborhood=_clean(form.neighborhood.data),
            city=_clean(form.city.data),
            state=_state(form.state.data),
            postal_code=_clean(form.postal_code.data),
            logo_url=logo_url,
            timezone=form.timezone.data,
            is_verified=form.is_verified.data,
            is_active=form.is_active.data,
        )
        db.session.add(item)
        db.session.commit()
        flash("Estabelecimento criado com sucesso.", "success")
        return redirect(url_for("admin.establishments"))

    return render_template(
        "admin/establishments/form.html",
        form=form,
        item=None,
        admin_section="establishments",
    )


@admin_bp.route("/estabelecimentos/<int:item_id>/editar", methods=["GET", "POST"])
@admin_required
def establishment_edit(item_id):
    item = db.session.get(Establishment, item_id) or abort(404)
    form = EstablishmentForm(obj=item)

    if form.validate_on_submit():
        handle = _public_handle(form.slug, form.name.data, "establishment", current_id=item.id)
        if handle is None:
            return render_template(
                "admin/establishments/form.html", form=form, item=item, admin_section="establishments"
            )
        try:
            uploaded_logo = save_uploaded_image(form.logo_file.data, "establishments")
        except ValueError as exc:
            form.logo_file.errors.append(str(exc)
            )
            return render_template(
                "admin/establishments/form.html", form=form, item=item, admin_section="establishments"
            )
        item.name = form.name.data.strip()
        item.slug = handle
        item.description = _clean(form.description.data)
        item.phone = _clean(form.phone.data)
        item.email = _clean(form.email.data.lower() if form.email.data else None)
        item.instagram = _clean(form.instagram.data)
        item.address_line1 = _clean(form.address_line1.data)
        item.address_line2 = _clean(form.address_line2.data)
        item.neighborhood = _clean(form.neighborhood.data)
        item.city = _clean(form.city.data)
        item.state = _state(form.state.data)
        item.postal_code = _clean(form.postal_code.data)
        if uploaded_logo:
            item.logo_url = uploaded_logo
        item.timezone = form.timezone.data
        item.is_verified = form.is_verified.data
        item.is_active = form.is_active.data
        db.session.commit()
        flash("Estabelecimento atualizado.", "success")
        return redirect(url_for("admin.establishments"))

    return render_template(
        "admin/establishments/form.html",
        form=form,
        item=item,
        admin_section="establishments",
    )


@admin_bp.route("/estabelecimentos/<int:item_id>/dashboard")
@admin_required
def establishment_dashboard(item_id):
    item = db.session.get(Establishment, item_id) or abort(404)
    active_memberships = [m for m in item.memberships if m.status == "active"]
    experiences = list(item.experiences)
    bookings = list(item.bookings)
    counts = {
        "professionals": len(active_memberships),
        "experiences": len(experiences),
        "available_slots": sum(1 for slot in item.slots if slot.status == SlotStatus.AVAILABLE),
        "confirmed_bookings": sum(1 for booking in bookings if booking.status == BookingStatus.CONFIRMED),
    }
    upcoming_items = sorted(
        [booking for booking in bookings if booking.status == BookingStatus.CONFIRMED],
        key=lambda booking: booking.slot.starts_at,
    )[:6]
    upcoming = [
        {
            "booking": booking,
            "local_start": to_local(booking.slot.starts_at, booking.professional.timezone),
        }
        for booking in upcoming_items
    ]
    return render_template(
        "admin/establishments/dashboard.html",
        item=item,
        counts=counts,
        active_memberships=active_memberships,
        upcoming=upcoming,
        admin_section="establishments",
    )


@admin_bp.route("/profissionais")
@admin_required
def professionals():
    items = db.session.scalars(
        select(ProfessionalProfile).order_by(ProfessionalProfile.created_at.desc())
    ).all()
    return render_template(
        "admin/professionals/list.html",
        professionals=items,
        admin_section="professionals",
    )


@admin_bp.route("/profissionais/novo", methods=["GET", "POST"])
@admin_required
def professional_create():
    form = ProfessionalForm()
    if request.method == "GET":
        form.is_active.data = True

    if form.validate_on_submit():
        handle = _public_handle(form.slug, form.display_name.data, "professional")
        if handle is None:
            return render_template(
                "admin/professionals/form.html", form=form, item=None, admin_section="professionals"
            )
        try:
            avatar_url = save_uploaded_image(form.avatar_file.data, "professionals")
        except ValueError as exc:
            form.avatar_file.errors.append(str(exc))
            return render_template(
                "admin/professionals/form.html", form=form, item=None, admin_section="professionals"
            )
        item = ProfessionalProfile(
            display_name=form.display_name.data.strip(),
            slug=handle,
            bio=_clean(form.bio.data),
            primary_specialty=_clean(form.primary_specialty.data),
            phone=_clean(form.phone.data),
            instagram=_clean(form.instagram.data),
            city=_clean(form.city.data),
            state=_state(form.state.data),
            avatar_url=avatar_url,
            avatar_focus_x=_focus_percent(form.avatar_focus_x.data),
            avatar_focus_y=_focus_percent(form.avatar_focus_y.data),
            timezone=form.timezone.data,
            default_booking_cutoff_minutes=form.default_booking_cutoff_minutes.data,
            is_verified=form.is_verified.data,
            is_active=form.is_active.data,
        )
        db.session.add(item)
        db.session.commit()
        flash("Profissional cadastrado com sucesso.", "success")
        return redirect(url_for("admin.professionals"))

    return render_template(
        "admin/professionals/form.html",
        form=form,
        item=None,
        admin_section="professionals",
    )


@admin_bp.route("/profissionais/<int:item_id>/editar", methods=["GET", "POST"])
@admin_required
def professional_edit(item_id):
    item = db.session.get(ProfessionalProfile, item_id) or abort(404)
    form = ProfessionalForm(obj=item)

    if form.validate_on_submit():
        handle = _public_handle(form.slug, form.display_name.data, "professional", current_id=item.id)
        if handle is None:
            return render_template(
                "admin/professionals/form.html", form=form, item=item, admin_section="professionals"
            )
        try:
            uploaded_avatar = save_uploaded_image(form.avatar_file.data, "professionals")
        except ValueError as exc:
            form.avatar_file.errors.append(str(exc))
            return render_template(
                "admin/professionals/form.html", form=form, item=item, admin_section="professionals"
            )
        item.display_name = form.display_name.data.strip()
        item.slug = handle
        item.bio = _clean(form.bio.data)
        item.primary_specialty = _clean(form.primary_specialty.data)
        item.phone = _clean(form.phone.data)
        item.instagram = _clean(form.instagram.data)
        item.city = _clean(form.city.data)
        item.state = _state(form.state.data)
        if uploaded_avatar:
            item.avatar_url = uploaded_avatar
        item.avatar_focus_x = _focus_percent(form.avatar_focus_x.data, 50 if item.avatar_focus_x is None else item.avatar_focus_x)
        item.avatar_focus_y = _focus_percent(form.avatar_focus_y.data, 50 if item.avatar_focus_y is None else item.avatar_focus_y)
        item.timezone = form.timezone.data
        item.default_booking_cutoff_minutes = form.default_booking_cutoff_minutes.data
        item.is_verified = form.is_verified.data
        item.is_active = form.is_active.data
        db.session.commit()
        flash("Profissional atualizado.", "success")
        return redirect(url_for("admin.professionals"))

    return render_template(
        "admin/professionals/form.html",
        form=form,
        item=item,
        admin_section="professionals",
    )


@admin_bp.route("/vinculos")
@admin_required
def memberships():
    items = db.session.scalars(
        select(ProfessionalEstablishmentMembership)
        .order_by(ProfessionalEstablishmentMembership.created_at.desc())
    ).all()
    return render_template(
        "admin/memberships/list.html",
        memberships=items,
        admin_section="memberships",
    )


@admin_bp.route("/vinculos/novo", methods=["GET", "POST"])
@admin_required
def membership_create():
    form = MembershipForm()
    _set_membership_choices(form)

    if not form.professional_id.choices or not form.establishment_id.choices:
        flash("Cadastre ao menos um profissional e um estabelecimento antes de criar um vínculo.", "info")

    if form.validate_on_submit():
        item = ProfessionalEstablishmentMembership(
            professional_id=form.professional_id.data,
            establishment_id=form.establishment_id.data,
            role_name=_clean(form.role_name.data),
            status=form.status.data,
            is_primary=form.is_primary.data,
            started_at=form.started_at.data,
            ended_at=form.ended_at.data,
        )
        try:
            save_membership(item)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
        else:
            flash("Vínculo profissional criado.", "success")
            return redirect(url_for("admin.memberships"))

    return render_template(
        "admin/memberships/form.html",
        form=form,
        item=None,
        admin_section="memberships",
    )


@admin_bp.route("/vinculos/<int:item_id>/editar", methods=["GET", "POST"])
@admin_required
def membership_edit(item_id):
    item = db.session.get(ProfessionalEstablishmentMembership, item_id) or abort(404)
    form = MembershipForm(obj=item)
    _set_membership_choices(form)

    if form.validate_on_submit():
        item.professional_id = form.professional_id.data
        item.establishment_id = form.establishment_id.data
        item.role_name = _clean(form.role_name.data)
        item.status = form.status.data
        item.is_primary = form.is_primary.data
        item.started_at = form.started_at.data
        item.ended_at = form.ended_at.data
        try:
            save_membership(item)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
        else:
            flash("Vínculo atualizado.", "success")
            return redirect(url_for("admin.memberships"))

    return render_template(
        "admin/memberships/form.html",
        form=form,
        item=item,
        admin_section="memberships",
    )


@admin_bp.route("/experiencias")
@admin_required
def experiences():
    items = db.session.scalars(
        select(Experience).order_by(Experience.created_at.desc())
    ).all()
    return render_template(
        "admin/experiences/list.html",
        experiences=items,
        ExperienceStatus=ExperienceStatus,
        admin_section="experiences",
    )


@admin_bp.route("/experiencias/nova", methods=["GET", "POST"])
@admin_required
def experience_create():
    form = ExperienceForm()
    _set_experience_choices(form)
    _set_experience_cutoff_help(form)

    if request.method == "GET":
        form.status.data = ExperienceStatus.DRAFT

    if not form.professional_id.choices:
        flash("Cadastre um profissional antes de criar uma experiência.", "info")

    if form.validate_on_submit() and _experience_status_is_valid(form):
        try:
            image_url = save_uploaded_image(form.image_file.data, "experiences")
        except ValueError as exc:
            form.image_file.errors.append(str(exc))
            return render_template(
                "admin/experiences/form.html", form=form, item=None, admin_section="experiences"
            )
        establishment_id = form.establishment_id.data or None
        item = Experience(
            professional_id=form.professional_id.data,
            establishment_id=establishment_id,
            title=form.title.data.strip(),
            slug=unique_slug(Experience, form.slug.data or form.title.data),
            category=form.category.data,
            short_description=form.short_description.data.strip(),
            description=_clean(form.description.data),
            badge=_clean(form.badge.data),
            image_url=image_url,
            image_focus_x=_focus_percent(form.image_focus_x.data),
            image_focus_y=_focus_percent(form.image_focus_y.data),
            regular_price=form.regular_price.data,
            price=form.price.data,
            duration_minutes=form.duration_minutes.data,
            booking_cutoff_minutes=form.booking_cutoff_minutes.data,
            status=form.status.data,
            is_featured=form.is_featured.data,
            is_first_experience=False,
        )
        db.session.add(item)
        db.session.commit()
        flash("Experiência criada com sucesso.", "success")
        return redirect(url_for("admin.experiences"))

    return render_template(
        "admin/experiences/form.html",
        form=form,
        item=None,
        admin_section="experiences",
    )


@admin_bp.route("/experiencias/<int:item_id>/editar", methods=["GET", "POST"])
@admin_required
def experience_edit(item_id):
    item = db.session.get(Experience, item_id) or abort(404)
    form = ExperienceForm(obj=item)
    _set_experience_choices(form)
    _set_experience_cutoff_help(form)

    if form.validate_on_submit() and _experience_status_is_valid(form):
        try:
            uploaded_image = save_uploaded_image(form.image_file.data, "experiences")
        except ValueError as exc:
            form.image_file.errors.append(str(exc))
            return render_template(
                "admin/experiences/form.html", form=form, item=item, admin_section="experiences"
            )

        item.professional_id = form.professional_id.data
        item.establishment_id = form.establishment_id.data or None
        item.title = form.title.data.strip()
        item.slug = unique_slug(Experience, form.slug.data or form.title.data, current_id=item.id)
        item.category = form.category.data
        item.short_description = form.short_description.data.strip()
        item.description = _clean(form.description.data)
        item.badge = _clean(form.badge.data)
        if uploaded_image:
            item.image_url = uploaded_image
        item.image_focus_x = _focus_percent(form.image_focus_x.data, 50 if item.image_focus_x is None else item.image_focus_x)
        item.image_focus_y = _focus_percent(form.image_focus_y.data, 50 if item.image_focus_y is None else item.image_focus_y)
        item.regular_price = form.regular_price.data
        item.price = form.price.data
        item.duration_minutes = form.duration_minutes.data
        item.booking_cutoff_minutes = form.booking_cutoff_minutes.data
        item.status = form.status.data
        item.is_featured = form.is_featured.data
        item.is_first_experience = False
        db.session.commit()
        flash("Experiência atualizada.", "success")
        return redirect(url_for("admin.experiences"))

    return render_template(
        "admin/experiences/form.html",
        form=form,
        item=item,
        admin_section="experiences",
    )


@admin_bp.post("/experiencias/<int:item_id>/publicar")
@admin_required
def experience_publish(item_id):
    item = db.session.get(Experience, item_id) or abort(404)
    try:
        publish_experience(item)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "error")
    else:
        flash(f"{item.title} está publicada no marketplace.", "success")
    return redirect(url_for("admin.experiences"))


@admin_bp.post("/experiencias/<int:item_id>/pausar")
@admin_required
def experience_pause(item_id):
    item = db.session.get(Experience, item_id) or abort(404)
    item.status = ExperienceStatus.PAUSED
    db.session.commit()
    flash(f"{item.title} foi pausada.", "info")
    return redirect(url_for("admin.experiences"))


@admin_bp.route("/oportunidades")
@admin_required
def opportunities():
    slots = db.session.scalars(
        select(ExperienceSlot).order_by(ExperienceSlot.starts_at.asc())
    ).all()
    for slot in slots:
        refresh_slot(slot)
    db.session.commit()
    rows = [
        {
            "slot": slot,
            "local_start": to_local(slot.starts_at, slot.professional.timezone),
            "local_end": to_local(slot.ends_at, slot.professional.timezone),
        }
        for slot in slots
    ]
    return render_template(
        "admin/opportunities/list.html",
        rows=rows,
        SlotStatus=SlotStatus,
        admin_section="opportunities",
    )


@admin_bp.route("/oportunidades/nova", methods=["GET", "POST"])
@admin_required
def opportunity_create():
    form = OpportunityBatchForm()
    form.experience_id.choices = experience_choices(published_only=False)

    if not form.experience_id.choices:
        flash("Crie uma experiência antes de publicar oportunidades.", "info")

    if form.validate_on_submit():
        experience = db.session.get(Experience, form.experience_id.data) or abort(404)
        try:
            created = create_slots_batch(
                experience,
                form.slot_date.data,
                form.times.data,
                cutoff_minutes=form.booking_cutoff_minutes.data,
            )
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
        else:
            sync_professional_if_stale(experience.professional_id, stale_after_seconds=0)
            flash(f"{len(created)} oportunidade(s) publicada(s) com sucesso.", "success")
            return redirect(url_for("admin.opportunities"))

    return render_template(
        "admin/opportunities/form.html",
        form=form,
        admin_section="opportunities",
    )


@admin_bp.post("/oportunidades/<int:slot_id>/bloquear")
@admin_required
def opportunity_block(slot_id):
    slot = db.session.get(ExperienceSlot, slot_id) or abort(404)
    if block_slot_manual(slot):
        flash("Oportunidade bloqueada manualmente.", "info")
    else:
        flash("Uma oportunidade já reservada não pode ser bloqueada.", "error")
    return redirect(url_for("admin.opportunities"))


@admin_bp.post("/oportunidades/<int:slot_id>/reabrir")
@admin_required
def opportunity_reopen(slot_id):
    slot = db.session.get(ExperienceSlot, slot_id) or abort(404)
    if slot.status == SlotStatus.BLOCKED_EXTERNAL:
        clear_external_conflict(slot)
        flash("Conflito externo removido; disponibilidade recalculada.", "success")
    elif slot.status in {SlotStatus.BLOCKED_MANUAL, SlotStatus.EXPIRED}:
        slot.status = SlotStatus.AVAILABLE
        slot.hold_expires_at = None
        refresh_slot(slot)
        db.session.commit()
        flash("Disponibilidade recalculada.", "success")
    else:
        flash("Este horário não pode ser reaberto nesse estado.", "error")
    return redirect(url_for("admin.opportunities"))


@admin_bp.post("/oportunidades/<int:slot_id>/simular-conflito")
@admin_required
def opportunity_simulate_external_conflict(slot_id):
    """Temporary QA hook until Google Calendar OAuth is connected."""
    slot = db.session.get(ExperienceSlot, slot_id) or abort(404)
    if mark_external_conflict(slot, provider="google", reason="Conflito simulado para QA"):
        flash("Conflito externo simulado: o horário saiu do marketplace.", "info")
    else:
        flash("Somente horários disponíveis podem receber um conflito externo.", "error")
    return redirect(url_for("admin.opportunities"))


@admin_bp.route("/reservas")
@admin_required
def bookings():
    items = db.session.scalars(
        select(Booking).order_by(Booking.created_at.desc())
    ).all()
    rows = [
        {
            "booking": item,
            "local_start": to_local(item.slot.starts_at, item.professional.timezone),
        }
        for item in items
    ]
    return render_template(
        "admin/bookings/list.html",
        rows=rows,
        BookingStatus=BookingStatus,
        admin_section="bookings",
    )


def _admin_booking_status(item, status):
    now = utcnow()
    if status == BookingStatus.COMPLETED:
        item.status = status
        item.completed_at = now
    elif status == BookingStatus.NO_SHOW:
        item.status = status
        item.no_show_at = now
    elif status == BookingStatus.CANCELLED:
        try:
            delete_booking_event(item)
        except Exception:
            pass
        cancel_booking(item, reason="Cancelada pelo administrador", now=now)
        return
    db.session.commit()


@admin_bp.post("/reservas/<int:booking_id>/concluir")
@admin_required
def booking_complete(booking_id):
    item = db.session.get(Booking, booking_id) or abort(404)
    if item.status != BookingStatus.CONFIRMED:
        flash("Somente reservas confirmadas podem ser concluídas.", "error")
    else:
        _admin_booking_status(item, BookingStatus.COMPLETED)
        flash("Atendimento marcado como concluído.", "success")
    return redirect(url_for("admin.bookings"))


@admin_bp.post("/reservas/<int:booking_id>/no-show")
@admin_required
def booking_no_show(booking_id):
    item = db.session.get(Booking, booking_id) or abort(404)
    if item.status != BookingStatus.CONFIRMED:
        flash("Somente reservas confirmadas podem ser marcadas como no-show.", "error")
    else:
        _admin_booking_status(item, BookingStatus.NO_SHOW)
        flash("Reserva marcada como não compareceu.", "info")
    return redirect(url_for("admin.bookings"))


@admin_bp.post("/reservas/<int:booking_id>/cancelar")
@admin_required
def booking_cancel_admin(booking_id):
    item = db.session.get(Booking, booking_id) or abort(404)
    if item.status not in {BookingStatus.PENDING, BookingStatus.CONFIRMED}:
        flash("Esta reserva não pode ser cancelada.", "error")
    else:
        _admin_booking_status(item, BookingStatus.CANCELLED)
        flash("Reserva cancelada.", "info")
    return redirect(url_for("admin.bookings"))


@admin_bp.get("/identificador/disponibilidade")
@admin_required
def handle_availability():
    resource_type = request.args.get("type")
    value = request.args.get("value", "")
    current_id = request.args.get("current_id", type=int)
    if resource_type not in {"professional", "establishment"}:
        return {"available": False, "message": "Tipo de perfil inválido."}, 400
    available, message = public_handle_available(
        value, resource_type=resource_type, current_id=current_id
    )
    from app.services.slug_service import slugify
    return {
        "available": available,
        "handle": slugify(value),
        "message": message if not available else "Este endereço está disponível.",
    }
