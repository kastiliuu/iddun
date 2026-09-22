import re
import unicodedata

from sqlalchemy import select

from app.extensions import db


RESERVED_PUBLIC_HANDLES = {
    "admin",
    "login",
    "logout",
    "cadastro",
    "experiencias",
    "profissionais",
    "minha-conta",
    "minhas-reservas",
    "integracoes",
    "static",
    "api",
    "app",
    "iddun",
}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    compact = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    return compact or "item"


def unique_slug(model, value: str, current_id=None) -> str:
    """Return a unique slug inside one SQLAlchemy model."""
    base = slugify(value)
    candidate = base
    suffix = 2

    while True:
        statement = select(model.id).where(model.slug == candidate)
        if current_id is not None:
            statement = statement.where(model.id != current_id)
        exists = db.session.scalar(statement)
        if exists is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


def public_handle_available(value, resource_type=None, current_id=None):
    from app.models.establishment import Establishment
    from app.models.professional import ProfessionalProfile

    candidate = slugify(value)
    if candidate in RESERVED_PUBLIC_HANDLES:
        return False, "Este endereço é reservado pelo IDDUN."

    queries = [
        ("professional", ProfessionalProfile),
        ("establishment", Establishment),
    ]
    for kind, model in queries:
        statement = select(model.id).where(model.slug == candidate)
        if kind == resource_type and current_id is not None:
            statement = statement.where(model.id != current_id)
        if db.session.scalar(statement) is not None:
            return False, "Este endereço já está sendo usado."
    return True, None


def unique_public_handle(value, resource_type=None, current_id=None):
    base = slugify(value)
    if base in RESERVED_PUBLIC_HANDLES:
        base = f"{base}-perfil"
    candidate = base
    suffix = 2
    while True:
        available, _ = public_handle_available(candidate, resource_type=resource_type, current_id=current_id)
        if available:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1
