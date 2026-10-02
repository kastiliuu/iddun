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
