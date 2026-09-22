from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from app.extensions import db
from app.forms.platform import (
    BusinessEditForm,
    BusinessOnboardingForm,
    ProfessionalCertificationForm,
    ProfessionalEditForm,
    ProfessionalOnboardingForm,
    TeamMemberForm,
    WorkModeChoiceForm,
)
from app.models.booking import BookingStatus
from app.models.certification import ProfessionalCertification
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentGalleryItem,
    EstablishmentUserAccess,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.experience import ExperienceStatus
from app.models.professional import ProfessionalPortfolioItem, ProfessionalProfile
from app.models.reputation import ContactClick
from app.models.user import User
from app.services.media_service import save_uploaded_certificate, save_uploaded_image
from app.services.reputation_service import reputation_summary
from app.services.slug_service import unique_public_handle


professional_bp = Blueprint("professional", __name__, url_prefix="/pro")
business_bp = Blueprint("business", __name__, url_prefix="/business")


def utcnow():
    return datetime.now(timezone.utc)


def _files_with_names(items):
    return [item for item in (items or []) if item and getattr(item, "filename", "")]


def _save_many(files, folder, max_files=8):
    selected = _files_with_names(files)[:max_files]
    return [save_uploaded_image(item, folder) for item in selected]


def _theme_for_business(category):
    if category == "barbearia":
        return "barber"
    if category == "tatuagem":
        return "tattoo"
    return "beauty"


def _focus_value(value):
    """Normalize media focal points even when an older client omits the field."""
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 50


def _managed_establishment(slug):
    establishment = db.session.scalar(select(Establishment).where(Establishment.slug == slug))
    if establishment is None:
        abort(404)

    access = db.session.scalar(
        select(EstablishmentUserAccess).where(
            EstablishmentUserAccess.establishment_id == establishment.id,
            EstablishmentUserAccess.user_id == current_user.id,
            EstablishmentUserAccess.status == EstablishmentAccessStatus.ACTIVE,
        )
    )
    if access is None:
        abort(403)
    return establishment, access


@professional_bp.route("/comecar", methods=["GET", "POST"])
@login_required
def start():
    form = WorkModeChoiceForm()
    if form.validate_on_submit():
        if form.mode.data == "business":
            return redirect(url_for("business.onboarding"))
        if current_user.professional_profile:
            return redirect(url_for("professional.dashboard"))
        return redirect(url_for("professional.onboarding"))

    return render_template(
        "platform/start.html",
        form=form,
        current_page="for-professionals",
    )


@professional_bp.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    if current_user.professional_profile:
        return redirect(url_for("professional.dashboard"))

    form = ProfessionalOnboardingForm()
    if request.method == "GET":
        form.display_name.data = current_user.name

    if form.validate_on_submit():
        portfolio_files = _files_with_names(form.portfolio_files.data)
        if len(portfolio_files) < 3:
            form.portfolio_files.errors.append("Adicione pelo menos 3 fotos do seu trabalho para publicar o perfil.")
        else:
            try:
                avatar_url = save_uploaded_image(form.avatar_file.data, "professionals")
                cover_url = save_uploaded_image(form.cover_file.data, "professionals/covers")
                portfolio_urls = _save_many(portfolio_files, "professionals/portfolio", max_files=8)
            except ValueError as exc:
                form.portfolio_files.errors.append(str(exc))
            else:
                profile = ProfessionalProfile(
                    user=current_user,
                    display_name=form.display_name.data.strip(),
                    slug=unique_public_handle(form.display_name.data, resource_type="professional"),
                    headline=(form.headline.data or "").strip() or None,
                    primary_specialty=form.primary_specialty.data.strip(),
                    specialties_text=(form.specialties_text.data or "").strip() or None,
                    bio=form.bio.data.strip(),
                    phone=(form.phone.data or "").strip() or None,
                    whatsapp_enabled=bool(form.whatsapp_enabled.data and form.phone.data),
                    instagram=(form.instagram.data or "").strip() or None,
                    city=form.city.data.strip(),
                    state=form.state.data.strip().upper(),
                    avatar_url=avatar_url,
                    cover_url=cover_url,
                    avatar_focus_x=_focus_value(form.avatar_focus_x.data),
                    avatar_focus_y=_focus_value(form.avatar_focus_y.data),
                    cover_focus_x=_focus_value(form.cover_focus_x.data),
                    cover_focus_y=_focus_value(form.cover_focus_y.data),
                    visual_theme=form.visual_theme.data,
                    plan_tier="free",
                    onboarding_completed=True,
                    published_at=utcnow(),
                    claimed_at=utcnow(),
                )
                db.session.add(profile)
                db.session.flush()
                for index, image_url in enumerate(portfolio_urls):
                    db.session.add(
                        ProfessionalPortfolioItem(
                            professional=profile,
                            image_url=image_url,
                            sort_order=index,
                        )
                    )
                db.session.commit()
                flash("Seu perfil profissional está no ar. Bem-vindo ao IDDUN Pro.", "success")
                return redirect(url_for("professional.dashboard"))

    return render_template(
        "platform/professional-onboarding.html",
        form=form,
        current_page="for-professionals",
    )


@professional_bp.route("")
@professional_bp.route("/painel")
@login_required
def dashboard():
    profile = current_user.professional_profile
    if profile is None:
        return redirect(url_for("professional.start"))

    confirmed_bookings = sum(1 for booking in profile.bookings if booking.status == BookingStatus.CONFIRMED)
    published_experiences = sum(1 for item in profile.experiences if item.status == ExperienceStatus.PUBLISHED)
    reputation = reputation_summary(profile.reviews_received)
    whatsapp_clicks = sum(1 for item in profile.contact_clicks if item.channel == "whatsapp")
    return render_template(
        "platform/professional-dashboard.html",
        profile=profile,
        confirmed_bookings=confirmed_bookings,
        published_experiences=published_experiences,
        reputation=reputation,
        whatsapp_clicks=whatsapp_clicks,
        current_page="professional-dashboard",
    )


@professional_bp.route("/perfil/editar", methods=["GET", "POST"])
@login_required
def edit_profile():
    profile = current_user.professional_profile
    if profile is None:
        return redirect(url_for("professional.onboarding"))

    form = ProfessionalEditForm(obj=profile)
    if form.validate_on_submit():
        try:
            avatar_url = save_uploaded_image(form.avatar_file.data, "professionals")
            cover_url = save_uploaded_image(form.cover_file.data, "professionals/covers")
            new_portfolio = _save_many(form.portfolio_files.data, "professionals/portfolio", max_files=8)
        except ValueError as exc:
            form.portfolio_files.errors.append(str(exc))
        else:
            profile.display_name = form.display_name.data.strip()
            profile.headline = (form.headline.data or "").strip() or None
            profile.primary_specialty = form.primary_specialty.data.strip()
            profile.specialties_text = (form.specialties_text.data or "").strip() or None
            profile.bio = form.bio.data.strip()
            profile.phone = (form.phone.data or "").strip() or None
            profile.whatsapp_enabled = bool(form.whatsapp_enabled.data and profile.phone)
            profile.instagram = (form.instagram.data or "").strip() or None
            profile.city = form.city.data.strip()
            profile.state = form.state.data.strip().upper()
            profile.visual_theme = form.visual_theme.data
            profile.avatar_focus_x = _focus_value(form.avatar_focus_x.data)
            profile.avatar_focus_y = _focus_value(form.avatar_focus_y.data)
            profile.cover_focus_x = _focus_value(form.cover_focus_x.data)
            profile.cover_focus_y = _focus_value(form.cover_focus_y.data)
            if avatar_url:
                profile.avatar_url = avatar_url
            if cover_url:
                profile.cover_url = cover_url
            start_order = len(profile.portfolio_items)
            for offset, image_url in enumerate(new_portfolio):
                db.session.add(
                    ProfessionalPortfolioItem(
                        professional=profile,
                        image_url=image_url,
                        sort_order=start_order + offset,
                    )
                )
            db.session.flush()
            profile.onboarding_completed = profile.ready_to_publish
            if profile.onboarding_completed and profile.published_at is None:
                profile.published_at = utcnow()
            db.session.commit()
            flash("Perfil profissional atualizado.", "success")
            return redirect(url_for("professional.dashboard"))

    return render_template(
        "platform/professional-edit.html",
        form=form,
        profile=profile,
        current_page="professional-dashboard",
    )


@professional_bp.post("/portfolio/<int:item_id>/remover")
@login_required
def remove_portfolio_item(item_id):
    profile = current_user.professional_profile
    if profile is None:
        abort(404)
    item = db.session.get(ProfessionalPortfolioItem, item_id)
    if item is None or item.professional_id != profile.id:
        abort(404)
    profile.portfolio_items.remove(item)
    db.session.flush()
    profile.onboarding_completed = profile.ready_to_publish
    if not profile.onboarding_completed:
        profile.published_at = None
    db.session.commit()
    flash("Imagem removida do portfólio.", "success")
    return redirect(url_for("professional.edit_profile"))


@professional_bp.post("/vinculos/<int:membership_id>/aceitar")
@login_required
def accept_membership(membership_id):
    profile = current_user.professional_profile
    membership = db.session.get(ProfessionalEstablishmentMembership, membership_id)
    if profile is None or membership is None or membership.professional_id != profile.id:
        abort(404)
    if membership.status != MembershipStatus.PENDING:
        flash("Este convite não está mais pendente.", "info")
        return redirect(url_for("professional.dashboard"))

    has_active_membership = any(item.status == MembershipStatus.ACTIVE for item in profile.memberships)
    membership.status = MembershipStatus.ACTIVE
    membership.started_at = membership.started_at or datetime.now().date()
    membership.ended_at = None
    membership.is_primary = not has_active_membership
    db.session.commit()
    flash(f"Vínculo com {membership.establishment.name} confirmado.", "success")
    return redirect(url_for("professional.dashboard"))


@professional_bp.post("/vinculos/<int:membership_id>/recusar")
@login_required
def reject_membership(membership_id):
    profile = current_user.professional_profile
    membership = db.session.get(ProfessionalEstablishmentMembership, membership_id)
    if profile is None or membership is None or membership.professional_id != profile.id:
        abort(404)
    if membership.status != MembershipStatus.PENDING:
        flash("Este convite não está mais pendente.", "info")
        return redirect(url_for("professional.dashboard"))

    membership.status = MembershipStatus.REJECTED
    membership.is_primary = False
    membership.ended_at = datetime.now().date()
    db.session.commit()
    flash(f"Convite de {membership.establishment.name} recusado.", "info")
    return redirect(url_for("professional.dashboard"))


@professional_bp.route("/certificacoes", methods=["GET", "POST"])
@login_required
def certifications():
    profile = current_user.professional_profile
    if profile is None:
        return redirect(url_for("professional.onboarding"))

    form = ProfessionalCertificationForm()
    if form.validate_on_submit():
        if form.expires_at.data and form.issued_at.data and form.expires_at.data < form.issued_at.data:
            form.expires_at.errors.append("A validade não pode ser anterior à emissão.")
        else:
            try:
                document_url = save_uploaded_certificate(form.document_file.data)
            except ValueError as exc:
                form.document_file.errors.append(str(exc))
            else:
                certificate = ProfessionalCertification(
                    professional=profile,
                    title=form.title.data.strip(),
                    issuer=form.issuer.data.strip(),
                    issued_at=form.issued_at.data,
                    expires_at=form.expires_at.data,
                    credential_id=(form.credential_id.data or "").strip() or None,
                    verification_url=(form.verification_url.data or "").strip() or None,
                    document_url=document_url,
                    is_public=bool(form.is_public.data),
                )
                db.session.add(certificate)
                db.session.commit()
                flash("Certificação adicionada ao seu perfil.", "success")
                return redirect(url_for("professional.certifications"))

    return render_template(
        "platform/professional-certifications.html",
        form=form,
        profile=profile,
        current_page="professional-dashboard",
    )


@professional_bp.post("/certificacoes/<int:certification_id>/remover")
@login_required
def remove_certification(certification_id):
    profile = current_user.professional_profile
    if profile is None:
        abort(404)
    certificate = db.session.get(ProfessionalCertification, certification_id)
    if certificate is None or certificate.professional_id != profile.id:
        abort(404)
    db.session.delete(certificate)
    db.session.commit()
    flash("Certificação removida.", "info")
    return redirect(url_for("professional.certifications"))


@business_bp.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    form = BusinessOnboardingForm()
    if request.method == "GET":
        form.email.data = current_user.email

    if form.validate_on_submit():
        try:
            logo_url = save_uploaded_image(form.logo_file.data, "establishments/logos")
            cover_url = save_uploaded_image(form.cover_file.data, "establishments/covers")
            gallery_urls = _save_many(form.gallery_files.data, "establishments/gallery", max_files=10)
        except ValueError as exc:
            form.gallery_files.errors.append(str(exc))
        else:
            establishment = Establishment(
                name=form.name.data.strip(),
                slug=unique_public_handle(form.name.data, resource_type="establishment"),
                description=form.description.data.strip(),
                category=form.category.data,
                visual_theme=_theme_for_business(form.category.data),
                plan_tier="free",
                onboarding_completed=True,
                published_at=utcnow(),
                phone=(form.phone.data or "").strip() or None,
                whatsapp_enabled=bool(form.whatsapp_enabled.data and form.phone.data),
                email=(form.email.data or "").strip().lower() or None,
                instagram=(form.instagram.data or "").strip() or None,
                address_line1=form.address_line1.data.strip(),
                address_line2=(form.address_line2.data or "").strip() or None,
                neighborhood=(form.neighborhood.data or "").strip() or None,
                city=form.city.data.strip(),
                state=form.state.data.strip().upper(),
                postal_code=(form.postal_code.data or "").strip() or None,
                logo_url=logo_url,
                cover_url=cover_url,
                logo_focus_x=_focus_value(form.logo_focus_x.data),
                logo_focus_y=_focus_value(form.logo_focus_y.data),
                cover_focus_x=_focus_value(form.cover_focus_x.data),
                cover_focus_y=_focus_value(form.cover_focus_y.data),
            )
            db.session.add(establishment)
            db.session.flush()
            db.session.add(
                EstablishmentUserAccess(
                    user=current_user,
                    establishment=establishment,
                    role=EstablishmentAccessRole.OWNER,
                    status=EstablishmentAccessStatus.ACTIVE,
                )
            )
            for index, image_url in enumerate(gallery_urls):
                db.session.add(
                    EstablishmentGalleryItem(
                        establishment=establishment,
                        image_url=image_url,
                        sort_order=index,
                    )
                )
            db.session.commit()
            flash("Página da empresa criada. Agora monte sua equipe no IDDUN Business.", "success")
            return redirect(url_for("business.dashboard", slug=establishment.slug))

    return render_template(
        "platform/business-onboarding.html",
        form=form,
        current_page="for-professionals",
    )


@business_bp.route("/<slug>/painel", methods=["GET", "POST"])
@login_required
def dashboard(slug):
    establishment, access = _managed_establishment(slug)
    team_form = TeamMemberForm()

    if team_form.validate_on_submit():
        email = team_form.email.data.strip().lower()
        user = db.session.scalar(select(User).where(User.email == email))
        if user is None or user.professional_profile is None:
            team_form.email.errors.append("Esse e-mail ainda não possui um perfil profissional IDDUN.")
        else:
            professional = user.professional_profile
            membership = db.session.scalar(
                select(ProfessionalEstablishmentMembership).where(
                    ProfessionalEstablishmentMembership.professional_id == professional.id,
                    ProfessionalEstablishmentMembership.establishment_id == establishment.id,
                )
            )
            if membership and membership.status == MembershipStatus.ACTIVE:
                team_form.email.errors.append("Esse profissional já faz parte da equipe.")
            elif membership and membership.status == MembershipStatus.PENDING:
                team_form.email.errors.append("Este profissional já possui um convite pendente.")
            else:
                if membership is None:
                    membership = ProfessionalEstablishmentMembership(
                        professional=professional,
                        establishment=establishment,
                        role_name=(team_form.role_name.data or "").strip() or professional.primary_specialty,
                        status=MembershipStatus.PENDING,
                        is_primary=False,
                    )
                    db.session.add(membership)
                else:
                    membership.status = MembershipStatus.PENDING
                    membership.role_name = (team_form.role_name.data or "").strip() or professional.primary_specialty
                    membership.is_primary = False
                    membership.started_at = None
                    membership.ended_at = None
                db.session.commit()
                flash(f"Convite enviado para {professional.display_name}. O vínculo será ativado após o aceite.", "success")
                return redirect(url_for("business.dashboard", slug=slug))

    confirmed_bookings = sum(1 for booking in establishment.bookings if booking.status == BookingStatus.CONFIRMED)
    published_experiences = sum(1 for item in establishment.experiences if item.status == ExperienceStatus.PUBLISHED)
    reputation = reputation_summary(establishment.reviews_received)
    whatsapp_clicks = sum(1 for item in establishment.contact_clicks if item.channel == "whatsapp")
    return render_template(
        "platform/business-dashboard.html",
        establishment=establishment,
        access=access,
        team_form=team_form,
        confirmed_bookings=confirmed_bookings,
        published_experiences=published_experiences,
        reputation=reputation,
        whatsapp_clicks=whatsapp_clicks,
        current_page="business-dashboard",
    )


@business_bp.route("/<slug>/editar", methods=["GET", "POST"])
@login_required
def edit(slug):
    establishment, access = _managed_establishment(slug)
    form = BusinessEditForm(obj=establishment)
    if form.validate_on_submit():
        try:
            logo_url = save_uploaded_image(form.logo_file.data, "establishments/logos")
            cover_url = save_uploaded_image(form.cover_file.data, "establishments/covers")
            gallery_urls = _save_many(form.gallery_files.data, "establishments/gallery", max_files=10)
        except ValueError as exc:
            form.gallery_files.errors.append(str(exc))
        else:
            establishment.name = form.name.data.strip()
            establishment.category = form.category.data
            establishment.visual_theme = _theme_for_business(form.category.data)
            establishment.description = form.description.data.strip()
            establishment.phone = (form.phone.data or "").strip() or None
            establishment.whatsapp_enabled = bool(form.whatsapp_enabled.data and establishment.phone)
            establishment.email = (form.email.data or "").strip().lower() or None
            establishment.instagram = (form.instagram.data or "").strip() or None
            establishment.address_line1 = form.address_line1.data.strip()
            establishment.address_line2 = (form.address_line2.data or "").strip() or None
            establishment.neighborhood = (form.neighborhood.data or "").strip() or None
            establishment.city = form.city.data.strip()
            establishment.state = form.state.data.strip().upper()
            establishment.postal_code = (form.postal_code.data or "").strip() or None
            establishment.logo_focus_x = _focus_value(form.logo_focus_x.data)
            establishment.logo_focus_y = _focus_value(form.logo_focus_y.data)
            establishment.cover_focus_x = _focus_value(form.cover_focus_x.data)
            establishment.cover_focus_y = _focus_value(form.cover_focus_y.data)
            if logo_url:
                establishment.logo_url = logo_url
            if cover_url:
                establishment.cover_url = cover_url
            start_order = len(establishment.gallery_items)
            for offset, image_url in enumerate(gallery_urls):
                db.session.add(
                    EstablishmentGalleryItem(
                        establishment=establishment,
                        image_url=image_url,
                        sort_order=start_order + offset,
                    )
                )
            db.session.flush()
            establishment.onboarding_completed = establishment.ready_to_publish
            if establishment.onboarding_completed and establishment.published_at is None:
                establishment.published_at = utcnow()
            db.session.commit()
            flash("Página da empresa atualizada.", "success")
            return redirect(url_for("business.dashboard", slug=slug))

    return render_template(
        "platform/business-edit.html",
        form=form,
        establishment=establishment,
        access=access,
        current_page="business-dashboard",
    )


@business_bp.post("/<slug>/equipe/<int:membership_id>/remover")
@login_required
def remove_team_member(slug, membership_id):
    establishment, access = _managed_establishment(slug)
    membership = db.session.get(ProfessionalEstablishmentMembership, membership_id)
    if membership is None or membership.establishment_id != establishment.id:
        abort(404)
    membership.status = MembershipStatus.INACTIVE
    membership.is_primary = False
    membership.ended_at = datetime.now().date()
    db.session.commit()
    flash("Profissional removido da equipe ativa.", "success")
    return redirect(url_for("business.dashboard", slug=slug))


@business_bp.post("/<slug>/galeria/<int:item_id>/remover")
@login_required
def remove_gallery_item(slug, item_id):
    establishment, access = _managed_establishment(slug)
    item = db.session.get(EstablishmentGalleryItem, item_id)
    if item is None or item.establishment_id != establishment.id:
        abort(404)
    db.session.delete(item)
    db.session.commit()
    flash("Imagem removida da galeria.", "success")
    return redirect(url_for("business.edit", slug=slug))
