from sqlalchemy import select

from app.extensions import db
from app.models.certification import (
    ProfessionalCertification,
)
from app.models.establishment import (
    Establishment,
    EstablishmentGalleryItem,
)
from app.models.experience import Experience
from app.models.professional import (
    ProfessionalPortfolioItem,
    ProfessionalProfile,
)
from app.models.profile import ClientProfile
from app.models.work_post import WorkPost
from app.services.media_storage import (
    get_media_storage,
    normalize_media_key,
)


MEDIA_COLUMNS = (
    ClientProfile.avatar_url,
    ProfessionalProfile.avatar_url,
    ProfessionalProfile.cover_url,
    ProfessionalPortfolioItem.image_url,
    Establishment.logo_url,
    Establishment.cover_url,
    EstablishmentGalleryItem.image_url,
    Experience.image_url,
    ProfessionalCertification.document_url,
    WorkPost.image_url,
)


def referenced_media_paths():
    referenced = set()

    for column in MEDIA_COLUMNS:
        values = db.session.scalars(
            select(column).where(
                column.is_not(None)
            )
        ).all()

        for value in values:
            normalized = normalize_media_key(
                value
            )

            if normalized is not None:
                referenced.add(normalized)

    return referenced


def orphaned_media_paths():
    storage = get_media_storage()
    stored = set(
        storage.list_stored_paths()
    )
    referenced = referenced_media_paths()

    return sorted(
        stored - referenced
    )


def delete_orphaned_media():
    storage = get_media_storage()
    removed = []

    for stored_path in (
        orphaned_media_paths()
    ):
        if storage.delete(stored_path):
            removed.append(stored_path)

    return removed


def missing_media_references():
    """Relaciona uploads apontados pelo banco que faltam no storage ativo.

    Não altera registros nem objetos. Falhas de acesso ao backend são propagadas
    para não serem confundidas com arquivos efetivamente ausentes.
    """
    storage = get_media_storage()
    results = []
    existence = {}

    for column in MEDIA_COLUMNS:
        model = column.class_
        rows = db.session.execute(
            select(model.id, column).where(column.is_not(None))
        )
        for record_id, value in rows:
            key = normalize_media_key(value)
            if key is None:
                continue
            if key not in existence:
                existence[key] = storage.exists(key)
            if not existence[key]:
                results.append((model.__tablename__, record_id, column.key, key))

    return sorted(results, key=lambda item: (item[0], item[1], item[2]))
