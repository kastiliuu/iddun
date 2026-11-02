from app.models.reschedule_request import RescheduleRequest
from app.models.cancellation_request import CancellationRequest
from app.services.cancellation_request_service import execute_cancellation, pending_cancellation
from datetime import date, datetime, time, timedelta, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.forms.platform import (
    BizPublishForm,
    BizStepAddressForm,
    BizStepBasicsForm,
    BizStepContactForm,
    BizStepHoursForm,
    BizStepMediaForm,
    BizStepOperationForm,
    BusinessEditForm,
    WEEKDAY_FIELDS,
    ProfessionalCertificationForm,
    ProfessionalEditForm,
    ProPublishForm,
    ProStepIdentityForm,
    ProStepLocationForm,
    ProStepModalityForm,
    ProStepPersonalizeForm,
    ProStepPresentationForm,
    ProStepSpecialtyForm,
    ProfessionalWorkExperienceForm,
    ProfessionalServiceDraftForm,
    TeamMemberForm,
    WorkModeChoiceForm,
)
from app.models.booking import (
    Booking,
    BookingStatus,
    ExperienceSlot,
    SlotStatus,
)
from app.models.certification import ProfessionalCertification
from app.models.establishment import (
    Establishment,
    EstablishmentAccessStatus,
    EstablishmentGalleryItem,
    EstablishmentUserAccess,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.experience import Experience, ExperienceStatus
from app.models.professional_experience import ProfessionalExperience
from app.models.professional import (
    ProfessionalPortfolioItem,
    ProfileTheme,
)
from app.models.reputation import ContactClick
from app.models.user import User
from app.services.admin_catalog_service import publish_experience
from app.services.business_operation_insights import business_operation_insights
from app.services.availability_service import AvailabilityError, create_availability, create_availability_batch, create_availability_from_working_hours
from app.services.booking_service import (
    BookingStateError,
    block_slot_manual,
    cancel_booking,
    complete_booking,
    mark_booking_no_show,
    reopen_manual_slot,
)
from app.services.google_calendar_service import (
    delete_booking_event,
)
from app.services.media_service import (
    UploadBatch,
    delete_uploaded_file,
    delete_uploaded_files,
)
from app.services.professional_dashboard_service import (
    professional_dashboard_context,
)
from app.services.professional_crm_service import (
    professional_clients_context,
)
from app.services.professional_insights_service import (
    professional_insights_context,
)
from app.services.professional_capacity_service import (
    professional_capacity_context,
)
from app.services.professional_schedule_service import (
    ScheduleValidationError,
    save_weekly_schedule,
    schedule_rows,
)
from app.services.establishment_readiness_service import valid_business_hours
from app.services.mobile_onboarding_service import (
    MobileOnboardingError,
    OnboardingConflict,
    create_establishment_draft,
    owned_establishment,
    owned_establishments,
    publish_establishment,
    publish_professional_profile,
    update_establishment_draft,
    update_professional_draft,
)
from app.services.onboarding_steps import (
    PROFESSIONAL_CATEGORIES,
    business_journey,
    professional_journey,
)
from app.services.reputation_service import reputation_summary
from app.services.slug_service import unique_slug
from app.services.time_service import to_local, local_naive_to_utc


professional_bp = Blueprint(
    "professional",
    __name__,
    url_prefix="/pro",
)
business_bp = Blueprint(
    "business",
    __name__,
    url_prefix="/business",
)


def utcnow():
    return datetime.now(timezone.utc)


def _files_with_names(items):
    return [
        item
        for item in (items or [])
        if item and getattr(item, "filename", "")
    ]


def _theme_for_business(category):
    if category == "barbearia":
        return "barber"

    if category == "tatuagem":
        return "tattoo"

    return "beauty"


def _focus_value(value):
    """Normalize media focal points when an older client omits the field."""
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 50


def _managed_establishment(slug):
    establishment = db.session.scalar(
        select(Establishment).where(
            Establishment.slug == slug,
        )
    )

    if establishment is None:
        abort(404)

    access = db.session.scalar(
        select(EstablishmentUserAccess).where(
            EstablishmentUserAccess.establishment_id
            == establishment.id,
            EstablishmentUserAccess.user_id
            == current_user.id,
            EstablishmentUserAccess.status
            == EstablishmentAccessStatus.ACTIVE,
        )
    )

    if access is None:
        abort(403)

    return establishment, access


def _record_upload_failure(
    form_field,
    message,
    log_message,
):
    db.session.rollback()
    current_app.logger.exception(log_message)
    form_field.errors.append(message)


@professional_bp.route(
    "/comecar",
    methods=["GET", "POST"],
)
@login_required
def start():
    form = WorkModeChoiceForm()

    if form.validate_on_submit():
        if form.mode.data == "business":
            return redirect(
                url_for("business.onboarding")
            )

        # Publicado vai ao painel; rascunho retoma a etapa pendente.
        return redirect(
            url_for("professional.onboarding")
        )

    return render_template(
        "platform/start.html",
        form=form,
        current_page="for-professionals",
    )


# --- Onboarding Profissional por etapas (PR 2 do onboarding V0) ------------
#
# Cada etapa é um formulário comum (funciona sem JavaScript) que salva o
# rascunho no servidor pelo mesmo serviço da API do app. Publicar é uma
# ação explícita na etapa "Revisar e publicar" (F1). Perfis já publicados
# não passam por aqui: seguem para o painel e para Editar perfil.

# Fora do ar pela moderação (published_at preenchido e is_active falso):
# mesma regra da publicação, que recusa com publication_locked.
PRO_LOCKED_MESSAGE = (
    "Este perfil foi desativado e não pode ser publicado por aqui. "
    "Fale com o suporte do IDDUN."
)
BIZ_LOCKED_MESSAGE = (
    "Esta página foi desativada e não pode ser publicada por aqui. "
    "Fale com o suporte do IDDUN."
)

PRO_ONBOARDING_STEPS = (
    {
        "slug": "nome",
        "key": "identity",
        "form": ProStepIdentityForm,
        "title": "Como as pessoas vão te chamar?",
        "lead": "Use o nome que seus clientes já conhecem. Ele aparece no seu perfil público.",
    },
    {
        "slug": "cidade",
        "key": "location",
        "form": ProStepLocationForm,
        "title": "Onde você atende?",
        "lead": "Cidade e UF ajudam clientes da sua região a encontrar você.",
    },
    {
        "slug": "especialidade",
        "key": "specialty",
        "form": ProStepSpecialtyForm,
        "title": "Qual é a sua especialidade?",
        "lead": "Diga o que você faz de melhor e escolha as áreas em que atua.",
    },
    {
        "slug": "atendimento",
        "key": "modality",
        "form": ProStepModalityForm,
        "title": "Como você atende?",
        "lead": "Escolha uma ou mais formas. O endereço do cliente nunca aparece no seu perfil.",
    },
    {
        "slug": "apresentacao",
        "key": "presentation",
        "form": ProStepPresentationForm,
        "title": "Conte quem você é.",
        "lead": "Fale da sua técnica, da sua experiência e do resultado que gosta de entregar.",
    },
    {
        "slug": "fotos",
        "key": "personalize",
        "form": ProStepPersonalizeForm,
        "optional": True,
        "multipart": True,
        "title": "Deixe o perfil com a sua cara",
        "lead": "Tudo nesta etapa é opcional. Dá para fazer agora ou depois, em Editar perfil.",
    },
    {
        "slug": "revisar",
        "key": "review",
        "form": ProPublishForm,
        "title": "Revise e publique seu perfil",
        "lead": "Publicar coloca seu perfil no ar. Receber reservas depende de serviços e horários, que você cria depois.",
    },
)
PRO_STEP_BY_SLUG = {item["slug"]: item for item in PRO_ONBOARDING_STEPS}
PRO_SLUG_BY_KEY = {item["key"]: item["slug"] for item in PRO_ONBOARDING_STEPS}


def _pro_step_url(slug, **params):
    return url_for("professional.onboarding_step", step=slug, **params)


def _pro_onboarding_prefill(form, profile, slug):
    if slug == "nome":
        form.display_name.data = (
            profile.display_name if profile is not None else current_user.name
        )
    if profile is None:
        return
    if slug == "cidade":
        form.city.data = profile.city
        form.state.data = profile.state
    elif slug == "especialidade":
        form.primary_specialty.data = profile.primary_specialty
        selected = {
            item.strip().lower()
            for item in (profile.specialties_text or "").split(",")
            if item.strip()
        }
        form.categories.data = [
            key for key, label in PROFESSIONAL_CATEGORIES.items()
            if label.lower() in selected
        ]
    elif slug == "atendimento":
        form.attendance_modalities.data = [
            item for item in (profile.attendance_modalities or "").split(",") if item
        ]
    elif slug == "apresentacao":
        form.headline.data = profile.headline
        form.bio.data = profile.bio
    elif slug == "fotos":
        form.phone.data = profile.phone
        form.whatsapp_enabled.data = bool(profile.whatsapp_enabled)
        form.instagram.data = profile.instagram
        form.visual_theme.data = profile.visual_theme or ProfileTheme.BEAUTY
        form.avatar_focus_x.data = profile.avatar_focus_x
        form.avatar_focus_y.data = profile.avatar_focus_y
        form.cover_focus_x.data = profile.cover_focus_x
        form.cover_focus_y.data = profile.cover_focus_y


def _pro_onboarding_changes(form, slug):
    if slug == "nome":
        return {"display_name": form.display_name.data}
    if slug == "cidade":
        return {"city": form.city.data, "state": form.state.data}
    if slug == "especialidade":
        return {
            "primary_specialty": form.primary_specialty.data,
            "categories": list(form.categories.data or []),
        }
    if slug == "atendimento":
        return {"attendance_modalities": list(form.attendance_modalities.data or [])}
    if slug == "apresentacao":
        return {"headline": form.headline.data or None, "bio": form.bio.data}
    return {}


def _save_pro_personalize_step(form, profile):
    """Fotos, portfólio e contatos opcionais. Arquivos e banco andam juntos."""
    portfolio_files = _files_with_names(form.portfolio_files.data)
    room = max(0, 8 - len(profile.portfolio_items))
    if len(portfolio_files) > room:
        form.portfolio_files.errors.append(
            f"Você pode adicionar mais {room} foto(s) ao portfólio agora."
            if room
            else "Seu portfólio já tem 8 fotos. Remova alguma em Editar perfil."
        )
        return False

    replaced_media = []
    try:
        with UploadBatch() as uploads:
            avatar_url = uploads.save_image(form.avatar_file.data, "professionals")
            cover_url = uploads.save_image(form.cover_file.data, "professionals/covers")
            new_portfolio = uploads.save_many_images(
                portfolio_files, "professionals/portfolio", max_files=8,
            )

            update_professional_draft(
                user=current_user,
                changes={
                    "phone": form.phone.data or None,
                    "whatsapp_enabled": bool(form.whatsapp_enabled.data and form.phone.data),
                    "instagram": form.instagram.data or None,
                    "visual_theme": form.visual_theme.data or None,
                },
                commit=False,
            )
            profile.avatar_focus_x = _focus_value(form.avatar_focus_x.data)
            profile.avatar_focus_y = _focus_value(form.avatar_focus_y.data)
            profile.cover_focus_x = _focus_value(form.cover_focus_x.data)
            profile.cover_focus_y = _focus_value(form.cover_focus_y.data)
            if avatar_url:
                replaced_media.append(profile.avatar_url)
                profile.avatar_url = avatar_url
            if cover_url:
                replaced_media.append(profile.cover_url)
                profile.cover_url = cover_url
            start_order = len(profile.portfolio_items)
            for offset, image_url in enumerate(new_portfolio):
                db.session.add(ProfessionalPortfolioItem(
                    professional=profile,
                    image_url=image_url,
                    sort_order=start_order + offset,
                ))
            db.session.commit()
            uploads.commit()
    except MobileOnboardingError as exc:
        db.session.rollback()
        form.phone.errors.append(str(exc))
        return False
    except ValueError as exc:
        db.session.rollback()
        form.portfolio_files.errors.append(str(exc))
        return False
    except (OSError, SQLAlchemyError):
        _record_upload_failure(
            form.portfolio_files,
            "Não foi possível salvar suas fotos agora. Tente novamente.",
            "Falha ao salvar fotos do onboarding profissional.",
        )
        return False

    delete_uploaded_files(replaced_media)
    return True


@professional_bp.get("/onboarding")
@login_required
def onboarding():
    """Retoma o cadastro na primeira etapa pendente."""
    profile = current_user.professional_profile
    if profile is not None and profile.is_active:
        return redirect(url_for("professional.dashboard"))
    if profile is not None and profile.published_at is not None:
        # Desativado pela moderação: o dono não republica por aqui.
        flash(PRO_LOCKED_MESSAGE, "info")
        return redirect(url_for("professional.dashboard"))
    if profile is None:
        return redirect(_pro_step_url("nome"))
    journey = professional_journey(profile)
    return redirect(_pro_step_url(PRO_SLUG_BY_KEY[journey["currentStep"]]))


@professional_bp.route("/onboarding/<step>", methods=["GET", "POST"])
@login_required
def onboarding_step(step):
    definition = PRO_STEP_BY_SLUG.get(step)
    if definition is None:
        abort(404)

    profile = current_user.professional_profile
    if profile is not None and profile.is_active:
        flash(
            "Seu perfil já está publicado. Para mudar algo, use Editar perfil.",
            "info",
        )
        return redirect(url_for("professional.dashboard"))
    if profile is not None and profile.published_at is not None:
        flash(PRO_LOCKED_MESSAGE, "info")
        return redirect(url_for("professional.dashboard"))
    if profile is None and step != "nome":
        return redirect(_pro_step_url("nome"))

    index = PRO_ONBOARDING_STEPS.index(definition)
    back_to_review = request.args.get("retorno") == "revisar" and step != "revisar"
    form = definition["form"]()
    step_error = None

    if request.method == "GET":
        _pro_onboarding_prefill(form, profile, step)

    if form.validate_on_submit():
        if step == "revisar":
            try:
                publish_professional_profile(profile)
            except OnboardingConflict as exc:
                step_error = str(exc)
            else:
                return redirect(url_for("professional.onboarding_done"))
        elif step == "fotos":
            if _save_pro_personalize_step(form, profile):
                return redirect(_pro_step_url("revisar"))
        else:
            try:
                update_professional_draft(
                    user=current_user,
                    changes=_pro_onboarding_changes(form, step),
                )
            except MobileOnboardingError as exc:
                step_error = str(exc)
            else:
                if back_to_review:
                    return redirect(_pro_step_url("revisar"))
                return redirect(_pro_step_url(PRO_ONBOARDING_STEPS[index + 1]["slug"]))

    profile = current_user.professional_profile
    journey = professional_journey(profile) if profile is not None else None
    previous = PRO_ONBOARDING_STEPS[index - 1]["slug"] if index > 0 else None
    status = 422 if request.method == "POST" else 200
    return render_template(
        "platform/pro-onboarding-step.html",
        form=form,
        step=definition,
        steps=PRO_ONBOARDING_STEPS,
        step_index=index,
        step_total=len(PRO_ONBOARDING_STEPS),
        previous_url=_pro_step_url(previous) if previous else url_for("professional.start"),
        step_url=_pro_step_url,
        review_url=_pro_step_url("revisar"),
        onb_kicker="Cadastro profissional",
        back_to_review=back_to_review,
        profile=profile,
        journey=journey,
        step_error=step_error,
        current_page="for-professionals",
    ), status


@professional_bp.get("/onboarding/concluido")
@login_required
def onboarding_done():
    profile = current_user.professional_profile
    if profile is None or not profile.is_active:
        return redirect(url_for("professional.onboarding"))
    return render_template(
        "platform/pro-onboarding-done.html",
        profile=profile,
        journey=professional_journey(profile),
        current_page="for-professionals",
    )


@professional_bp.route("")
@professional_bp.route("/painel")
@login_required
def dashboard():
    profile = current_user.professional_profile

    if profile is None:
        return redirect(
            url_for("professional.start")
        )

    confirmed_bookings = sum(
        1
        for booking in profile.bookings
        if booking.status == BookingStatus.CONFIRMED
    )
    published_experiences = sum(
        1
        for item in profile.experiences
        if item.status == ExperienceStatus.PUBLISHED
    )
    reputation = reputation_summary(
        profile.reviews_received
    )
    whatsapp_clicks = sum(
        1
        for item in profile.contact_clicks
        if item.channel == "whatsapp"
    )

    day_context = (
        professional_dashboard_context(
            profile
        )
    )
    crm_context = (
        professional_clients_context(
            profile
        )
    )
    insights_context = (
        professional_insights_context(
            profile
        )
    )
    capacity_context = (
        professional_capacity_context(
            profile
        )
    )

    return render_template(
        "platform/professional-dashboard.html",
        profile=profile,
        reschedule_requests=db.session.scalars(
            select(RescheduleRequest)
            .join(Booking, Booking.id == RescheduleRequest.booking_id)
            .where(
                Booking.professional_id == profile.id,
                Booking.status == BookingStatus.CONFIRMED,
                RescheduleRequest.status == "pending",
            ).order_by(RescheduleRequest.requested_at.asc())
        ).all(),
        cancellation_requests=db.session.scalars(
            select(CancellationRequest)
            .join(Booking, Booking.id == CancellationRequest.booking_id)
            .where(
                Booking.professional_id == profile.id,
                Booking.status == BookingStatus.CONFIRMED,
                CancellationRequest.status == "pending",
            )
            .order_by(CancellationRequest.requested_at.asc())
        ).all(),
        confirmed_bookings=confirmed_bookings,
        published_experiences=published_experiences,
        reputation=reputation,
        whatsapp_clicks=whatsapp_clicks,
        current_page="professional-dashboard",
        **day_context,
        crm=crm_context,
        insights=insights_context,
        capacity=capacity_context,
    )


def _professional_slot_or_404(
    slot_id,
):
    profile = (
        current_user.professional_profile
    )

    if profile is None:
        abort(403)

    slot = db.session.get(
        ExperienceSlot,
        slot_id,
    )

    if (
        slot is None
        or slot.professional_id
        != profile.id
    ):
        abort(404)

    return slot


def _professional_booking_or_404(
    booking_id,
):
    profile = (
        current_user.professional_profile
    )

    if profile is None:
        abort(403)

    booking = db.session.get(
        Booking,
        booking_id,
    )

    if (
        booking is None
        or booking.professional_id
        != profile.id
    ):
        abort(404)

    return booking


def _dashboard_redirect():
    return redirect(
        url_for(
            "professional.dashboard"
        )
        + "#agenda-hoje"
    )


@professional_bp.post(
    "/painel/horarios/<int:slot_id>/bloquear"
)
@login_required
def dashboard_block_slot(slot_id):
    slot = _professional_slot_or_404(
        slot_id
    )

    if block_slot_manual(slot):
        flash(
            "Horário bloqueado.",
            "success",
        )
    else:
        flash(
            "Este horário já possui uma reserva e não pode ser bloqueado.",
            "error",
        )

    return _dashboard_redirect()


@professional_bp.post(
    "/painel/horarios/<int:slot_id>/liberar"
)
@login_required
def dashboard_reopen_slot(slot_id):
    slot = _professional_slot_or_404(
        slot_id
    )

    try:
        reopen_manual_slot(slot)
    except BookingStateError as exc:
        flash(
            str(exc),
            "error",
        )
    else:
        if slot.status == "available":
            flash(
                "Horário liberado novamente.",
                "success",
            )
        else:
            flash(
                "O horário não pode mais ser reservado porque o prazo mínimo já passou.",
                "info",
            )

    return _dashboard_redirect()


@professional_bp.post(
    "/painel/reservas/<int:booking_id>/concluir"
)
@login_required
def dashboard_complete_booking(
    booking_id,
):
    booking = (
        _professional_booking_or_404(
            booking_id
        )
    )

    try:
        complete_booking(
            booking
        )
    except BookingStateError as exc:
        flash(
            str(exc),
            "error",
        )
    else:
        flash(
            "Atendimento marcado como concluído.",
            "success",
        )

    return _dashboard_redirect()


@professional_bp.post(
    "/painel/reservas/<int:booking_id>/no-show"
)
@login_required
def dashboard_no_show_booking(
    booking_id,
):
    booking = (
        _professional_booking_or_404(
            booking_id
        )
    )

    try:
        mark_booking_no_show(
            booking
        )
    except BookingStateError as exc:
        flash(
            str(exc),
            "error",
        )
    else:
        flash(
            "Atendimento marcado como não compareceu.",
            "info",
        )

    return _dashboard_redirect()


@professional_bp.post(
    "/painel/reservas/<int:booking_id>/cancelar"
)
@login_required
def dashboard_cancel_booking(
    booking_id,
):
    booking = (
        _professional_booking_or_404(
            booking_id
        )
    )

    try:
        request_reason = (request.form.get("motivo") or "").strip()
        if pending_cancellation(booking.id):
            execute_cancellation(
                booking, current_user, request_reason or "Solicitação aceita pelo executor"
            )
        else:
            cancel_booking(
                booking, reason=request_reason or "Cancelada pelo profissional"
            )
        try:
            delete_booking_event(booking)
        except Exception:
            current_app.logger.exception(
                "Falha ao remover evento externo após o cancelamento confirmado."
            )
    except BookingStateError as exc:
        flash(
            str(exc),
            "error",
        )
    else:
        flash(
            "Reserva cancelada. O horário voltou a seguir as regras de disponibilidade.",
            "success",
        )

    return _dashboard_redirect()


@professional_bp.route(
    "/jornada",
    methods=["GET", "POST"],
)
@login_required
def schedule():
    profile = (
        current_user.professional_profile
    )

    if profile is None:
        return redirect(
            url_for(
                "professional.start"
            )
        )

    if request.method == "POST":
        try:
            active_days = (
                save_weekly_schedule(
                    profile,
                    request.form,
                )
            )
        except ScheduleValidationError as exc:
            db.session.rollback()
            flash(
                str(exc),
                "error",
            )
        else:
            flash(
                (
                    "Jornada atualizada. "
                    f"{active_days} dia(s) "
                    "de trabalho configurado(s)."
                ),
                "success",
            )
            return redirect(
                url_for(
                    "professional.schedule"
                )
            )

    return render_template(
        "platform/professional-schedule.html",
        profile=profile,
        schedule=schedule_rows(
            profile
        ),
        capacity=(
            professional_capacity_context(
                profile
            )
        ),
        current_page="professional-schedule",
    )


@professional_bp.get(
    "/insights"
)
@login_required
def insights():
    profile = (
        current_user.professional_profile
    )

    if profile is None:
        return redirect(
            url_for(
                "professional.start"
            )
        )

    context = (
        professional_insights_context(
            profile
        )
    )
    capacity = (
        professional_capacity_context(
            profile
        )
    )

    return render_template(
        "platform/professional-insights.html",
        profile=profile,
        current_page="professional-insights",
        capacity=capacity,
        **context,
    )


def _service_establishment_choices(profile):
    memberships = db.session.scalars(
        select(ProfessionalEstablishmentMembership).where(
            ProfessionalEstablishmentMembership.professional_id == profile.id,
            ProfessionalEstablishmentMembership.status == MembershipStatus.ACTIVE,
        )
    ).all()
    return [(0, "Atendimento independente (sem estabelecimento)")] + [
        (membership.establishment_id, membership.establishment.name)
        for membership in memberships
        if membership.establishment.is_active
    ]


@professional_bp.route("/servicos/novo", methods=["GET", "POST"])
@login_required
def create_service():
    profile = current_user.professional_profile
    if profile is None:
        return redirect(url_for("professional.start"))

    form = ProfessionalServiceDraftForm()
    form.establishment_id.choices = _service_establishment_choices(profile)
    if form.validate_on_submit():
        try:
            with UploadBatch() as uploads:
                image_url = uploads.save_image(
                    form.image_file.data, "experiences",
                )
                item = Experience(
                    professional_id=profile.id,
                    establishment_id=form.establishment_id.data or None,
                    title=form.title.data.strip(),
                    slug=unique_slug(Experience, form.title.data),
                    category=form.category.data,
                    short_description=form.short_description.data.strip(),
                    description=(form.description.data or "").strip() or None,
                    regular_price=form.regular_price.data,
                    price=form.price.data,
                    duration_minutes=form.duration_minutes.data,
                    image_url=image_url,
                    status=ExperienceStatus.DRAFT,
                )
                db.session.add(item)
                db.session.commit()
                uploads.commit()
        except ValueError as exc:
            db.session.rollback()
            form.image_file.errors.append(str(exc))
        except (OSError, SQLAlchemyError):
            db.session.rollback()
            current_app.logger.exception("Falha ao criar serviço profissional.")
            form.image_file.errors.append(
                "Não foi possível salvar o serviço. Tente novamente."
            )
        else:
            flash(
                "Rascunho do serviço criado. Você poderá publicá-lo após completar as informações necessárias.",
                "success",
            )
            return redirect(url_for("professional.services"))

    return render_template(
        "platform/professional-service-form.html",
        form=form,
        current_page="professional-services",
    )


@professional_bp.route("/servicos/<int:service_id>/editar", methods=["GET", "POST"])
@login_required
def edit_service(service_id):
    profile = current_user.professional_profile
    if profile is None:
        abort(404)

    item = db.session.scalar(
        select(Experience).where(
            Experience.id == service_id,
            Experience.professional_id == profile.id,
        )
    )
    if item is None:
        abort(404)

    # Changes to published services could unexpectedly alter the terms
    # of existing bookings. Keep this first editing flow to inactive items.
    if item.status not in {ExperienceStatus.DRAFT, ExperienceStatus.PAUSED}:
        flash("Somente serviços em rascunho ou pausados podem ser editados.", "info")
        return redirect(url_for("professional.services"))

    form = ProfessionalServiceDraftForm(obj=item)
    form.establishment_id.choices = _service_establishment_choices(profile)
    if request.method == "GET":
        form.establishment_id.data = item.establishment_id or 0

    # A change of location must never desynchronize existing slot/booking rows.
    changing_location = (
        request.method == "POST"
        and form.establishment_id.data is not None
        and (form.establishment_id.data or None) != item.establishment_id
    )
    if changing_location and db.session.scalar(
        select(ExperienceSlot.id).where(ExperienceSlot.experience_id == item.id).limit(1)
    ) is not None:
        form.establishment_id.errors = list(form.establishment_id.errors) + [
            "Não é possível alterar o local de um serviço que já possui horários."
        ]
        return render_template(
            "platform/professional-service-form.html",
            form=form, service=item, current_page="professional-services",
        ), 200

    if form.validate_on_submit():
        old_image_url = item.image_url
        try:
            with UploadBatch() as uploads:
                new_image_url = uploads.save_image(
                    form.image_file.data, "experiences",
                )
                item.establishment_id = form.establishment_id.data or None
                item.title = form.title.data.strip()
                item.category = form.category.data
                item.short_description = form.short_description.data.strip()
                item.description = (form.description.data or "").strip() or None
                item.regular_price = form.regular_price.data
                item.price = form.price.data
                item.duration_minutes = form.duration_minutes.data
                if new_image_url:
                    item.image_url = new_image_url
                # Keep slug and publication state unchanged.
                db.session.commit()
                uploads.commit()
        except ValueError as exc:
            db.session.rollback()
            form.image_file.errors.append(str(exc))
        except (OSError, SQLAlchemyError):
            db.session.rollback()
            current_app.logger.exception("Falha ao editar serviço profissional.")
            form.image_file.errors.append(
                "Não foi possível atualizar o serviço. Tente novamente."
            )
        else:
            if new_image_url and old_image_url:
                delete_uploaded_file(old_image_url)
            flash("Serviço atualizado.", "success")
            return redirect(url_for("professional.services"))

    return render_template(
        "platform/professional-service-form.html",
        form=form,
        service=item,
        current_page="professional-services",
    )


@professional_bp.post("/servicos/<int:service_id>/publicar")
@login_required
def publish_service(service_id):
    profile = current_user.professional_profile
    if profile is None:
        abort(404)

    item = db.session.scalar(
        select(Experience).where(
            Experience.id == service_id,
            Experience.professional_id == profile.id,
        )
    )
    if item is None:
        abort(404)
    if item.status not in {ExperienceStatus.DRAFT, ExperienceStatus.PAUSED}:
        flash("Este serviço não pode ser publicado neste estado.", "info")
        return redirect(url_for("professional.services"))

    try:
        publish_experience(item)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "error")
    else:
        flash("Serviço publicado no IDDUN.", "success")
    return redirect(url_for("professional.services"))


@professional_bp.post("/servicos/<int:service_id>/pausar")
@login_required
def pause_service(service_id):
    profile = current_user.professional_profile
    if profile is None:
        abort(404)

    item = db.session.scalar(
        select(Experience).where(
            Experience.id == service_id,
            Experience.professional_id == profile.id,
        )
    )
    if item is None:
        abort(404)
    if item.status != ExperienceStatus.PUBLISHED:
        flash("Somente serviços publicados podem ser pausados.", "info")
        return redirect(url_for("professional.services"))

    item.status = ExperienceStatus.PAUSED
    db.session.commit()
    flash("Serviço pausado. Reservas já confirmadas permanecem válidas.", "info")
    return redirect(url_for("professional.services"))


@professional_bp.post("/servicos/<int:service_id>/horarios")
@login_required
def create_service_slot(service_id):
    profile = current_user.professional_profile
    if profile is None:
        abort(404)
    item = db.session.scalar(
        select(Experience).where(
            Experience.id == service_id,
            Experience.professional_id == profile.id,
        )
    )
    if item is None:
        abort(404)

    try:
        create_availability(
            user=current_user,
            experience_reference=str(item.id),
            slot_date=request.form.get("slot_date"),
            slot_time=request.form.get("slot_time"),
        )
    except AvailabilityError as exc:
        flash(str(exc), "error")
    else:
        flash("Horário disponibilizado para reserva.", "success")
    return redirect(url_for("professional.services") + f"#servico-{item.id}")


@professional_bp.post("/servicos/<int:service_id>/horarios/lote")
@login_required
def create_service_slots_batch(service_id):
    profile = current_user.professional_profile
    if profile is None:
        abort(404)
    item = db.session.scalar(
        select(Experience).where(
            Experience.id == service_id,
            Experience.professional_id == profile.id,
        )
    )
    if item is None:
        abort(404)

    try:
        created = create_availability_batch(
            user=current_user,
            experience_reference=str(item.id),
            slot_date=request.form.get("slot_date"),
            slot_times=request.form.get("slot_times"),
        )
    except AvailabilityError as exc:
        flash(str(exc), "error")
    else:
        flash(f"{len(created)} horários disponibilizados para reserva.", "success")
    return redirect(url_for("professional.services") + f"#servico-{item.id}")


@professional_bp.post("/servicos/<int:service_id>/horarios/jornada")
@login_required
def create_service_slots_from_schedule(service_id):
    profile = current_user.professional_profile
    if profile is None:
        abort(404)
    item = db.session.scalar(
        select(Experience).where(
            Experience.id == service_id,
            Experience.professional_id == profile.id,
        )
    )
    if item is None:
        abort(404)

    try:
        created = create_availability_from_working_hours(
            user=current_user,
            experience_reference=str(item.id),
            slot_date=request.form.get("slot_date"),
        )
    except AvailabilityError as exc:
        flash(str(exc), "error")
    else:
        flash(
            f"{len(created)} horários abertos conforme sua jornada semanal.",
            "success",
        )
    return redirect(url_for("professional.services") + f"#servico-{item.id}")


@professional_bp.post("/servicos/<int:service_id>/horarios/<int:slot_id>/bloquear")
@login_required
def block_service_slot(service_id, slot_id):
    slot = _professional_slot_or_404(slot_id)
    if slot.experience_id != service_id:
        abort(404)
    # Never cancel pending holds as a side effect from the service catalog.
    if slot.status != SlotStatus.AVAILABLE:
        flash("Somente horários disponíveis podem ser bloqueados aqui.", "error")
    elif block_slot_manual(slot):
        flash("Horário bloqueado.", "success")
    else:
        flash("Este horário não pode ser bloqueado.", "error")
    return redirect(url_for("professional.services") + f"#servico-{service_id}")


@professional_bp.post("/servicos/<int:service_id>/horarios/<int:slot_id>/liberar")
@login_required
def reopen_service_slot(service_id, slot_id):
    slot = _professional_slot_or_404(slot_id)
    if slot.experience_id != service_id:
        abort(404)
    if slot.status != SlotStatus.BLOCKED_MANUAL:
        flash("Somente horários bloqueados manualmente podem ser liberados.", "error")
    else:
        try:
            reopen_manual_slot(slot)
        except BookingStateError as exc:
            flash(str(exc), "error")
        else:
            flash(
                "Horário liberado." if slot.status == SlotStatus.AVAILABLE
                else "O prazo para reservar este horário já terminou.",
                "success" if slot.status == SlotStatus.AVAILABLE else "info",
            )
    return redirect(url_for("professional.services") + f"#servico-{service_id}")


@professional_bp.get("/servicos")
@login_required
def services():
    profile = current_user.professional_profile
    if profile is None:
        return redirect(url_for("professional.start"))

    items = db.session.scalars(
        select(Experience)
        .where(Experience.professional_id == profile.id)
        .order_by(Experience.created_at.desc(), Experience.id.desc())
    ).all()
    upcoming = db.session.scalars(
        select(ExperienceSlot)
        .where(
            ExperienceSlot.professional_id == profile.id,
            ExperienceSlot.starts_at >= utcnow(),
        )
        .order_by(ExperienceSlot.starts_at.asc())
        .limit(100)
    ).all()
    slots_by_service = {item.id: [] for item in items}
    for slot in upcoming:
        rows = slots_by_service.get(slot.experience_id)
        if rows is not None and len(rows) < 5:
            rows.append({
                "id": slot.id,
                "starts_at": to_local(slot.starts_at, profile.timezone),
                "raw_status": slot.status,
                "status": SlotStatus.LABELS.get(slot.status, slot.status),
            })

    return render_template(
        "platform/professional-services.html",
        profile=profile,
        experiences=items,
        slots_by_service=slots_by_service,
        ExperienceStatus=ExperienceStatus,
        SlotStatus=SlotStatus,
        current_page="professional-services",
    )


@professional_bp.get(
    "/clientes"
)
@login_required
def clients():
    profile = (
        current_user.professional_profile
    )

    if profile is None:
        return redirect(
            url_for(
                "professional.start"
            )
        )

    context = (
        professional_clients_context(
            profile,
            search=request.args.get(
                "q",
                "",
            ),
        )
    )

    return render_template(
        "platform/professional-clients.html",
        profile=profile,
        current_page="professional-clients",
        **context,
    )


@professional_bp.route(
    "/perfil/editar",
    methods=["GET", "POST"],
)
@login_required
def edit_profile():
    profile = current_user.professional_profile

    if profile is None:
        return redirect(
            url_for("professional.onboarding")
        )

    form = ProfessionalEditForm(obj=profile)
    if request.method == 'GET':
        form.attendance_modalities.data = (profile.attendance_modalities or '').split(',') if profile.attendance_modalities else []

    if form.validate_on_submit():
        replaced_media = []

        try:
            with UploadBatch() as uploads:
                avatar_url = uploads.save_image(
                    form.avatar_file.data,
                    "professionals",
                )
                cover_url = uploads.save_image(
                    form.cover_file.data,
                    "professionals/covers",
                )
                new_portfolio = (
                    uploads.save_many_images(
                        form.portfolio_files.data,
                        "professionals/portfolio",
                        max_files=8,
                    )
                )

                profile.display_name = (
                    form.display_name.data.strip()
                )
                profile.headline = (
                    form.headline.data or ""
                ).strip() or None
                profile.primary_specialty = (
                    form.primary_specialty.data.strip()
                )
                profile.specialties_text = (
                    form.specialties_text.data or ""
                ).strip() or None
                profile.bio = form.bio.data.strip()
                profile.phone = (
                    form.phone.data or ""
                ).strip() or None
                profile.whatsapp_enabled = bool(
                    form.whatsapp_enabled.data
                    and profile.phone
                )
                profile.instagram = (
                    form.instagram.data or ""
                ).strip() or None
                profile.city = form.city.data.strip()
                profile.state = (
                    form.state.data.strip().upper()
                )
                profile.visual_theme = (
                    form.visual_theme.data
                )
                profile.attendance_modalities = ",".join(form.attendance_modalities.data)
                profile.avatar_focus_x = (
                    _focus_value(
                        form.avatar_focus_x.data
                    )
                )
                profile.avatar_focus_y = (
                    _focus_value(
                        form.avatar_focus_y.data
                    )
                )
                profile.cover_focus_x = (
                    _focus_value(
                        form.cover_focus_x.data
                    )
                )
                profile.cover_focus_y = (
                    _focus_value(
                        form.cover_focus_y.data
                    )
                )

                if avatar_url:
                    replaced_media.append(
                        profile.avatar_url
                    )
                    profile.avatar_url = avatar_url

                if cover_url:
                    replaced_media.append(
                        profile.cover_url
                    )
                    profile.cover_url = cover_url

                start_order = len(
                    profile.portfolio_items
                )

                for offset, image_url in enumerate(
                    new_portfolio
                ):
                    db.session.add(
                        ProfessionalPortfolioItem(
                            professional=profile,
                            image_url=image_url,
                            sort_order=(
                                start_order + offset
                            ),
                        )
                    )

                db.session.flush()

                profile.onboarding_completed = (
                    profile.ready_to_publish
                )

                # Rascunho só vai ao ar por publicação explícita (F1);
                # aqui só se completa a data de quem já está no ar.
                if (
                    profile.is_active
                    and profile.onboarding_completed
                    and profile.published_at is None
                ):
                    profile.published_at = utcnow()

                if (
                    profile.is_active
                    and not profile.ready_to_publish
                ):
                    profile.is_active = False
                    profile.published_at = None

                db.session.commit()
                uploads.commit()

        except ValueError as exc:
            db.session.rollback()
            form.portfolio_files.errors.append(
                str(exc)
            )

        except (OSError, SQLAlchemyError):
            _record_upload_failure(
                form.portfolio_files,
                (
                    "Não foi possível atualizar seu "
                    "perfil agora. Tente novamente."
                ),
                (
                    "Falha ao atualizar o perfil "
                    "profissional."
                ),
            )

        else:
            delete_uploaded_files(replaced_media)

            flash(
                "Perfil profissional atualizado.",
                "success",
            )
            return redirect(
                url_for("professional.dashboard")
            )

    editing_experience = None
    editing_id = request.args.get("experiencia", type=int)
    if editing_id is not None:
        editing_experience = db.session.scalar(
            select(ProfessionalExperience).where(
                ProfessionalExperience.id == editing_id,
                ProfessionalExperience.professional_id == profile.id,
            )
        )
        if editing_experience is None:
            abort(404)

    return render_template(
        "platform/professional-edit.html",
        form=form,
        experience_form=ProfessionalWorkExperienceForm(obj=editing_experience),
        editing_experience=editing_experience,
        profile=profile,
        current_page="professional-dashboard",
    )


def _invalid_work_experience_response(profile, experience_form, editing_experience=None):
    """Reexibe os valores enviados sem alterar o contrato visual do editor."""
    profile_form = ProfessionalEditForm(obj=profile)
    profile_form.attendance_modalities.data = (
        (profile.attendance_modalities or "").split(",")
        if profile.attendance_modalities else []
    )
    return render_template(
        "platform/professional-edit.html",
        form=profile_form,
        experience_form=experience_form,
        editing_experience=editing_experience,
        profile=profile,
        current_page="professional-dashboard",
    ), 422


@professional_bp.post("/experiencia-profissional/adicionar")
@login_required
def add_work_experience():
    profile = current_user.professional_profile
    if profile is None:
        return redirect(url_for("professional.onboarding"))

    form = ProfessionalWorkExperienceForm()
    if not form.validate_on_submit():
        flash("Confira os dados da experiência profissional.", "error")
        return _invalid_work_experience_response(profile, form)

    experience = ProfessionalExperience(
        company_name=form.company_name.data.strip(),
        role_title=form.role_title.data.strip(),
        started_at=form.started_at.data,
        ended_at=form.ended_at.data,
        is_current=bool(form.is_current.data),
        description=(form.description.data or "").strip() or None,
    )
    try:
        experience.normalize_dates()
    except ValueError as exc:
        form.ended_at.errors.append(str(exc))
        flash(str(exc), "error")
        return _invalid_work_experience_response(profile, form)

    # Bind the relationship only after validating; an invalid transient
    # object would otherwise remain in profile.professional_experiences.
    experience.professional = profile
    db.session.add(experience)
    db.session.commit()
    flash("Experiência profissional adicionada.", "success")
    return redirect(url_for("professional.edit_profile") + "#experiencia-profissional")


@professional_bp.post("/experiencia-profissional/<int:experience_id>/editar")
@login_required
def update_work_experience(experience_id):
    profile = current_user.professional_profile
    if profile is None:
        abort(404)
    experience = db.session.scalar(
        select(ProfessionalExperience).where(
            ProfessionalExperience.id == experience_id,
            ProfessionalExperience.professional_id == profile.id,
        )
    )
    if experience is None:
        abort(404)

    form = ProfessionalWorkExperienceForm()
    if not form.validate_on_submit():
        flash("Confira os dados da experiência profissional.", "error")
        return _invalid_work_experience_response(profile, form, experience)

    # Validate a candidate before updating the existing record.
    candidate = ProfessionalExperience(
        company_name=form.company_name.data.strip(),
        role_title=form.role_title.data.strip(),
        started_at=form.started_at.data,
        ended_at=form.ended_at.data,
        is_current=bool(form.is_current.data),
        description=(form.description.data or "").strip() or None,
    )
    try:
        candidate.normalize_dates()
    except ValueError as exc:
        form.ended_at.errors.append(str(exc))
        flash(str(exc), "error")
        return _invalid_work_experience_response(profile, form, experience)

    experience.company_name = candidate.company_name
    experience.role_title = candidate.role_title
    experience.started_at = candidate.started_at
    experience.ended_at = candidate.ended_at
    experience.is_current = candidate.is_current
    experience.description = candidate.description
    db.session.commit()
    flash("Experiência profissional atualizada.", "success")
    return redirect(url_for("professional.edit_profile") + "#experiencia-profissional")


@professional_bp.post("/experiencia-profissional/<int:experience_id>/remover")
@login_required
def remove_work_experience(experience_id):
    profile = current_user.professional_profile
    if profile is None:
        abort(404)
    experience = db.session.scalar(
        select(ProfessionalExperience).where(
            ProfessionalExperience.id == experience_id,
            ProfessionalExperience.professional_id == profile.id,
        )
    )
    if experience is None:
        abort(404)
    db.session.delete(experience)
    db.session.commit()
    flash("Experiência profissional removida.", "info")
    return redirect(url_for("professional.edit_profile") + "#experiencia-profissional")


@professional_bp.post(
    "/portfolio/<int:item_id>/remover"
)
@login_required
def remove_portfolio_item(item_id):
    profile = current_user.professional_profile

    if profile is None:
        abort(404)

    item = db.session.get(
        ProfessionalPortfolioItem,
        item_id,
    )

    if (
        item is None
        or item.professional_id != profile.id
    ):
        abort(404)

    image_url = item.image_url

    profile.portfolio_items.remove(item)
    db.session.flush()

    profile.onboarding_completed = (
        profile.ready_to_publish
    )

    if not profile.onboarding_completed:
        profile.is_active = False
        profile.published_at = None

    db.session.commit()
    delete_uploaded_file(image_url)

    flash(
        "Imagem removida do portfólio.",
        "success",
    )
    return redirect(
        url_for("professional.edit_profile") + "#portfolio"
    )


@professional_bp.post(
    "/vinculos/<int:membership_id>/aceitar"
)
@login_required
def accept_membership(membership_id):
    profile = current_user.professional_profile
    membership = db.session.get(
        ProfessionalEstablishmentMembership,
        membership_id,
    )

    if (
        profile is None
        or membership is None
        or membership.professional_id != profile.id
    ):
        abort(404)

    if membership.status != MembershipStatus.PENDING:
        flash(
            "Este convite não está mais pendente.",
            "info",
        )
        return redirect(
            url_for("professional.dashboard")
        )

    has_active_membership = any(
        item.status == MembershipStatus.ACTIVE
        for item in profile.memberships
    )

    membership.status = MembershipStatus.ACTIVE
    membership.started_at = (
        membership.started_at
        or datetime.now().date()
    )
    membership.ended_at = None
    membership.is_primary = (
        not has_active_membership
    )

    db.session.commit()

    flash(
        (
            f"Vínculo com "
            f"{membership.establishment.name} "
            f"confirmado."
        ),
        "success",
    )
    return redirect(
        url_for("professional.dashboard")
    )


@professional_bp.post(
    "/vinculos/<int:membership_id>/recusar"
)
@login_required
def reject_membership(membership_id):
    profile = current_user.professional_profile
    membership = db.session.get(
        ProfessionalEstablishmentMembership,
        membership_id,
    )

    if (
        profile is None
        or membership is None
        or membership.professional_id != profile.id
    ):
        abort(404)

    if membership.status != MembershipStatus.PENDING:
        flash(
            "Este convite não está mais pendente.",
            "info",
        )
        return redirect(
            url_for("professional.dashboard")
        )

    membership.status = MembershipStatus.REJECTED
    membership.is_primary = False
    membership.ended_at = datetime.now().date()

    db.session.commit()

    flash(
        (
            f"Convite de "
            f"{membership.establishment.name} "
            f"recusado."
        ),
        "info",
    )
    return redirect(
        url_for("professional.dashboard")
    )


@professional_bp.route(
    "/certificacoes",
    methods=["GET", "POST"],
)
@login_required
def certifications():
    profile = current_user.professional_profile

    if profile is None:
        return redirect(
            url_for("professional.onboarding")
        )

    form = ProfessionalCertificationForm()

    if form.validate_on_submit():
        invalid_expiration = (
            form.expires_at.data
            and form.issued_at.data
            and form.expires_at.data
            < form.issued_at.data
        )

        if invalid_expiration:
            form.expires_at.errors.append(
                (
                    "A validade não pode ser "
                    "anterior à emissão."
                )
            )
        else:
            try:
                with UploadBatch() as uploads:
                    document_url = (
                        uploads.save_certificate(
                            form.document_file.data
                        )
                    )

                    certificate = (
                        ProfessionalCertification(
                            professional=profile,
                            title=(
                                form.title.data.strip()
                            ),
                            issuer=(
                                form.issuer.data.strip()
                            ),
                            issued_at=(
                                form.issued_at.data
                            ),
                            expires_at=(
                                form.expires_at.data
                            ),
                            credential_id=(
                                form.credential_id.data
                                or ""
                            ).strip()
                            or None,
                            verification_url=(
                                form.verification_url.data
                                or ""
                            ).strip()
                            or None,
                            document_url=document_url,
                            is_public=bool(
                                form.is_public.data
                            ),
                        )
                    )

                    db.session.add(certificate)
                    db.session.commit()
                    uploads.commit()

            except ValueError as exc:
                db.session.rollback()
                form.document_file.errors.append(
                    str(exc)
                )

            except (OSError, SQLAlchemyError):
                _record_upload_failure(
                    form.document_file,
                    (
                        "Não foi possível adicionar "
                        "a certificação agora. "
                        "Tente novamente."
                    ),
                    (
                        "Falha ao salvar uma "
                        "certificação profissional."
                    ),
                )

            else:
                flash(
                    (
                        "Certificação adicionada "
                        "ao seu perfil."
                    ),
                    "success",
                )
                return redirect(
                    url_for(
                        "professional.certifications"
                    )
                )

    return render_template(
        "platform/professional-certifications.html",
        form=form,
        profile=profile,
        current_page="professional-dashboard",
    )


@professional_bp.post(
    "/certificacoes/"
    "<int:certification_id>/remover"
)
@login_required
def remove_certification(certification_id):
    profile = current_user.professional_profile

    if profile is None:
        abort(404)

    certificate = db.session.get(
        ProfessionalCertification,
        certification_id,
    )

    if (
        certificate is None
        or certificate.professional_id
        != profile.id
    ):
        abort(404)

    document_url = certificate.document_url

    db.session.delete(certificate)
    db.session.commit()

    delete_uploaded_file(document_url)

    flash(
        "Certificação removida.",
        "info",
    )
    return redirect(
        url_for("professional.certifications")
    )


# --- Cadastro de Estabelecimento por etapas (PR 3 do onboarding V0) -------
#
# O rascunho nasce na etapa 1 (nome, tipo, cidade e UF, SCR-EST-002) e cada
# etapa seguinte é salva pelo id estável, com autorização de proprietário
# ativo, pelo mesmo serviço da API do app. Publicar é explícito (F1);
# endereço só para físico ou híbrido (F2); estabelecimentos publicados não
# passam pelo cadastro nem são alterados por ele.

BIZ_ONBOARDING_STEPS = (
    {
        "slug": "dados",
        "key": "basics",
        "form": BizStepBasicsForm,
        "title": "Qual é o seu espaço e onde ele fica?",
        "lead": "Nome, tipo e cidade criam o rascunho da sua página. Nada fica público até você publicar.",
    },
    {
        "slug": "atendimento",
        "key": "operation",
        "form": BizStepOperationForm,
        "title": "Como seu negócio atende?",
        "lead": "Se você atende só no endereço do cliente, nenhum endereço aparece na sua página.",
    },
    {
        "slug": "endereco",
        "key": "address",
        "form": BizStepAddressForm,
        "title": "Qual é o endereço comercial?",
        "lead": "Use o endereço do espaço onde os clientes são atendidos. Nunca um endereço residencial.",
    },
    {
        "slug": "funcionamento",
        "key": "hours",
        "form": BizStepHoursForm,
        "title": "Quando você atende?",
        "lead": "Funcionamento do espaço. Os horários de cada profissional são definidos depois, na agenda.",
    },
    {
        "slug": "contato",
        "key": "contact",
        "form": BizStepContactForm,
        "title": "Como os clientes falam com você?",
        "lead": "Uma apresentação curta e pelo menos um contato: telefone ou e-mail comercial.",
    },
    {
        "slug": "fotos",
        "key": "personalize",
        "form": BizStepMediaForm,
        "title": "Mostre seu espaço",
        "lead": "Logo, capa e fotos são opcionais. Dá para fazer agora ou depois, em Editar empresa.",
        "optional": True,
        "multipart": True,
    },
    {
        "slug": "revisar",
        "key": "review",
        "form": BizPublishForm,
        "title": "Revise e publique sua página",
        "lead": "Publicar coloca a página no ar. Reservas dependem de serviços, profissionais e horários, que você organiza depois.",
    },
)
BIZ_STEP_BY_SLUG = {item["slug"]: item for item in BIZ_ONBOARDING_STEPS}
BIZ_SLUG_BY_KEY = {item["key"]: item["slug"] for item in BIZ_ONBOARDING_STEPS}


def _biz_step_url(establishment_id, slug, **params):
    return url_for(
        "business.onboarding_step",
        establishment_id=establishment_id,
        step=slug,
        **params,
    )


def _biz_drafts():
    """Rascunhos nunca publicados do dono (os publicados ficam no painel)."""
    return [
        item for item in owned_establishments(current_user)
        if not item.is_active and item.published_at is None
    ]


def _biz_step_applies(establishment, slug):
    if slug != "endereco":
        return True
    return establishment is None or establishment.operation_mode in {"physical", "hybrid"}


def _biz_neighbour(establishment, index, direction):
    position = index + direction
    while 0 <= position < len(BIZ_ONBOARDING_STEPS):
        slug = BIZ_ONBOARDING_STEPS[position]["slug"]
        if _biz_step_applies(establishment, slug):
            return slug
        position += direction
    return None


def _biz_prefill(form, establishment, slug):
    if slug == "dados":
        form.name.data = establishment.name
        form.category.data = establishment.category
        form.city.data = establishment.city
        form.state.data = establishment.state
    elif slug == "atendimento":
        form.operation_mode.data = establishment.operation_mode
    elif slug == "endereco":
        form.address_line1.data = establishment.address_line1
        form.address_line2.data = establishment.address_line2
        form.neighborhood.data = establishment.neighborhood
        form.postal_code.data = establishment.postal_code
    elif slug == "funcionamento":
        form.business_hours_mode.data = establishment.business_hours_mode
        for day, periods in (establishment.business_hours or {}).items():
            if periods:
                getattr(form, f"{day}_start").data = periods[0].get("start")
                getattr(form, f"{day}_end").data = periods[0].get("end")
    elif slug == "contato":
        form.description.data = establishment.description
        form.phone.data = establishment.phone
        form.whatsapp_enabled.data = bool(establishment.whatsapp_enabled) or not establishment.phone
        form.instagram.data = establishment.instagram
        # D-ONB-05: o e-mail da conta é só sugestão, visível e editável;
        # passa a valer quando a pessoa salva esta etapa.
        form.email.data = establishment.email or current_user.email
    elif slug == "fotos":
        form.logo_focus_x.data = establishment.logo_focus_x
        form.logo_focus_y.data = establishment.logo_focus_y
        form.cover_focus_x.data = establishment.cover_focus_x
        form.cover_focus_y.data = establishment.cover_focus_y


def _biz_hours(form):
    weekly = {}
    for day, _label in WEEKDAY_FIELDS:
        start = (getattr(form, f"{day}_start").data or "").strip()
        end = (getattr(form, f"{day}_end").data or "").strip()
        if start or end:
            weekly[day] = [{"start": start, "end": end}]
    return weekly


def _biz_changes(form, slug):
    if slug == "dados":
        return {
            "name": form.name.data,
            "category": form.category.data,
            "city": form.city.data,
            "state": form.state.data,
        }
    if slug == "atendimento":
        return {"operation_mode": form.operation_mode.data}
    if slug == "endereco":
        return {
            "address_line1": form.address_line1.data,
            "address_line2": form.address_line2.data or None,
            "neighborhood": form.neighborhood.data or None,
            "postal_code": form.postal_code.data or None,
        }
    if slug == "funcionamento":
        if form.business_hours_mode.data == "fixed_hours":
            return {"business_hours_mode": "fixed_hours", "business_hours": _biz_hours(form)}
        # Sob agendamento: a grade deixa de valer (DEC-ID-103).
        return {"business_hours_mode": "scheduled", "business_hours": None}
    if slug == "contato":
        phone = (form.phone.data or "").strip()
        return {
            "description": form.description.data,
            "phone": phone or None,
            "whatsapp_enabled": bool(form.whatsapp_enabled.data and phone),
            "commercial_email": (form.email.data or "").strip().lower() or None,
        }
    return {}


def _save_biz_media_step(form, establishment):
    gallery_files = _files_with_names(form.gallery_files.data)
    room = max(0, 10 - len(establishment.gallery_items))
    if len(gallery_files) > room:
        form.gallery_files.errors.append(
            f"Você pode adicionar mais {room} foto(s) agora."
            if room
            else "A galeria já tem 10 fotos. Remova alguma em Editar empresa."
        )
        return False

    replaced_media = []
    try:
        with UploadBatch() as uploads:
            logo_url = uploads.save_image(form.logo_file.data, "establishments/logos")
            cover_url = uploads.save_image(form.cover_file.data, "establishments/covers")
            gallery_urls = uploads.save_many_images(
                gallery_files, "establishments/gallery", max_files=10,
            )
            establishment.logo_focus_x = _focus_value(form.logo_focus_x.data)
            establishment.logo_focus_y = _focus_value(form.logo_focus_y.data)
            establishment.cover_focus_x = _focus_value(form.cover_focus_x.data)
            establishment.cover_focus_y = _focus_value(form.cover_focus_y.data)
            if logo_url:
                replaced_media.append(establishment.logo_url)
                establishment.logo_url = logo_url
            if cover_url:
                replaced_media.append(establishment.cover_url)
                establishment.cover_url = cover_url
            start_order = len(establishment.gallery_items)
            for offset, image_url in enumerate(gallery_urls):
                db.session.add(EstablishmentGalleryItem(
                    establishment=establishment,
                    image_url=image_url,
                    sort_order=start_order + offset,
                ))
            db.session.commit()
            uploads.commit()
    except ValueError as exc:
        db.session.rollback()
        form.gallery_files.errors.append(str(exc))
        return False
    except (OSError, SQLAlchemyError):
        _record_upload_failure(
            form.gallery_files,
            "Não foi possível salvar as fotos agora. Tente novamente.",
            "Falha ao salvar fotos do onboarding de estabelecimento.",
        )
        return False

    delete_uploaded_files(replaced_media)
    return True


def _render_biz_step(definition, establishment, form, *, step_error=None,
                     back_to_review=False, status=200):
    index = BIZ_ONBOARDING_STEPS.index(definition)
    previous = _biz_neighbour(establishment, index, -1)
    if establishment is None:
        previous_url = url_for("business.onboarding")
        step_url = lambda slug, **params: url_for("business.onboarding_new")  # noqa: E731
        review_url = url_for("business.onboarding_new")
    else:
        previous_url = (
            _biz_step_url(establishment.id, previous) if previous
            else url_for("business.onboarding")
        )

        def step_url(slug, **params):
            return _biz_step_url(establishment.id, slug, **params)

        review_url = step_url("revisar")
    return render_template(
        "platform/biz-onboarding-step.html",
        form=form,
        step=definition,
        steps=BIZ_ONBOARDING_STEPS,
        step_index=index,
        step_total=len(BIZ_ONBOARDING_STEPS),
        previous_url=previous_url,
        step_url=step_url,
        review_url=review_url,
        onb_kicker="Cadastro do estabelecimento",
        back_to_review=back_to_review,
        establishment=establishment,
        journey=business_journey(establishment) if establishment is not None else None,
        weekdays=WEEKDAY_FIELDS,
        step_error=step_error,
        current_page="for-professionals",
    ), status


@business_bp.get("/onboarding")
@login_required
def onboarding():
    """Começar ou continuar: rascunhos do dono e "criar outro"."""
    drafts = _biz_drafts()
    if not drafts:
        return redirect(url_for("business.onboarding_new"))
    return render_template(
        "platform/biz-onboarding-start.html",
        drafts=[(item, business_journey(item)) for item in drafts],
        current_page="for-professionals",
    )


@business_bp.get("/onboarding/<int:establishment_id>")
@login_required
def onboarding_resume(establishment_id):
    """Retoma um rascunho na primeira etapa pendente."""
    try:
        establishment = owned_establishment(current_user, establishment_id)
    except MobileOnboardingError:
        abort(404)
    if establishment.is_active or establishment.published_at is not None:
        return redirect(url_for("business.dashboard", slug=establishment.slug))
    return redirect(_biz_step_url(
        establishment.id, BIZ_SLUG_BY_KEY[business_journey(establishment)["currentStep"]],
    ))


@business_bp.route("/onboarding/novo", methods=["GET", "POST"])
@login_required
def onboarding_new():
    definition = BIZ_STEP_BY_SLUG["dados"]
    form = BizStepBasicsForm()
    step_error = None
    if form.validate_on_submit():
        try:
            establishment = create_establishment_draft(
                user=current_user,
                name=form.name.data,
                category=form.category.data,
                city=form.city.data,
                state=form.state.data,
            )
        except MobileOnboardingError as exc:
            step_error = str(exc)
        else:
            return redirect(_biz_step_url(establishment.id, "atendimento"))
    return _render_biz_step(
        definition, None, form, step_error=step_error,
        status=422 if request.method == "POST" else 200,
    )


@business_bp.route(
    "/onboarding/<int:establishment_id>/<step>",
    methods=["GET", "POST"],
)
@login_required
def onboarding_step(establishment_id, step):
    definition = BIZ_STEP_BY_SLUG.get(step)
    if definition is None:
        abort(404)
    try:
        establishment = owned_establishment(current_user, establishment_id)
    except MobileOnboardingError:
        abort(404)
    if establishment.is_active:
        flash(
            "Esta página já está publicada. Para mudar algo, use Editar empresa.",
            "info",
        )
        return redirect(url_for("business.dashboard", slug=establishment.slug))
    if establishment.published_at is not None:
        flash(BIZ_LOCKED_MESSAGE, "info")
        return redirect(url_for("business.dashboard", slug=establishment.slug))

    index = BIZ_ONBOARDING_STEPS.index(definition)
    back_to_review = request.args.get("retorno") == "revisar" and step != "revisar"
    if not _biz_step_applies(establishment, step):
        # Endereço só para físico ou híbrido (F2): pula para a próxima.
        return redirect(_biz_step_url(
            establishment.id,
            "revisar" if back_to_review else _biz_neighbour(establishment, index, 1),
        ))

    form = definition["form"]()
    step_error = None
    if request.method == "GET":
        _biz_prefill(form, establishment, step)

    if form.validate_on_submit():
        if step == "revisar":
            try:
                publish_establishment(user=current_user, establishment_id=establishment.id)
            except OnboardingConflict as exc:
                step_error = str(exc)
            else:
                return redirect(url_for(
                    "business.onboarding_done", establishment_id=establishment.id,
                ))
        elif step == "fotos":
            if _save_biz_media_step(form, establishment):
                return redirect(_biz_step_url(establishment.id, "revisar"))
        else:
            hours_ok = True
            changes = _biz_changes(form, step)
            if step == "funcionamento" and changes["business_hours_mode"] == "fixed_hours":
                hours_ok = valid_business_hours(changes["business_hours"])
                if not hours_ok:
                    form.business_hours_mode.errors.append(
                        "Informe abertura e fechamento válidos (HH:MM) em pelo menos um dia."
                    )
            if hours_ok:
                try:
                    update_establishment_draft(
                        user=current_user,
                        establishment_id=establishment.id,
                        changes=changes,
                    )
                except MobileOnboardingError as exc:
                    step_error = str(exc)
                else:
                    if back_to_review:
                        return redirect(_biz_step_url(establishment.id, "revisar"))
                    return redirect(_biz_step_url(
                        establishment.id, _biz_neighbour(establishment, index, 1),
                    ))

    return _render_biz_step(
        definition, establishment, form, step_error=step_error,
        back_to_review=back_to_review,
        status=422 if request.method == "POST" else 200,
    )


@business_bp.get("/onboarding/<int:establishment_id>/concluido")
@login_required
def onboarding_done(establishment_id):
    try:
        establishment = owned_establishment(current_user, establishment_id)
    except MobileOnboardingError:
        abort(404)
    if not establishment.is_active:
        return redirect(_biz_step_url(establishment.id, "revisar"))
    return render_template(
        "platform/biz-onboarding-done.html",
        establishment=establishment,
        current_page="for-professionals",
    )


@business_bp.route(
    "/<slug>/painel",
    methods=["GET", "POST"],
)
@login_required
def dashboard(slug):
    establishment, access = (
        _managed_establishment(slug)
    )
    team_form = TeamMemberForm()

    if team_form.validate_on_submit():
        email = (
            team_form.email.data.strip().lower()
        )
        user = db.session.scalar(
            select(User).where(User.email == email)
        )

        if (
            user is None
            or user.professional_profile is None
        ):
            team_form.email.errors.append(
                (
                    "Esse e-mail ainda não possui um "
                    "perfil profissional IDDUN."
                )
            )
        else:
            professional = user.professional_profile

            membership = db.session.scalar(
                select(
                    ProfessionalEstablishmentMembership
                ).where(
                    ProfessionalEstablishmentMembership.professional_id
                    == professional.id,
                    ProfessionalEstablishmentMembership.establishment_id
                    == establishment.id,
                )
            )

            if (
                membership
                and membership.status
                == MembershipStatus.ACTIVE
            ):
                team_form.email.errors.append(
                    (
                        "Esse profissional já faz parte "
                        "da equipe."
                    )
                )

            elif (
                membership
                and membership.status
                == MembershipStatus.PENDING
            ):
                team_form.email.errors.append(
                    (
                        "Este profissional já possui "
                        "um convite pendente."
                    )
                )

            else:
                role_name = (
                    team_form.role_name.data or ""
                ).strip() or professional.primary_specialty

                if membership is None:
                    membership = (
                        ProfessionalEstablishmentMembership(
                            professional=professional,
                            establishment=establishment,
                            role_name=role_name,
                            status=(
                                MembershipStatus.PENDING
                            ),
                            is_primary=False,
                        )
                    )
                    db.session.add(membership)
                else:
                    membership.status = (
                        MembershipStatus.PENDING
                    )
                    membership.role_name = role_name
                    membership.is_primary = False
                    membership.started_at = None
                    membership.ended_at = None

                db.session.commit()

                flash(
                    (
                        f"Convite enviado para "
                        f"{professional.display_name}. "
                        f"O vínculo será ativado após "
                        f"o aceite."
                    ),
                    "success",
                )
                return redirect(
                    url_for(
                        "business.dashboard",
                        slug=slug,
                    )
                )

    confirmed_bookings = sum(
        1
        for booking in establishment.bookings
        if booking.status == BookingStatus.CONFIRMED
    )
    published_experiences = sum(
        1
        for item in establishment.experiences
        if item.status == ExperienceStatus.PUBLISHED
    )
    catalog_preview = db.session.scalars(
        select(Experience)
        .where(
            Experience.establishment_id == establishment.id,
            Experience.status == ExperienceStatus.PUBLISHED,
        )
        .order_by(Experience.created_at.desc(), Experience.id.desc())
        .limit(6)
    ).all()

    reputation = reputation_summary(
        establishment.reviews_received
    )
    whatsapp_clicks = sum(
        1
        for item in establishment.contact_clicks
        if item.channel == "whatsapp"
    )

    return render_template(
        "platform/business-dashboard.html",
        establishment=establishment,
        access=access,
        team_form=team_form,
        confirmed_bookings=confirmed_bookings,
        published_experiences=published_experiences,
        catalog_preview=catalog_preview,
        reputation=reputation,
        whatsapp_clicks=whatsapp_clicks,
        current_page="business-dashboard",
    )


@business_bp.get("/<slug>/servicos")
@login_required
def services(slug):
    establishment, access = _managed_establishment(slug)
    items = db.session.scalars(
        select(Experience)
        .where(Experience.establishment_id == establishment.id)
        .order_by(Experience.created_at.desc(), Experience.id.desc())
    ).all()
    counts = {
        status: sum(1 for item in items if item.status == status)
        for status in (
            ExperienceStatus.DRAFT,
            ExperienceStatus.PUBLISHED,
            ExperienceStatus.PAUSED,
            ExperienceStatus.ARCHIVED,
        )
    }
    return render_template(
        "platform/business-services.html",
        establishment=establishment,
        access=access,
        experiences=items,
        counts=counts,
        ExperienceStatus=ExperienceStatus,
        current_page="business-services",
    )


@business_bp.get("/<slug>/reservas")
@login_required
def bookings(slug):
    establishment, access = _managed_establishment(slug)
    selected_status = (request.args.get("status") or "").strip().lower()
    allowed_statuses = {value for value, _ in BookingStatus.CHOICES}
    if selected_status and selected_status not in allowed_statuses:
        abort(400)

    raw_date = (request.args.get("date") or "").strip()
    selected_date = None
    if raw_date:
        try:
            selected_date = date.fromisoformat(raw_date)
        except ValueError:
            abort(400)

    query = (
        select(Booking)
        .join(ExperienceSlot, Booking.slot_id == ExperienceSlot.id)
        .where(Booking.establishment_id == establishment.id)
    )
    if selected_status:
        query = query.where(Booking.status == selected_status)
    if selected_date:
        start = local_naive_to_utc(
            datetime.combine(selected_date, time.min), establishment.timezone
        )
        end = local_naive_to_utc(
            datetime.combine(selected_date + timedelta(days=1), time.min),
            establishment.timezone,
        )
        query = query.where(
            ExperienceSlot.starts_at >= start,
            ExperienceSlot.starts_at < end,
        )
    items = db.session.scalars(
        query.order_by(ExperienceSlot.starts_at.desc(), Booking.id.desc())
        .limit(100)
    ).all()
    rows = [
        {
            "booking": item,
            "local_start": to_local(item.slot.starts_at, establishment.timezone),
        }
        for item in items
    ]
    return render_template(
        "platform/business-bookings.html",
        establishment=establishment,
        access=access,
        rows=rows,
        selected_status=selected_status,
        selected_date=raw_date,
        status_choices=BookingStatus.CHOICES,
        current_page="business-bookings",
    )


@business_bp.get("/<slug>/indicadores")
@login_required
def insights(slug):
    establishment, access = _managed_establishment(slug)
    metrics = business_operation_insights(establishment.id)
    return render_template(
        "platform/business-insights.html",
        establishment=establishment,
        access=access,
        metrics=metrics,
        BookingStatus=BookingStatus,
        current_page="business-insights",
    )


@business_bp.route(
    "/<slug>/editar",
    methods=["GET", "POST"],
)
@login_required
def edit(slug):
    establishment, access = (
        _managed_establishment(slug)
    )
    form = BusinessEditForm(
        obj=establishment
    )

    if form.validate_on_submit():
        replaced_media = []

        try:
            with UploadBatch() as uploads:
                logo_url = uploads.save_image(
                    form.logo_file.data,
                    "establishments/logos",
                )
                cover_url = uploads.save_image(
                    form.cover_file.data,
                    "establishments/covers",
                )
                gallery_urls = (
                    uploads.save_many_images(
                        form.gallery_files.data,
                        "establishments/gallery",
                        max_files=10,
                    )
                )

                establishment.name = (
                    form.name.data.strip()
                )
                establishment.category = (
                    form.category.data
                )
                establishment.visual_theme = (
                    _theme_for_business(
                        form.category.data
                    )
                )
                establishment.description = (
                    form.description.data.strip()
                )
                establishment.phone = (
                    form.phone.data or ""
                ).strip() or None
                establishment.whatsapp_enabled = bool(
                    form.whatsapp_enabled.data
                    and establishment.phone
                )
                establishment.email = (
                    form.email.data or ""
                ).strip().lower() or None
                establishment.instagram = (
                    form.instagram.data or ""
                ).strip() or None
                establishment.address_line1 = (
                    form.address_line1.data.strip()
                )
                establishment.address_line2 = (
                    form.address_line2.data or ""
                ).strip() or None
                establishment.neighborhood = (
                    form.neighborhood.data or ""
                ).strip() or None
                establishment.city = (
                    form.city.data.strip()
                )
                establishment.state = (
                    form.state.data.strip().upper()
                )
                establishment.postal_code = (
                    form.postal_code.data or ""
                ).strip() or None
                establishment.logo_focus_x = (
                    _focus_value(
                        form.logo_focus_x.data
                    )
                )
                establishment.logo_focus_y = (
                    _focus_value(
                        form.logo_focus_y.data
                    )
                )
                establishment.cover_focus_x = (
                    _focus_value(
                        form.cover_focus_x.data
                    )
                )
                establishment.cover_focus_y = (
                    _focus_value(
                        form.cover_focus_y.data
                    )
                )

                if logo_url:
                    replaced_media.append(
                        establishment.logo_url
                    )
                    establishment.logo_url = logo_url

                if cover_url:
                    replaced_media.append(
                        establishment.cover_url
                    )
                    establishment.cover_url = (
                        cover_url
                    )

                start_order = len(
                    establishment.gallery_items
                )

                for offset, image_url in enumerate(
                    gallery_urls
                ):
                    db.session.add(
                        EstablishmentGalleryItem(
                            establishment=(
                                establishment
                            ),
                            image_url=image_url,
                            sort_order=(
                                start_order + offset
                            ),
                        )
                    )

                db.session.flush()

                establishment.onboarding_completed = (
                    establishment.ready_to_publish
                )

                # Rascunho só vai ao ar por publicação explícita (F1).
                if (
                    establishment.is_active
                    and establishment.onboarding_completed
                    and establishment.published_at
                    is None
                ):
                    establishment.published_at = (
                        utcnow()
                    )

                db.session.commit()
                uploads.commit()

        except ValueError as exc:
            db.session.rollback()
            form.gallery_files.errors.append(
                str(exc)
            )

        except (OSError, SQLAlchemyError):
            _record_upload_failure(
                form.gallery_files,
                (
                    "Não foi possível atualizar a "
                    "página da empresa agora. "
                    "Tente novamente."
                ),
                (
                    "Falha ao atualizar o "
                    "estabelecimento."
                ),
            )

        else:
            delete_uploaded_files(replaced_media)

            flash(
                "Página da empresa atualizada.",
                "success",
            )
            return redirect(
                url_for(
                    "business.dashboard",
                    slug=slug,
                )
            )

    return render_template(
        "platform/business-edit.html",
        form=form,
        establishment=establishment,
        access=access,
        current_page="business-dashboard",
    )


@business_bp.post(
    "/<slug>/equipe/"
    "<int:membership_id>/remover"
)
@login_required
def remove_team_member(
    slug,
    membership_id,
):
    establishment, access = (
        _managed_establishment(slug)
    )
    membership = db.session.get(
        ProfessionalEstablishmentMembership,
        membership_id,
    )

    if (
        membership is None
        or membership.establishment_id
        != establishment.id
    ):
        abort(404)

    membership.status = (
        MembershipStatus.INACTIVE
    )
    membership.is_primary = False
    membership.ended_at = datetime.now().date()

    db.session.commit()

    flash(
        "Profissional removido da equipe ativa.",
        "success",
    )
    return redirect(
        url_for(
            "business.dashboard",
            slug=slug,
        )
    )


@business_bp.post(
    "/<slug>/galeria/<int:item_id>/remover"
)
@login_required
def remove_gallery_item(
    slug,
    item_id,
):
    establishment, access = (
        _managed_establishment(slug)
    )
    item = db.session.get(
        EstablishmentGalleryItem,
        item_id,
    )

    if (
        item is None
        or item.establishment_id
        != establishment.id
    ):
        abort(404)

    image_url = item.image_url

    db.session.delete(item)
    db.session.commit()

    delete_uploaded_file(image_url)

    flash(
        "Imagem removida da galeria.",
        "success",
    )
    return redirect(
        url_for(
            "business.edit",
            slug=slug,
        )
        + "#galeria"
    )