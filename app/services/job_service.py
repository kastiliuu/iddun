from sqlalchemy import func, or_, select

from app.extensions import db
from app.models.job import (
    JobApplication,
    JobApplicationStatus,
    JobPost,
    JobPostStatus,
    utcnow,
)
from app.models.professional import (
    ProfessionalProfile,
)
from app.services.establishment_team_service import (
    EstablishmentTeamError,
    require_establishment_manager,
)


class JobError(ValueError):
    pass


def _require_active_user(user):
    if (
        user is None
        or user.id is None
        or not user.is_active
    ):
        raise JobError(
            "Entre em uma conta ativa para continuar."
        )


def _professional_for_user(
    user,
):
    _require_active_user(
        user
    )

    return db.session.scalar(
        select(
            ProfessionalProfile
        ).where(
            ProfessionalProfile.user_id
            == user.id
        )
    )


def _clean_text(
    value,
    *,
    required=False,
    maximum=None,
):
    clean = str(
        value or ""
    ).strip()

    if required and not clean:
        raise JobError(
            "Preencha os campos obrigatórios."
        )

    if (
        maximum is not None
        and len(clean) > maximum
    ):
        raise JobError(
            "Um dos campos ultrapassa o tamanho permitido."
        )

    return clean or None


def _managed_establishment(
    user,
    reference,
):
    try:
        return require_establishment_manager(
            user,
            reference,
        )
    except EstablishmentTeamError as exc:
        raise JobError(
            str(exc)
        ) from exc


def public_jobs(
    *,
    search=None,
    city=None,
    specialty=None,
    offset=0,
    limit=20,
):
    filters = [
        JobPost.status
        == JobPostStatus.PUBLISHED,
    ]

    query = (
        select(JobPost)
        .join(
            JobPost.establishment
        )
        .where(
            *filters,
            JobPost.establishment.has(
                is_active=True
            ),
        )
    )

    if search:
        needle = (
            f"%{str(search).strip().lower()}%"
        )
        query = query.where(
            or_(
                func.lower(
                    JobPost.title
                ).like(needle),
                func.lower(
                    JobPost.description
                ).like(needle),
                func.lower(
                    JobPost.specialty
                ).like(needle),
            )
        )

    if city:
        query = query.where(
            func.lower(
                JobPost.city
            ).like(
                f"%{str(city).strip().lower()}%"
            )
        )

    if specialty:
        query = query.where(
            func.lower(
                JobPost.specialty
            ).like(
                f"%{str(specialty).strip().lower()}%"
            )
        )

    count_query = select(
        func.count(
            JobPost.id
        )
    ).where(
        JobPost.status
        == JobPostStatus.PUBLISHED,
        JobPost.establishment.has(
            is_active=True
        ),
    )

    if search:
        needle = (
            f"%{str(search).strip().lower()}%"
        )
        count_query = count_query.where(
            or_(
                func.lower(
                    JobPost.title
                ).like(needle),
                func.lower(
                    JobPost.description
                ).like(needle),
                func.lower(
                    JobPost.specialty
                ).like(needle),
            )
        )

    if city:
        count_query = count_query.where(
            func.lower(
                JobPost.city
            ).like(
                f"%{str(city).strip().lower()}%"
            )
        )

    if specialty:
        count_query = count_query.where(
            func.lower(
                JobPost.specialty
            ).like(
                f"%{str(specialty).strip().lower()}%"
            )
        )

    total = (
        db.session.scalar(
            count_query
        )
        or 0
    )

    items = db.session.scalars(
        query.order_by(
            JobPost.published_at.desc(),
            JobPost.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    return items, total


def public_job(
    job_id,
):
    job = db.session.get(
        JobPost,
        job_id,
    )

    if (
        job is None
        or job.status
        != JobPostStatus.PUBLISHED
        or job.establishment is None
        or not job.establishment.is_active
    ):
        raise JobError(
            "Vaga não encontrada."
        )

    return job


def managed_jobs(
    *,
    user,
    establishment_reference,
):
    establishment, access = (
        _managed_establishment(
            user,
            establishment_reference,
        )
    )

    items = db.session.scalars(
        select(JobPost)
        .where(
            JobPost.establishment_id
            == establishment.id
        )
        .order_by(
            JobPost.created_at.desc(),
            JobPost.id.desc(),
        )
    ).all()

    return (
        establishment,
        access,
        items,
    )


def create_job(
    *,
    user,
    establishment_reference,
    payload,
):
    establishment, _ = (
        _managed_establishment(
            user,
            establishment_reference,
        )
    )

    title = _clean_text(
        payload.get(
            "title"
        ),
        required=True,
        maximum=160,
    )
    description = _clean_text(
        payload.get(
            "description"
        ),
        required=True,
    )
    specialty = _clean_text(
        payload.get(
            "specialty"
        ),
        maximum=120,
    )
    employment_type = _clean_text(
        payload.get(
            "employmentType"
        ),
        maximum=40,
    )
    compensation_text = _clean_text(
        payload.get(
            "compensationText"
        ),
        maximum=180,
    )

    job = JobPost(
        establishment=establishment,
        title=title,
        specialty=specialty,
        description=description,
        city=(
            _clean_text(
                payload.get(
                    "city"
                ),
                maximum=120,
            )
            or establishment.city
        ),
        state=(
            _clean_text(
                payload.get(
                    "state"
                ),
                maximum=80,
            )
            or establishment.state
        ),
        neighborhood=(
            _clean_text(
                payload.get(
                    "neighborhood"
                ),
                maximum=120,
            )
            or establishment.neighborhood
        ),
        employment_type=(
            employment_type
        ),
        compensation_text=(
            compensation_text
        ),
        status=JobPostStatus.DRAFT,
    )

    db.session.add(
        job
    )
    db.session.commit()

    return job


def _managed_job(
    *,
    user,
    establishment_reference,
    job_id,
):
    establishment, access = (
        _managed_establishment(
            user,
            establishment_reference,
        )
    )

    job = db.session.get(
        JobPost,
        job_id,
    )

    if (
        job is None
        or job.establishment_id
        != establishment.id
    ):
        raise JobError(
            "Vaga não encontrada."
        )

    return (
        establishment,
        access,
        job,
    )


def update_job(
    *,
    user,
    establishment_reference,
    job_id,
    payload,
):
    _, _, job = _managed_job(
        user=user,
        establishment_reference=(
            establishment_reference
        ),
        job_id=job_id,
    )

    if (
        job.status
        == JobPostStatus.CLOSED
    ):
        raise JobError(
            "Uma vaga encerrada não pode ser editada."
        )

    fields = {
        "title": (
            "title",
            160,
        ),
        "specialty": (
            "specialty",
            120,
        ),
        "description": (
            "description",
            None,
        ),
        "city": (
            "city",
            120,
        ),
        "state": (
            "state",
            80,
        ),
        "neighborhood": (
            "neighborhood",
            120,
        ),
        "employmentType": (
            "employment_type",
            40,
        ),
        "compensationText": (
            "compensation_text",
            180,
        ),
    }

    for key, (
        attribute,
        maximum,
    ) in fields.items():
        if key not in payload:
            continue

        required = (
            key
            in {
                "title",
                "description",
            }
        )

        setattr(
            job,
            attribute,
            _clean_text(
                payload.get(
                    key
                ),
                required=required,
                maximum=maximum,
            ),
        )

    db.session.commit()

    return job


def publish_job(
    *,
    user,
    establishment_reference,
    job_id,
):
    _, _, job = _managed_job(
        user=user,
        establishment_reference=(
            establishment_reference
        ),
        job_id=job_id,
    )

    if (
        job.status
        == JobPostStatus.CLOSED
    ):
        raise JobError(
            "Uma vaga encerrada não pode ser republicada."
        )

    if (
        not job.title
        or not job.description
    ):
        raise JobError(
            "Complete título e descrição antes de publicar."
        )

    job.status = (
        JobPostStatus.PUBLISHED
    )
    job.published_at = (
        job.published_at
        or utcnow()
    )
    job.closed_at = None

    db.session.commit()

    return job


def close_job(
    *,
    user,
    establishment_reference,
    job_id,
):
    _, _, job = _managed_job(
        user=user,
        establishment_reference=(
            establishment_reference
        ),
        job_id=job_id,
    )

    if (
        job.status
        == JobPostStatus.CLOSED
    ):
        return job

    job.status = (
        JobPostStatus.CLOSED
    )
    job.closed_at = utcnow()

    db.session.commit()

    return job


def apply_to_job(
    *,
    user,
    job_id,
    message=None,
):
    _require_active_user(
        user
    )

    professional = (
        _professional_for_user(
            user
        )
    )

    if (
        professional is None
        or not professional.is_active
    ):
        raise JobError(
            "Você precisa de um perfil profissional ativo para se candidatar."
        )

    job = public_job(
        job_id
    )

    application = db.session.scalar(
        select(
            JobApplication
        ).where(
            JobApplication.job_id
            == job.id,
            JobApplication.professional_id
            == professional.id,
        )
    )

    clean_message = _clean_text(
        message,
        maximum=1200,
    )

    if application is None:
        application = (
            JobApplication(
                job=job,
                professional=professional,
                message=clean_message,
                status=(
                    JobApplicationStatus
                    .SUBMITTED
                ),
            )
        )
        db.session.add(
            application
        )
    else:
        if (
            application.status
            == JobApplicationStatus.SUBMITTED
        ):
            raise JobError(
                "Você já se candidatou a esta vaga."
            )

        application.status = (
            JobApplicationStatus
            .SUBMITTED
        )
        application.message = (
            clean_message
        )

    db.session.commit()

    return application


def withdraw_application(
    *,
    user,
    job_id,
):
    _require_active_user(
        user
    )

    professional = (
        _professional_for_user(
            user
        )
    )

    if professional is None:
        raise JobError(
            "Sua conta não possui perfil profissional."
        )

    application = db.session.scalar(
        select(
            JobApplication
        ).where(
            JobApplication.job_id
            == job_id,
            JobApplication.professional_id
            == professional.id,
        )
    )

    if (
        application is None
        or application.status
        != JobApplicationStatus.SUBMITTED
    ):
        raise JobError(
            "Candidatura ativa não encontrada."
        )

    application.status = (
        JobApplicationStatus
        .WITHDRAWN
    )
    db.session.commit()

    return application


def my_applications(
    user,
):
    _require_active_user(
        user
    )

    professional = (
        _professional_for_user(
            user
        )
    )

    if professional is None:
        return []

    return db.session.scalars(
        select(
            JobApplication
        )
        .where(
            JobApplication.professional_id
            == professional.id
        )
        .order_by(
            JobApplication.created_at.desc(),
            JobApplication.id.desc(),
        )
    ).all()


def managed_job_applications(
    *,
    user,
    establishment_reference,
    job_id,
):
    _, _, job = _managed_job(
        user=user,
        establishment_reference=(
            establishment_reference
        ),
        job_id=job_id,
    )

    items = db.session.scalars(
        select(
            JobApplication
        )
        .where(
            JobApplication.job_id
            == job.id,
            JobApplication.status
            == JobApplicationStatus.SUBMITTED,
        )
        .order_by(
            JobApplication.created_at.desc(),
            JobApplication.id.desc(),
        )
    ).all()

    return job, items


def serialize_job(
    job,
    *,
    include_description=True,
    applications_count=None,
):
    establishment = (
        job.establishment
    )

    payload = {
        "id": str(
            job.id
        ),
        "title":
            job.title,
        "specialty":
            job.specialty,
        "city":
            job.city,
        "state":
            job.state,
        "neighborhood":
            job.neighborhood,
        "employmentType":
            job.employment_type,
        "compensationText":
            job.compensation_text,
        "status":
            job.status,
        "publishedAt": (
            job.published_at.isoformat()
            if job.published_at
            else None
        ),
        "closedAt": (
            job.closed_at.isoformat()
            if job.closed_at
            else None
        ),
        "createdAt":
            job.created_at.isoformat(),
        "establishment": {
            "id": str(
                establishment.id
            ),
            "routeId":
                establishment.slug,
            "name":
                establishment.name,
            "logo":
                establishment.logo_url,
            "city":
                establishment.city,
            "state":
                establishment.state,
            "neighborhood":
                establishment.neighborhood,
        },
    }

    if include_description:
        payload[
            "description"
        ] = job.description

    if (
        applications_count
        is not None
    ):
        payload[
            "applicationsCount"
        ] = applications_count

    return payload


def serialize_application(
    application,
    *,
    include_professional=False,
):
    payload = {
        "id": str(
            application.id
        ),
        "status":
            application.status,
        "message":
            application.message,
        "createdAt":
            application.created_at.isoformat(),
        "job":
            serialize_job(
                application.job,
                include_description=False,
            ),
    }

    if include_professional:
        professional = (
            application.professional
        )
        payload[
            "professional"
        ] = {
            "id": str(
                professional.id
            ),
            "routeId":
                professional.slug,
            "name":
                professional.display_name,
            "specialty":
                professional.primary_specialty,
            "avatar":
                professional.avatar_url,
            "city":
                professional.city,
            "state":
                professional.state,
        }

    return payload
