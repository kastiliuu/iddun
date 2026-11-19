"""Recrutamento na Web (V1-CONV-D01/D05), em paridade com o app.

Telas finas sobre app/services/job_service.py, que concentra as regras:
- vaga nova exige o piloto habilitado pelo admin (A1-DEC-01, V1-CONV-D03);
- gerente só com permissão expressa da dona (A1-DEC-02);
- vagas que já existiam continuam no ar e administráveis (V1-CONV-D04);
- candidatura só com perfil profissional ativo; nova candidatura depois de
  retirar é permitida (A1-DEC-03).
Nada aqui decide permissão por conta própria.
"""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from app.extensions import db, limiter
from app.forms.platform import JobApplicationForm, JobPostForm
from app.models.establishment import (
    Establishment,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.job import JobApplication, JobApplicationStatus, JobPostStatus
from app.services.job_service import (
    JobError,
    JobPermissionError,
    apply_to_job,
    close_job,
    create_job,
    managed_job_applications,
    managed_jobs,
    my_applications,
    public_job,
    public_jobs,
    publish_job,
    update_job,
    withdraw_application,
)
from app.services.recruitment_access_service import (
    RecruitmentAccessError,
    establishment_managers,
    recruitment_capability,
    set_manager_recruitment_grant,
)

recruitment_bp = Blueprint("recruitment", __name__)

JOB_STATUS_LABELS = {
    JobPostStatus.DRAFT: "Rascunho",
    JobPostStatus.PUBLISHED: "Publicada",
    JobPostStatus.CLOSED: "Encerrada",
}
APPLICATION_STATUS_LABELS = {
    JobApplicationStatus.SUBMITTED: "Enviada",
    JobApplicationStatus.WITHDRAWN: "Retirada",
}
PAGE_SIZE = 20


def _payload(form):
    return {
        "title": form.title.data,
        "specialty": form.specialty.data,
        "description": form.description.data,
        "employmentType": form.employment_type.data,
        "compensationText": form.compensation_text.data,
    }


def _business_access(slug):
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


# ---------------------------------------------------------------- público

@recruitment_bp.get("/vagas")
def jobs():
    search = (request.args.get("q") or "").strip()[:80]
    city = (request.args.get("cidade") or "").strip()[:120]
    page = max(1, request.args.get("pagina", 1, type=int) or 1)
    items, total = public_jobs(
        search=search or None,
        city=city or None,
        offset=(page - 1) * PAGE_SIZE,
        limit=PAGE_SIZE,
    )
    return render_template(
        "recruitment/jobs.html",
        items=items,
        total=total,
        page=page,
        has_next=page * PAGE_SIZE < total,
        search=search,
        city=city,
        current_page="jobs",
    )


def _my_application(job):
    if not current_user.is_authenticated or current_user.professional_profile is None:
        return None
    return db.session.scalar(
        select(JobApplication).where(
            JobApplication.job_id == job.id,
            JobApplication.professional_id == current_user.professional_profile.id,
        )
    )


@recruitment_bp.get("/vagas/<int:job_id>")
def job_detail(job_id):
    try:
        job = public_job(job_id)
    except JobError:
        abort(404)
    profile = current_user.professional_profile if current_user.is_authenticated else None
    return render_template(
        "recruitment/job-detail.html",
        job=job,
        form=JobApplicationForm(),
        application=_my_application(job),
        can_apply=profile is not None and profile.is_active,
        current_page="jobs",
    )


@recruitment_bp.post("/vagas/<int:job_id>/candidatar")
@login_required
@limiter.limit("30 per hour")
def apply(job_id):
    form = JobApplicationForm()
    if not form.validate_on_submit():
        flash("Não foi possível enviar a candidatura. Confira a mensagem.", "error")
        return redirect(url_for("recruitment.job_detail", job_id=job_id))
    try:
        apply_to_job(user=current_user, job_id=job_id, message=form.message.data)
    except JobError as exc:
        db.session.rollback()
        flash(str(exc), "error")
    else:
        flash("Candidatura enviada. O estabelecimento recebe seu perfil profissional.", "success")
    return redirect(url_for("recruitment.job_detail", job_id=job_id))


@recruitment_bp.post("/vagas/<int:job_id>/retirar")
@login_required
@limiter.limit("30 per hour")
def withdraw(job_id):
    try:
        withdraw_application(user=current_user, job_id=job_id)
    except JobError as exc:
        db.session.rollback()
        flash(str(exc), "error")
    else:
        flash("Candidatura retirada. Você pode se candidatar de novo enquanto a vaga estiver aberta.", "info")
    target = request.form.get("voltar")
    if target == "candidaturas":
        return redirect(url_for("recruitment.applications"))
    return redirect(url_for("recruitment.job_detail", job_id=job_id))


@recruitment_bp.get("/minhas-candidaturas")
@login_required
def applications():
    return render_template(
        "recruitment/my-applications.html",
        items=my_applications(current_user),
        has_profile=current_user.professional_profile is not None,
        status_labels=APPLICATION_STATUS_LABELS,
        JobPostStatus=JobPostStatus,
        JobApplicationStatus=JobApplicationStatus,
        current_page="jobs",
    )


# ---------------------------------------------------------------- empresa

def _business_page(establishment, access, **context):
    capability = recruitment_capability(establishment, access)
    return render_template(
        "recruitment/business-jobs.html",
        establishment=establishment,
        access=access,
        capability=capability,
        managers=establishment_managers(establishment) if capability["isOwner"] else [],
        status_labels=JOB_STATUS_LABELS,
        JobPostStatus=JobPostStatus,
        current_page="business-jobs",
        **context,
    )


@recruitment_bp.route("/business/<slug>/vagas", methods=["GET", "POST"])
@login_required
def business_jobs(slug):
    establishment, access = _business_access(slug)
    form = JobPostForm()
    try:
        _, _, items = managed_jobs(user=current_user, establishment_reference=establishment.id)
    except JobPermissionError as exc:
        # A1-DEC-02: gerente sem permissão não vê vagas; a página explica.
        return _business_page(establishment, access, items=[], form=None, denied=str(exc)), 403
    except JobError:
        abort(403)

    if request.method == "POST":
        if form.validate_on_submit():
            try:
                job = create_job(
                    user=current_user,
                    establishment_reference=establishment.id,
                    payload=_payload(form),
                )
            except JobError as exc:
                db.session.rollback()
                flash(str(exc), "error")
                return redirect(url_for("recruitment.business_jobs", slug=slug))
            flash("Rascunho da vaga criado. Revise e publique quando estiver pronta.", "success")
            return redirect(url_for("recruitment.business_jobs", slug=slug) + f"#vaga-{job.id}")
        return _business_page(establishment, access, items=items, form=form, denied=None), 400

    return _business_page(establishment, access, items=items, form=form, denied=None)


@recruitment_bp.route("/business/<slug>/vagas/<int:job_id>/editar", methods=["GET", "POST"])
@login_required
def business_job_edit(slug, job_id):
    establishment, access = _business_access(slug)
    try:
        _, _, items = managed_jobs(user=current_user, establishment_reference=establishment.id)
    except JobPermissionError:
        abort(403)
    except JobError:
        abort(403)
    job = next((item for item in items if item.id == job_id), None)
    if job is None:
        abort(404)
    if job.status == JobPostStatus.CLOSED:
        flash("Uma vaga encerrada não pode ser editada.", "info")
        return redirect(url_for("recruitment.business_jobs", slug=slug))

    form = JobPostForm(obj=job)
    if form.validate_on_submit():
        try:
            update_job(
                user=current_user,
                establishment_reference=establishment.id,
                job_id=job.id,
                payload=_payload(form),
            )
        except JobError as exc:
            db.session.rollback()
            flash(str(exc), "error")
        else:
            flash("Vaga atualizada.", "success")
            return redirect(url_for("recruitment.business_jobs", slug=slug) + f"#vaga-{job.id}")
    return render_template(
        "recruitment/business-job-form.html",
        establishment=establishment,
        access=access,
        job=job,
        form=form,
        status_labels=JOB_STATUS_LABELS,
        current_page="business-jobs",
    ), (400 if request.method == "POST" else 200)


def _job_action(slug, job_id, action, success):
    establishment, _ = _business_access(slug)
    try:
        action(user=current_user, establishment_reference=establishment.id, job_id=job_id)
    except JobError as exc:
        db.session.rollback()
        flash(str(exc), "error")
    else:
        flash(success, "success")
    return redirect(url_for("recruitment.business_jobs", slug=slug) + f"#vaga-{job_id}")


@recruitment_bp.post("/business/<slug>/vagas/<int:job_id>/publicar")
@login_required
@limiter.limit("60 per hour")
def business_job_publish(slug, job_id):
    return _job_action(slug, job_id, publish_job, "Vaga publicada. Profissionais já podem se candidatar.")


@recruitment_bp.post("/business/<slug>/vagas/<int:job_id>/encerrar")
@login_required
@limiter.limit("60 per hour")
def business_job_close(slug, job_id):
    return _job_action(slug, job_id, close_job, "Vaga encerrada. As candidaturas recebidas ficam guardadas.")


@recruitment_bp.get("/business/<slug>/vagas/<int:job_id>/candidaturas")
@login_required
def business_job_applications(slug, job_id):
    establishment, access = _business_access(slug)
    try:
        job, items = managed_job_applications(
            user=current_user, establishment_reference=establishment.id, job_id=job_id
        )
    except JobPermissionError:
        abort(403)
    except JobError:
        abort(404)
    return render_template(
        "recruitment/business-job-applications.html",
        establishment=establishment,
        access=access,
        job=job,
        items=items,
        status_labels=JOB_STATUS_LABELS,
        current_page="business-jobs",
    )


@recruitment_bp.post("/business/<slug>/recrutamento/gerentes/<int:access_id>")
@login_required
@limiter.limit("60 per hour")
def business_manager_grant(slug, access_id):
    establishment, access = _business_access(slug)
    wanted = request.form.get("permitir")
    if wanted not in {"0", "1"}:
        abort(400)
    try:
        set_manager_recruitment_grant(
            establishment=establishment,
            owner_access=access,
            target_access_id=access_id,
            can_recruit=wanted == "1",
            reason=request.form.get("motivo"),
        )
    except RecruitmentAccessError as exc:
        db.session.rollback()
        if exc.code in {"recruitment_access_denied", "manager_not_found"}:
            abort(403 if exc.code == "recruitment_access_denied" else 404)
        flash(str(exc), "error")
    else:
        flash(
            "Permissão de recrutar concedida." if wanted == "1" else "Permissão de recrutar retirada. Vale imediatamente.",
            "success",
        )
    return redirect(url_for("recruitment.business_jobs", slug=slug) + "#gerentes")
