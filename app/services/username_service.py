"""@username — identidade social pública única (ID-SOC-R1-02, Notion 08, 14/11/2026).

Regras aprovadas:
- 3 a 30 caracteres: a-z, 0-9, ponto e sublinhado; sem ponto no início, no
  fim ou repetido. Sempre gravado em minúsculas.
- Reservados (com variações de ponto, sublinhado ou número): iddun, admin,
  suporte, oficial, ajuda, seguranca, api, pro, business.
- Um nome já usado (atual ou do histórico) nunca passa a outra pessoa.
- Troca no máximo 1 vez a cada 14 dias; o nome anterior vai para o histórico
  e continua apontando para a mesma pessoa.
"""

from datetime import datetime, timedelta, timezone
import re
import unicodedata

from sqlalchemy import select

from app.extensions import db


MIN_LENGTH = 3
MAX_LENGTH = 30
# O preenchimento automático deixa folga para o sufixo numérico.
GENERATED_BASE_LENGTH = 24
CHANGE_INTERVAL = timedelta(days=14)
FALLBACK_BASE = "pessoa"

RESERVED = frozenset(
    {
        "iddun",
        "admin",
        "suporte",
        "oficial",
        "ajuda",
        "seguranca",
        "api",
        "pro",
        "business",
    }
)

_PATTERN = re.compile(r"^[a-z0-9_](?:[a-z0-9_.]*[a-z0-9_])?$")


class UsernameError(ValueError):
    pass


def normalize(raw):
    """Tira espaços e o @ inicial e passa para minúsculas."""
    value = (raw or "").strip()
    if value.startswith("@"):
        value = value[1:]
    return value.lower()


def is_reserved(value):
    """Reservado mesmo com ponto, sublinhado ou número (ex.: ad.min, iddun_2)."""
    core = re.sub(r"[._0-9]", "", value or "")
    return core in RESERVED or core.startswith("iddun")


def validate_format(raw):
    """Devolve o @username normalizado ou explica o que está errado."""
    value = normalize(raw)
    if len(value) < MIN_LENGTH or len(value) > MAX_LENGTH:
        raise UsernameError(
            f"Use de {MIN_LENGTH} a {MAX_LENGTH} caracteres."
        )
    if not _PATTERN.match(value) or ".." in value:
        raise UsernameError(
            "Use só letras sem acento, números, ponto e sublinhado, "
            "sem ponto no começo, no fim ou repetido."
        )
    if is_reserved(value):
        raise UsernameError("Este @ é reservado. Escolha outro.")
    return value


def base_from_name(name):
    """Base do @ sugerido a partir do nome: sem acento, minúsculo, com pontos."""
    ascii_name = (
        unicodedata.normalize("NFKD", name or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    base = re.sub(r"[^a-z0-9]+", ".", ascii_name).strip(".")
    base = base[:GENERATED_BASE_LENGTH].strip(".")
    if len(base) < MIN_LENGTH or is_reserved(base):
        base = FALLBACK_BASE
    return base


def _owner_of(value):
    """Conta dona do nome, atual ou no histórico; None se livre."""
    from app.models.user import User, UsernameHistory

    owner = db.session.scalar(select(User.id).where(User.username == value))
    if owner is not None:
        return owner
    return db.session.scalar(
        select(UsernameHistory.user_id).where(UsernameHistory.username == value)
    )


def is_available(value, *, user=None):
    owner = _owner_of(value)
    return owner is None or (user is not None and owner == user.id)


def suggest(name, *, taken=()):
    """Primeiro @ livre: base, base2, base3… Respeita nomes já escolhidos no mesmo envio."""
    base = base_from_name(name)
    taken = set(taken)
    candidate = base
    suffix = 1
    while candidate in taken or _owner_of(candidate) is not None:
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


def choose_for_new_account(raw, name):
    """No cadastro: o @ informado (validado e livre) ou um sugerido pelo nome."""
    if not (raw or "").strip():
        return suggest(name)
    value = validate_format(raw)
    if not is_available(value):
        raise UsernameError("Este @ já está em uso. Escolha outro.")
    return value


def next_change_at(user):
    """Data a partir da qual a pessoa pode trocar de novo; None se já pode."""
    from app.models.user import UsernameHistory

    last = db.session.scalar(
        select(UsernameHistory.created_at)
        .where(UsernameHistory.user_id == user.id)
        .order_by(UsernameHistory.created_at.desc())
        .limit(1)
    )
    if last is None:
        return None
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    available_at = last + CHANGE_INTERVAL
    return available_at if available_at > datetime.now(timezone.utc) else None


def change_username(user, raw):
    """Troca o @ da pessoa. O anterior vai para o histórico. Não faz commit."""
    from app.models.user import UsernameHistory

    value = validate_format(raw)
    if value == user.username:
        return False
    if not is_available(value, user=user):
        raise UsernameError("Este @ já está em uso. Escolha outro.")
    blocked_until = next_change_at(user)
    if blocked_until is not None:
        raise UsernameError(
            "Você poderá trocar o @ de novo em "
            f"{blocked_until.astimezone(timezone.utc).strftime('%d/%m/%Y')}."
        )

    # A pessoa pode voltar a um @ que já foi dela.
    own_old = db.session.scalar(
        select(UsernameHistory).where(
            UsernameHistory.user_id == user.id,
            UsernameHistory.username == value,
        )
    )
    if own_old is not None:
        db.session.delete(own_old)
        db.session.flush()

    if user.username:
        db.session.add(UsernameHistory(user_id=user.id, username=user.username))
    user.username = value
    return True


def resolve(raw):
    """(conta, é_o_atual) para um @; (None, False) se ninguém usa."""
    from app.models.user import User, UsernameHistory

    value = normalize(raw)
    if not value:
        return None, False
    user = db.session.scalar(select(User).where(User.username == value))
    if user is not None:
        return user, True
    old = db.session.scalar(
        select(UsernameHistory).where(UsernameHistory.username == value)
    )
    if old is not None:
        return old.user, False
    return None, False
